#!/usr/bin/env bash
# Holt LineageOS lineage-23.0 (AOSP android-16.0.0_r1), entschlackt den Baum und
# legt den OnePlus-3-Device-Tree hinein.
#   scripts/sync.sh [ZIELVERZEICHNIS]      (Default: ~/lineage)
# Umgebung:  STRIP=core|apps|none   (Default: apps = core + optionale Apps)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${1:-$HOME/lineage}"
STRIP="${STRIP:-apps}"
BRANCH=lineage-23.0

free_gb=$(df -BG --output=avail "$(dirname "$ROOT")" | tail -1 | tr -dc 0-9)
ram_gb=$(free -g | awk '/^Mem:/{print $2}')
(( free_gb >= 350 )) || echo "WARNUNG: nur ${free_gb} GB frei, Quellbaum + Build brauchen ca. 350 GB." >&2
(( ram_gb >= 30 ))  || echo "WARNUNG: nur ${ram_gb} GB RAM (+Swap), der Build will >= 32 GB." >&2
command -v repo >/dev/null || { echo "'repo' fehlt: https://source.android.com/docs/setup/download#installing-repo" >&2; exit 1; }

mkdir -p "$ROOT" && cd "$ROOT"
[ -d .repo ] || repo init -u https://github.com/LineageOS/android.git -b "$BRANCH" \
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
# OnePlus-3-Patches auf den Kernel legen (idempotent: erst sauber zuruecksetzen)
git -C kernel/oneplus/msm8996 checkout -q -- . && git -C kernel/oneplus/msm8996 clean -fdq
for p in "$SRC"/kernel/patches/*.patch; do
  git -C kernel/oneplus/msm8996 apply --whitespace=nowarn "$p" || { echo "Patch $p passt nicht" >&2; exit 1; }
done
echo "Fertig. Weiter mit: scripts/build.sh $ROOT   (vorher Blobs: scripts/extract-blobs.sh)"
