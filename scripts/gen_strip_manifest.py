#!/usr/bin/env python3
"""Erzeugt manifests/strip-*.xml (<remove-project>-Listen) aus dem echten
LineageOS-Manifest (default.xml + snippets/lineage.xml).

Jeder Eintrag wird gegen das Manifest geprueft: Pfade, die es nicht (mehr)
gibt, brechen das Skript ab, damit die Liste bei einem Branch-Wechsel nicht
still veraltet.

Aufruf:  scripts/gen_strip_manifest.py [lineage-branch] [--strict]   (Default: lineage-23.0)

Die Listen gelten fuer mehrere Branches; Muster ohne Treffer sind daher nur eine
Warnung. Mit --strict (z.B. in CI) werden sie zum Fehler.
"""
import re
import sys
import urllib.request
from fnmatch import fnmatch
from pathlib import Path

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
STRICT = "--strict" in sys.argv
BRANCH = ARGS[0] if ARGS else "lineage-23.0"
RAW = f"https://raw.githubusercontent.com/LineageOS/android/{BRANCH}/"
OUT = Path(__file__).resolve().parent.parent / "manifests"

# Stufe 1: Projekte, die fuer ein Telefon mit arm64-SoC sicher nicht gebraucht
# werden (Auto, TV, Emulator, Tests, Mac-Toolchains, fremde Plattformen).
CORE = [
    # Android Automotive / TV / Wear-artige Geraeteklassen
    "packages/apps/Car/*", "packages/services/Car", "packages/services/display_safety",
    "packages/apps/Tv*", "packages/apps/TV", "packages/inputmethods/LeanbackIME",
    "packages/providers/TvProvider", "packages/apps/TvFeedbackConsent",
    "device/lineage/atv", "device/lineage/car", "device/google_car",
    "device/google/atv", "device/google/sdv", "device/google/sdv_display_safety",
    "hardware/sdv/*", "hardware/telink/*",
    # Emulator / virtuelle Geraete
    "device/google/cuttlefish", "device/google/cuttlefish_prebuilts",
    "device/google/cuttlefish_vmm", "device/google/trout",
    "device/generic/goldfish", "device/generic/x86", "device/generic/x86_64",
    "device/generic/car", "device/generic/trusty", "device/sample",
    "prebuilts/android-emulator", "tools/acloud", "tools/netsim",
    # Fremde Kernel-Prebuilts (der OnePlus 3 baut seinen eigenen 3.18-Kernel)
    "kernel/prebuilts/*", "kernel/tests",
    # Trusty-TEE (der OnePlus 3 nutzt Qualcomm QSEE)
    "trusty/*",
    # Fremde Hardware-Stacks
    "hardware/ti/*", "hardware/samsung/*", "hardware/st/*", "hardware/synaptics/*",
    "hardware/nxp/uwb", "hardware/nxp/keymint", "hardware/nxp/weaver",
    "hardware/nxp/nxp_mcu_loader", "hardware/nxp/secure_element",
    "hardware/knowles/*", "hardware/google/pixel", "hardware/google/pixel-sepolicy",
    "hardware/qcom-caf/sm*", "hardware/qcom-caf/sdm*", "hardware/qcom-caf/msm8953/*",
    "hardware/qcom-caf/msm8998/*",
    "vendor/qcom/opensource/commonsys/wfd",
    "device/qcom/sepolicy_vndr/sm*",
    # Test-, Entwickler- und Infrastruktur-Tools (nicht Teil des Images)
    "cts", "development", "platform_testing", "sdk", "pdk",
    "test/*", "external/chromium-crossbench", "external/chromium-web-tests",
    "external/chromium-trace", "external/chromiumos-config",
    "tools/asuite", "tools/tradefederation/*", "tools/trebuchet",
    "tools/loganalysis", "tools/test/*", "tools/dexter", "tools/aadevtools",
    "tools/deviceinfra/prebuilts", "tools/content_addressed_storage/prebuilts",
    "tools/doc_generation", "tools/rr_prebuilt", "tools/apifinder",
    "tools/lint_checks", "tools/mainline", "tools/ndkports", "tools/currysrc",
    "tools/external/fat32lib", "tools/security", "tools/strictdeps",
    "tools/repohooks", "tools/external_updater",
    "packages/apps/Test/*", "packages/apps/SampleLocationAttribution",
    "packages/apps/DeviceDiagnostics", "packages/apps/Traceur",
    # Mac-/Windows-Toolchains
    "prebuilts/clang/host/darwin-x86",
    # Lineage-Projekte, die nur Webseite/CI/Doku sind
    "lineage/*",
    # Webview-Prebuilts fuer x86 (arm + arm64 bleiben)
    "external/chromium-webview/prebuilt/x86", "external/chromium-webview/prebuilt/x86_64",
]

# Stufe 2: Apps und Extras, auf die ein Telefon notfalls verzichten kann.
# Behalten werden: Dialer, Kontakte, Nachrichten, Einstellungen, Launcher,
# Kamera (Aperture), Galerie (Glimpse), Dateien (DocumentsUI), WebView.
APPS = [
    "packages/apps/Jelly", "packages/apps/Etar", "packages/apps/Recorder",
    "packages/apps/Seedvault", "packages/apps/Twelve", "packages/apps/Updater",
    "packages/apps/DeskClock", "packages/apps/ExactCalculator",
    "packages/apps/FMRadio", "packages/apps/FlipFlap", "packages/apps/Gallery2",
    "packages/apps/AudioFX", "packages/apps/Camelot", "packages/apps/Canvas",
    "packages/apps/Catapult", "packages/apps/Backgrounds", "packages/apps/Music",
    "packages/apps/MusicFX", "packages/apps/Browser2", "packages/apps/Camera2",
    "packages/apps/EyeDropper", "packages/apps/AvatarPicker",
    "packages/apps/UniversalMediaPlayer", "packages/apps/VirtualGamepad",
    "packages/apps/QuickSearchBox", "packages/apps/PersonalContext",
    "packages/apps/OnDeviceAppPrediction", "packages/apps/SystemUIGo",
    "packages/apps/Login", "packages/apps/Multiuser", "packages/apps/PrivateSpace",
    "packages/apps/ThemePicker", "packages/wallpapers/LivePicker",
    "packages/screensavers/*", "packages/services/BuiltInPrintService",
    "packages/services/DeviceAsWebcam", "packages/services/CrossDeviceSync",
    "packages/services/DroidfoodAttestationFixer",
    "external/bash", "external/htop", "external/nano", "external/openssh",
    "external/rsync", "external/unrar", "external/vim", "external/libncurses",
]


def fetch(name):
    with urllib.request.urlopen(RAW + name, timeout=60) as r:
        return r.read().decode()


def projects(xml):
    out = []
    for m in re.finditer(r"<project\s+([^>]*?)/?>", xml):
        d = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        out.append((d["path"] if "path" in d else d["name"], d["name"]))
    return out


def main():
    allp = projects(fetch("default.xml")) + projects(fetch("snippets/lineage.xml"))
    by_path = {}
    for path, name in allp:
        by_path.setdefault(path, []).append(name)

    def expand(patterns):
        hit, miss = {}, []
        for pat in patterns:
            found = [p for p in by_path if fnmatch(p, pat)]
            if not found:
                miss.append(pat)
            for p in found:
                hit[p] = by_path[p]
        return hit, miss

    problems = False
    for label, pats in (("strip-core", CORE), ("strip-apps", APPS)):
        hit, miss = expand(pats)
        if miss:
            problems = problems or STRICT
            print(f"[{label}] kein Treffer in {BRANCH} (ok, wenn der Branch das Projekt nicht hat): {miss}", file=sys.stderr)
        keep = [p for p in hit if p.startswith(("hardware/qcom-caf/msm8996", "hardware/qcom-caf/common",
                "hardware/qcom-caf/bt", "packages/apps/Settings", "packages/apps/Dialer",
                "packages/apps/Launcher3", "vendor/lineage", "lineage-sdk", "device/lineage/sepolicy"))]
        if keep:
            sys.exit(f"[{label}] Strip-Liste trifft Projekte, die bleiben muessen: {keep}")
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f"<!-- AUTOMATISCH ERZEUGT von scripts/gen_strip_manifest.py ({BRANCH}). Nicht von Hand aendern. -->",
            "<manifest>",
        ]
        for path in sorted(hit):
            for name in hit[path]:
                # path=... ist noetig, weil derselbe Repo-Name an mehreren Pfaden liegt
                lines.append(f'  <remove-project name="{name}" path="{path}" />')
        lines.append("</manifest>")
        (OUT / f"{label}.xml").write_text("\n".join(lines) + "\n")
        print(f"{label}.xml: {len(hit)} Projekte entfernt (von {len(allp)})")
    sys.exit(1 if problems else 0)


main()
