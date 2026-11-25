#!/usr/bin/env bash
# Holt LineageOS lineage-23.0 (AOSP android-16.0.0_r1), entschlackt den Baum und
# legt den OnePlus-3-Device-Tree hinein.
#   scripts/sync.sh [ZIELVERZEICHNIS]      (Default: neben diesem Repo, z.B. /mnt/daten2/lineage)
#   CHECK_ONLY=1 scripts/sync.sh           nur Platz, RAM und Werkzeuge pruefen
# Umgebung:  STRIP=core|apps|none   (Default: apps = core + optionale Apps)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=common.sh
source "$SRC/scripts/common.sh"
ROOT="${1:-$(default_root)}"
STRIP="${STRIP:-apps}"
BRANCH=lineage-23.0

preflight "$ROOT" || exit 1
[ "${CHECK_ONLY:-0}" = 1 ] && { echo "Pruefung beendet (CHECK_ONLY=1)."; exit 0; }

mkdir -p "$ROOT" && cd "$ROOT"
# .repo/manifest.xml gibt es erst nach einem vollstaendigen "repo init"; ein abgebrochener Versuch hinterlaesst nur .repo/
[ -f .repo/manifest.xml ] || repo init -u https://github.com/LineageOS/android.git -b "$BRANCH" \
    --git-lfs --depth=1 --no-clone-bundle

mkdir -p .repo/local_manifests
cp "$SRC/manifests/oneplus3.xml" .repo/local_manifests/
rm -f .repo/local_manifests/strip-*.xml
case "$STRIP" in
  none) ;;
  core) cp "$SRC/manifests/strip-core.xml" .repo/local_manifests/ ;;
  apps) cp "$SRC"/manifests/strip-{core,apps}.xml .repo/local_manifests/ ;;
  *) echo "STRIP muss core|apps|none sein" >&2; exit 1 ;;
esac

repo sync -c --no-tags --no-clone-bundle -j"$(nproc)" --force-sync

# Device-Tree aus diesem Repo in den Quellbaum kopieren
rsync -a --delete "$SRC/device/oneplus/oneplus3/" device/oneplus/oneplus3/
rsync -a --delete "$SRC/device/oneplus/common/"   device/oneplus/common/
rsync -a --delete "$SRC/device/oppo/common/"      device/oppo/common/
# lineage-23.0 hat die Linkfiles fuer hardware/qcom-caf/msm8996 auskommentiert; ohne sie werden die HALs dort nicht gebaut
ln -sfn ../common/os_pickup.bp hardware/qcom-caf/msm8996/Android.bp
ln -sfn ../common/os_pickup.mk hardware/qcom-caf/msm8996/Android.mk
# OnePlus-3-Patches auf den Kernel legen (idempotent: erst sauber zuruecksetzen)
git -C kernel/oneplus/msm8996 checkout -q -- . && git -C kernel/oneplus/msm8996 clean -fdq
for p in "$SRC"/kernel/patches/*.patch; do
  git -C kernel/oneplus/msm8996 apply --whitespace=nowarn "$p" || { echo "Patch $p passt nicht" >&2; exit 1; }
done
echo "Fertig. Weiter mit: scripts/build.sh $ROOT   (vorher Blobs: scripts/extract-blobs.sh)"
