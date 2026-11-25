#!/usr/bin/env bash
# Baut lineage_oneplus3 (userdebug) als flashbares OTA-Zip.
#   scripts/build.sh [ANDROID_ROOT]       WITH_GMS=false  -> ohne Google-Apps
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=common.sh
source "$SRC/scripts/common.sh"
ROOT="${1:-$(default_root)}"
cd "$ROOT"
export USE_CCACHE=1 CCACHE_EXEC="$(command -v ccache || true)"
[ -n "$CCACHE_EXEC" ] && ccache -M 50G >/dev/null
# shellcheck disable=SC1091
source build/envsetup.sh
breakfast oneplus3 userdebug
mka bacon -j"$(nproc)"
ls -lh "$OUT"/lineage-*-oneplus3.zip
