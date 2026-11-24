#!/usr/bin/env bash
# Zieht die proprietaeren Treiber (Kamera, Modem, GPU, Sensoren ...) aus einem
# laufenden OnePlus 3 (adb, root/USB-Debugging) oder aus einem entpackten
# OxygenOS-Image. Ohne diese Blobs bootet das Geraet nicht.
#   scripts/extract-blobs.sh [ANDROID_ROOT] [PFAD_ZUM_STOCK_DUMP]
set -euo pipefail
ROOT="${1:-$HOME/lineage}"
cd "$ROOT/device/oneplus/oneplus3"
./extract-files.sh ${2:+"$2"}
