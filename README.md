# Android-Port: OnePlus 3 (oneplus3) auf aktuellem Android

Ziel: das neueste Android auf dem OnePlus 3, so schlank wie möglich, mit minimalen Google-Apps.

**Stand: Gerüst, nicht gebaut, nicht gebootet.** Der Build lief nicht, weil die Entwicklungsumgebung
(4 Kerne, 15 GB RAM, ~60 GB Platz) dafür zu klein ist. Ob das Ergebnis bootet, ist offen.
Siehe [docs/PORTING.md](docs/PORTING.md) für die bekannten Blocker.

## Basis

| Was | Wert |
|---|---|
| AOSP | `android-17.0.0_r1` (neuestes Tag auf android.googlesource.com, geprüft 2026-11-24) |
| Basis | LineageOS `lineage-24.0` (zieht genau dieses AOSP-Tag) |
| Gerät | `oneplus3`, Snapdragon 821 (msm8996), Kernel 3.18 |
| GApps | MindTheGapps, Zweig `cinnamonbun` (Android 17): Play Store, Setup Wizard, Google-App. OpenGApps (pico) ist eingestellt und endet bei Android 11. |

Offiziell unterstützt LineageOS den OnePlus 3 nur bis `lineage-18.1` (Android 11). Alles darüber ist ein eigener Port.

## Inhalt

- `manifests/oneplus3.xml`: Local-Manifest (Kernel, msm8996-HALs, Blobs, GApps)
- `manifests/strip-core.xml`: 248 Projekte entfernt (Auto, TV, Emulator, Tests, Mac-Toolchains, fremde SoCs/Kernel)
- `manifests/strip-apps.xml`: 47 weitere Projekte entfernt (Browser, Musik, Kalender, Uhr, Rechner, Updater, Shell-Tools ...)
- `scripts/gen_strip_manifest.py`: erzeugt die beiden Strip-Listen und prüft jeden Pfad gegen das echte Manifest
- `device/`: OnePlus-3-Device-Tree (Stand `lineage-18.1`) mit minimalem Produkt `lineage_oneplus3` (Lineage-Mini-Telefon + GApps)
- `scripts/sync.sh`, `extract-blobs.sh`, `build.sh`: Quellbaum holen, Blobs ziehen, bauen

Behalten werden: Telefon, Kontakte, Nachrichten, Einstellungen, Launcher, Kamera (Aperture), Galerie (Glimpse), Dateien, WebView.
Die Liste steht in `scripts/gen_strip_manifest.py` (`CORE`, `APPS`) und lässt sich dort ändern.

## Benutzung (auf einem eigenen Rechner)

Voraussetzung: Linux, ≥ 32 GB RAM (oder viel Swap), ≥ 350 GB frei, `repo`, `rsync`, `ccache`, Build-Abhängigkeiten laut
[LineageOS-Wiki](https://wiki.lineageos.org/devices/). Ein OnePlus 3 mit entsperrtem Bootloader.

```sh
scripts/sync.sh ~/lineage           # STRIP=core|apps|none
scripts/extract-blobs.sh ~/lineage  # Blobs vom laufenden Gerät (adb) ziehen
WITH_GMS=false scripts/build.sh ~/lineage   # ohne GApps; ohne WITH_GMS=false mit GApps
```
Der erste Build bricht sehr wahrscheinlich ab. Die Fehler und der Weg dahin stehen in `docs/PORTING.md`.
