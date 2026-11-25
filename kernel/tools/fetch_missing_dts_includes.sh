#!/usr/bin/env bash
# loop: compile dtb; for each missing include fetch from OnePlus kernel
cd "$(dirname "$0")/k44"; export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
T=$1
for i in $(seq 1 40); do
  out=$(make O=out qcom/$T 2>&1)
  miss=$(echo "$out" | grep -oE 'fatal error: [^:]+: No such file' | sed 's/fatal error: //;s/: No such file//' | head -1)
  [ -z "$miss" ] && { echo "$out" | grep -vE 'make\[|^\s*(CHK|GEN)' | head -${2:-40}; exit; }
  base=$(basename "$miss")
  path=$(git -C ../kop ls-tree -r --name-only HEAD | grep -E "(^|/)$base\$" | grep -E 'dts/qcom|include/dt-bindings' | head -1)
  [ -z "$path" ] && { echo "NICHT GEFUNDEN: $miss"; exit 1; }
  # Zielpfad relativ zu arm64 dts/qcom bzw. include
  case "$path" in
    arch/arm/boot/dts/qcom/*) dest=arch/arm64/boot/dts/qcom/${path#arch/arm/boot/dts/qcom/};;
    *) dest=$path;;
  esac
  mkdir -p "$(dirname $dest)"; git -C ../kop show HEAD:$path > $dest; echo "geholt: $path -> $dest"
done
