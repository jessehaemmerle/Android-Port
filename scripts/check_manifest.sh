#!/usr/bin/env bash
# Prueft OHNE grossen Download, ob sich unsere Local-Manifeste mit dem LineageOS-Manifest zusammenfuehren
# lassen (dieselbe Pruefung, die "repo sync" zuerst macht) und ob die wichtigen Projekte drin sind.
#   scripts/check_manifest.sh [lineage-zweig]      braucht 'repo' und Netz (laedt nur das Manifest, ca. 1 MB)
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${1:-lineage-23.0}"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; mkdir -p "$HOME"   # eigene Git-Identitaet, beruehrt die echte Konfiguration nicht
git config --global user.name check; git config --global user.email check@example.com; git config --global color.ui false
mkdir "$T/tree" && cd "$T/tree"
repo init -u https://github.com/LineageOS/android.git -b "$BRANCH" --depth=1 --no-clone-bundle --no-repo-verify </dev/null >/dev/null
mkdir -p .repo/local_manifests && cp "$SRC"/manifests/*.xml .repo/local_manifests/
repo manifest -o "$T/merged.xml" >/dev/null
python3 - "$T/merged.xml" <<'PY'
import re, sys
x = open(sys.argv[1]).read()
paths = {dict(re.findall(r'(\w+)="([^"]*)"', m)).get('path') for m in re.findall(r'<project\s+([^>]*?)/?>', x)}
need = ['kernel/oneplus/msm8996', 'vendor/oneplus', 'vendor/gapps', 'hardware/qcom-caf/common',
        'hardware/qcom-caf/msm8996/audio', 'hardware/qcom-caf/msm8996/display', 'hardware/qcom-caf/msm8996/media',
        'vendor/lineage', 'packages/apps/Settings', 'packages/apps/Dialer', 'packages/apps/Launcher3',
        'device/qcom/sepolicy-legacy-um', 'hardware/lineage/compat', 'prebuilts/clang/kernel/linux-x86/clang-r416183b']
miss = [p for p in need if p not in paths]
print(f"{len(paths)} Projekte im zusammengefuehrten Manifest")
if miss:
    sys.exit("FEHLT im Ergebnis: " + ", ".join(miss))
print("ok: alle benoetigten Projekte sind enthalten")
PY
