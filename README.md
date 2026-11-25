# Android-Port: OnePlus 3 (oneplus3) auf Android 16 (LineageOS 23.0)

Ziel: ein möglichst neues Android auf dem OnePlus 3, so schlank wie möglich, mit minimalen Google-Apps.

Das neueste AOSP ist `android-17.0.0_r1` (LineageOS 24.0). Gewählt ist `lineage-23.0` (Android 16): Für msm8996 gibt es dort noch
HAL-Zweige (`lineage-23.0-caf-msm8996` für Display und Media). Lineage selbst baut msm8996 in 23.0 nicht mehr, die Projekte sind im
Original-Manifest auskommentiert; das Local-Manifest holt sie wieder.

**Stand: Gerüst, nicht gebaut, nicht gebootet.** Der Build lief nicht, weil die Entwicklungsumgebung
(4 Kerne, 15 GB RAM, ~60 GB Platz) dafür zu klein ist. Ob das Ergebnis bootet, ist offen.
Siehe [docs/PORTING.md](docs/PORTING.md) für die bekannten Blocker.

## Basis

| Was | Wert |
|---|---|
| AOSP | `android-16.0.0_r1` (neuestes Tag: `android-17.0.0_r1`, geprüft 2026-11-24) |
| Basis | LineageOS `lineage-23.0` (zieht genau dieses AOSP-Tag) |
| Gerät | `oneplus3`, Snapdragon 821 (msm8996), Kernel 3.18 |
| GApps | MindTheGapps, Zweig `baklava` (Android 16): Play Store, Setup Wizard, Google-App. OpenGApps (pico) ist eingestellt und endet bei Android 11. |

Offiziell unterstützt LineageOS den OnePlus 3 nur bis `lineage-18.1` (Android 11). Alles darüber ist ein eigener Port.

## Stand der Arbeit

| Teil | Stand |
|---|---|
| Kernel | 4.4.302 (Lineage msm8996) + OnePlus-3-Patches; **baut** zu `Image.gz-dtb`, nicht gebootet. Lader/Dash-Charge und Audio-Maschinentreiber fehlen (siehe `kernel/README.md`) |
| Device-Tree | auf lineage-23.0 angepasst, soweit gegen den echten Quelltext prüfbar. **Nicht gebaut**, weil das den vollen Quellbaum braucht |
| Partitionen | `vendor`-Partition (1 GiB) wird mit `tools/repartition/op3_add_vendor.py` aus `userdata` angelegt; Werkzeug an Abbildern getestet, nicht am Gerät (`docs/REPARTITION.md`) |
| Blobs | `extract-files.py` (Python, wie lineage-23.0 es verlangt); Blobs müssen aus dem eigenen Gerät kommen |

## Inhalt

- `manifests/oneplus3.xml`: Local-Manifest (Kernel, msm8996-HALs, Blobs, GApps)
- `manifests/strip-core.xml`: 218 Projekte entfernt (Auto, TV, Emulator, Tests, Mac-Toolchains, fremde SoCs/Kernel)
- `manifests/strip-apps.xml`: 40 weitere Projekte entfernt (Browser, Musik, Kalender, Uhr, Rechner, Updater, Shell-Tools ...)
- `scripts/check_manifest.sh`: führt die Manifeste mit dem echten `repo` zusammen und prüft sie (ohne großen Download)
- `scripts/gen_strip_manifest.py`: erzeugt die beiden Strip-Listen und prüft jeden Pfad gegen das echte Manifest
- `tools/repartition/`: legt die Vendor-Partition an (GPT-Werkzeug mit Tests)
- `kernel/`: Kernel-Patchserie, defconfig, nicht portierte Teile, Werkzeuge
- `device/`: OnePlus-3-Device-Tree (Basis `lineage-18.1`, auf 23.0 angepasst) mit minimalem Produkt `lineage_oneplus3` (Lineage-Mini-Telefon + GApps)
- `scripts/sync.sh`, `extract-blobs.sh`, `build.sh`: Quellbaum holen (inkl. Kernel + Patches), Blobs ziehen, bauen
- `scripts/check_obsolete_vars.py`: findet im Device-Tree Variablen, die Android 16 als obsolet führt (brechen den Build)

Behalten werden: Telefon, Kontakte, Nachrichten, Einstellungen, Launcher, Kamera (Aperture), Galerie (Glimpse), Dateien, WebView.
Die Liste steht in `scripts/gen_strip_manifest.py` (`CORE`, `APPS`) und lässt sich dort ändern.

## Benutzung (auf einem eigenen Rechner)

Voraussetzung: Linux, ≥ 32 GB RAM (oder viel Swap), ≥ 350 GB frei, `repo` (siehe Hinweis von `scripts/sync.sh`), `rsync`, `git-lfs`, `ccache`, Build-Abhängigkeiten laut
[LineageOS-Wiki](https://wiki.lineageos.org/devices/). Ein OnePlus 3 mit entsperrtem Bootloader.

```sh
# Zielordner ohne Angabe: neben diesem Repo (liegt das Repo in /mnt/daten2/Android-Port, wird es /mnt/daten2/lineage).
# Anderer Ort: Ordner als Argument oder LINEAGE_ROOT=/pfad setzen.
CHECK_ONLY=1 scripts/sync.sh        # prüft nur Platz, RAM und Werkzeuge (u. a. 'repo')
scripts/sync.sh                     # STRIP=core|apps|none
scripts/extract-blobs.sh            # Blobs vom laufenden Gerät (adb) ziehen
WITH_GMS=false scripts/build.sh     # ohne GApps; ohne WITH_GMS=false mit GApps
```
Der erste Build bricht sehr wahrscheinlich ab. Die Fehler und der Weg dahin stehen in `docs/PORTING.md`.
