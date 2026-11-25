# Kernel für den OnePlus 3 (4.4.302)

**Basis:** `LineageOS/android_kernel_xiaomi_msm8996`, Zweig `lineage-22.2` (Linux 4.4.302, CAF msm-4.4).
Der OnePlus-3-Kernel (`android_kernel_oneplus_msm8996`) endet bei **3.18.124** und stammt von 2019. Ein 3.18-Kernel
ist für Android 16 zu alt, der Xiaomi-Kernel ist der einzige gepflegte msm8996-Kernel in Lineage.

Die OnePlus-3-Änderungen liegen als Patch-Serie in `patches/` und werden von `scripts/sync.sh` angewendet.
Quelle der Änderungen: die 18 „Import OnePlus changes"-Commits von 2019 im OnePlus-3.18-Kernel, dazu die
OnePlus-DTS (`15801`/`15811`).

## Was geprüft ist

| Prüfung | Ergebnis |
|---|---|
| Serie auf unverändertem `lineage-22.2` anwenden | alle 10 Patches passen, Ergebnis identisch mit dem Arbeitsstand |
| `make oneplus3_defconfig && make Image.gz-dtb` (gcc 13, aarch64) | baut fehlerfrei, 13 MiB mit beiden DTBs |
| DTB-Kompilierung `msm8996-v3-pmi8996-mtp_15801`, `msm8996pro-pmi8996-mtp_15811` | ohne Fehler |
| Auf einem OnePlus 3 gebootet | **nein, nie ausprobiert** |

## Was portiert ist

- DTS für OnePlus 3 (15801) und 3T (15811) inkl. Panel-, Kamera- und Batterie-Daten, 12 OnePlus-Pingruppen, zwei
  OnePlus-UART-Clocks (`0001`)
- Touchscreen Synaptics S3320 und Tasten S1302, Alert-Slider (`tri_state_key`), Fingerabdruck FPC1020 (`0002`)
- NFC PN544 + P61 (`0003`), Lautsprecher-Verstärker TFA9890 (`0004`)
- Dash-Zugriffs-Hooks für GPIO/`io.h` (`0006`), LCD-vddi-Power für das Display (`0007`), Kamera-Kleinigkeiten (`0008`),
  USB/PCI/UFS/PM-Anpassungen (`0009`)
- `oneplus3_defconfig` aus `mi8996_defconfig`; der generische `tfa98xx`-Treiber ist abgeschaltet, weil er dieselben
  Symbole wie der OnePlus-Treiber hat (Link-Fehler)

## Was NICHT portiert ist (Originaldiffs in `unported/`)

| Bereich | Warum nicht |
|---|---|
| **Lader / Dash Charge** (`qpnp-smbcharger`, `qpnp-fg`, `battery_current_limit`) | Der 4.4-Kernel hat die Power-Supply- und Charger-Typ-Logik umgebaut (REAL_TYPE). Die OnePlus-Patches stützen sich auf die alte API. Blindes Mergen eines Laders ist riskant. Der Lader läuft mit den CAF-Standardwerten, **ohne Dash Charge**. |
| **Fuel-Gauge bq27541, `oneplus_fastcg`, Type-C-Chips** (`0005`, nicht aktiviert) | Nutzen `power_supply->get_property/set_property`, `power_supply_set_usb_otg` u. Ä. aus 3.18; Quelltext liegt im Repo, ist aber in der defconfig **aus** |
| **Audio-Maschinentreiber** (`sound/soc/msm/msm8996.c`, `wcd-mbhc`, Routing) | OnePlus hat die MI2S-Anbindung für den TFA9890 eingebaut; der 4.4-Kernel hat dort schon eigenen, anders gebauten Code. Ohne Anpassung hängt der TFA9890 an keiner Soundkarte: **voraussichtlich kein Lautsprecher-Ton**. |
| USB-Gadget/dwc3-VBUS | hängt am Lader (siehe oben) |
| Kamera: Aktuator-Sequenzschreiben, EEPROM-Vendorinfo (IMX298, S5K3P8SP) | Hunks passen nicht, Fuzz-Anwendung hat die Dateien kaputt gemacht |
| `thaw_fingerprintd` beim Resume | nur eine Beschleunigung |

## DTS-Lücke: Treiber, die der 4.4-Kernel zu den DT-Knoten nicht kennt

Für jeden `compatible`-String im gebauten DTB wurde im Quelltext nach einem passenden Treiber gesucht. Ohne Treffer
(echte OnePlus-Lücken): `oneplus,gpio_switch`, `oneplus,rf_cable`, `atmel,24c32`. Weitere Strings des alten
3.18-Audio-DT (`qcom,msm-compr-dsp`, `qcom,msm-dai-slim`, `qcom,tasha-slim-pgd`, `qcom,msm-hdmi-audio-codec-rx`,
`qcom,glink-qos-config`, `qcom,msm-imem`, `qcom,pm-snoc-client`, `qcom,qpnp-regulator`, `qcom,msm-lsuart-v14`,
`qcom,qcom-l2cache-pmu`, `arm,coresight-fuse-v3`) kennt der 4.4-Kernel nicht. Der Audio-Teil des OnePlus-DTS muss
auf die 4.4-Audio-Knoten umgestellt werden.

## Neu bauen / prüfen

```sh
# aarch64-linux-gnu-gcc und arm-linux-gnueabihf-gcc nötig (CROSS_COMPILE_ARM32 wird vom Kernel verlangt)
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabihf-
git clone --depth 1 -b lineage-22.2 https://github.com/LineageOS/android_kernel_xiaomi_msm8996 k && cd k
for p in /pfad/zu/kernel/patches/*.patch; do git apply "$p"; done
make O=out oneplus3_defconfig && make O=out -j"$(nproc)" Image.gz-dtb
```

`tools/` enthält die Hilfsmittel des Imports: `apply_op_patches.py` (dateiweises Anwenden mit Pfad-Umbiegung, Fuzz 0),
`fetch_missing_dts_includes.sh`, `pinctrl_label_diff.py`.
