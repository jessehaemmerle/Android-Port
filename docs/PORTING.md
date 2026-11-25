# Port-Notizen: OnePlus 3 → lineage-23.0 / Android 16

„Geprüft" heißt: am 2026-11-24/25 per `git ls-remote`, durch Lesen der Dateien oder durch Kompilieren bestätigt.
„Vermutung" heißt: aus Fachwissen abgeleitet, nicht ausprobiert.

## Geprüft: Plattform

- Neuestes AOSP-Tag: `android-17.0.0_r1` (`lineage-24.0`). `lineage-23.0` basiert auf `android-16.0.0_r1`.
- Der Device-Tree `LineageOS/android_device_oneplus_oneplus3` endet bei `lineage-18.1`, der Kernel ebenso (3.18.124).
  Es gibt keinen öffentlichen OnePlus-3-Tree für Android 12–16 (gesucht auf GitHub, nur ältere Forks).
- `lineage-23.0` führt die msm8996-HALs im eigenen Manifest (`hardware/qcom-caf/msm8996/{audio,display,media}`),
  `lineage-24.0` nicht mehr. **Audio-Zweig `lineage-23.0-caf-msm8996` existiert auf GitHub nicht**, `repo sync` würde
  scheitern; `manifests/oneplus3.xml` biegt ihn per `extend-project` auf `lineage-22.2-caf-msm8996` um.
- Bei den Lineage-Geräte-Trees ist der Zweig `lineage-23.0` oft nur ein Alias auf `lineage-22.2` (Beispiel
  `oneplus_sdm845-common`: identischer Commit). Die 22.2-Trees sind also nicht automatisch 23.0-tauglich: ihr
  `PRODUCT_FULL_TREBLE_OVERRIDE` und `PRODUCT_ENFORCE_VINTF_MANIFEST_OVERRIDE` sind in Android 16 obsolet.
- Blobs (`TheMuppets/proprietary_vendor_oneplus`): neuester Zweig mit oneplus3 ist `lineage-19.1`.
- MindTheGapps `baklava` existiert und hat `arm64/arm64-vendor.mk`; `common_mini_phone.mk` existiert in 23.0.

## Geprüft: Änderungen im Device-Tree (Begründung)

| Änderung | Beleg |
|---|---|
| `extract-files.sh`/`setup-makefiles.sh` → `extract-files.py` | `tools/extract-utils` auf `lineage-23.0` enthält nur Python (`extract.py`, `extract_utils/`), kein `extract_utils.sh`. Das neue Skript lädt gegen den echten `extract_utils` und baut ein `ExtractUtilsModule` |
| `verity.mk`-Include entfernt | `build/make/target/product/verity.mk` gibt es in `android-16.0.0_r1` nicht (HTTP 404) |
| `BOARD_PLAT_PUBLIC_SEPOLICY_DIR` → `SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS` | `KATI_obsolete_var` in `build/make/core/config.mk` mit genau diesem Ersatz |
| `PRODUCT_ENFORCE_VINTF_MANIFEST_OVERRIDE` entfernt | `KATI_obsolete_var ... Deprecated.` |
| `prebuilts/vndk/v28/…`-Kopien → `libprotobuf-cpp-{full,lite}-vendorcompat` | Das 23.0-Manifest hat nur `prebuilts/vndk/v30..v34`; `hardware/lineage/compat` definiert die `-vendorcompat`-Module mit `stem: libprotobuf-cpp-full` |
| `lineage.dependencies` leer | Der OnePlus-Kernel hat keinen 23.0-Zweig; Kernel und HALs kommen aus `manifests/oneplus3.xml` |
| Kernel-Zeilen (`oneplus3_defconfig`, `TARGET_KERNEL_ARCH`, UFS-`boot_devices`), CPU-Variante `generic` + `RUNTIME kryo`, CAF-VINTF-Matrizen, `non_ab_device.mk`, `qcom-caf/common/common.mk`, `BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES` | Übernommen von `xiaomi_msm8996-common@lineage-22.2` (gleicher SoC, gleiche HAL-Zweige); die referenzierten Dateien existieren in 23.0 |

`scripts/check_obsolete_vars.py` findet solche Fälle automatisch: Es liest alle `KATI_obsolete_var` aus
`build/make/core/*.mk` des AOSP-Tags (67 Variablen). Es meldet auf dem angepassten Tree nichts und findet auf dem
unveränderten 22.2-Referenztree die beiden obigen Variablen.

## Korrektur einer früheren Vermutung

Ich hatte die 50 HIDL-HALs im Device-Tree als wahrscheinlichen Blocker bezeichnet. Das ist so nicht belegt:

- Alle alten HIDL-Interface-Verzeichnisse liegen noch in `hardware/interfaces` von `android-16.0.0_r1` (33 geprüft:
  Composer 2.1, Allocator/Mapper 2.0, Keymaster 3.0, Gatekeeper 1.0, Health 2.1, Light 2.0, Audio 2/6/7 …).
- Der Xiaomi-msm8996-Tree (`lineage-22.2`, offiziell) nutzt genau diese HIDL-Dienste (Composer 2.1, Keymaster 3.0,
  Gatekeeper 1.0, Camera 2.4/2.5, Audio 6.0) mit `legacy`-Kompatibilitätsmatrizen.

Ob das **Laufzeitverhalten** unter Android 16 (VINTF/Framework-Matrix) noch passt, ist offen.

## Nicht geprüft (kein Build möglich)

- Ob der Quellbaum nach dem Entfernen der Projekte aus den Strip-Listen noch baut (Soong-Abhängigkeiten).
- Ob alle 175 Pakete aus `device.mk` in 23.0 noch existieren. 107 davon stehen nicht in der 22.2-Referenz. Einige sind
  OnePlus-spezifisch (NFC NQ, Doze, PocketMode), bei anderen hat die Referenz moderne Ersatzmodule
  (z. B. `android.hardware.light-service.lineage`, `android.hardware.health-service.qti`, `disable_configstore`,
  `vendor.qti.hardware.memtrack-service`). Das zeigt erst der Build.
- Das Verhalten der Blobs mit Kernel 4.4 und den Android-9-Treibern.

## Blocker, die ich kenne (nach Gewicht)

1. **Vendor-Partition.** Die fstab des OnePlus-3-Trees kennt keine `vendor`-/`cust`-Partition (die Xiaomi-msm8996-Referenz mountet `/vendor` von `cust`).
   `BOARD_VNDK_VERSION := current` und `TARGET_COPY_OUT_VENDOR := vendor` ohne eigene Partition ist so nicht erprobt.
   Entweder Vendor ins System-Image oder die Partition neu aufteilen. **Entscheidung nötig**, siehe unten.
2. **Kernel-Lücken** (siehe `kernel/README.md`): kein Dash Charge, kein Audio-Maschinentreiber für den TFA9890
   (voraussichtlich kein Lautsprecher), alter 3.18-Audio-Teil im DTS, Kamera-EEPROM/Aktuator-Teile, Fuel-Gauge bq27541.
3. **SELinux.** Der Sepolicy-Baum des Geräts ist von 2019 (Android 9); Android 16 hat die Plattform-Policy stark
   verändert. Rechnen Sie mit vielen Policy-Fehlern.
4. **Kernel 4.4 unter Android 16.** Google verlangt für neue Geräte deutlich neuere Kernel. Für ältere Geräte gilt das
   nicht strikt, aber Features wie eBPF-Netzwerkzählung sind bei 4.4 begrenzt (Vermutung).
5. **32-Bit-Anteil.** Das Gerät baut `arm64` + `arm`; ob der 32-Bit-Teil der Blobs noch lädt, ist offen.

## Offene Entscheidung: Vendor-Partition

Die fstab und die `BoardConfig.mk` des OnePlus-3-Trees kennen `system` (3,15 GB), `cache` (256 MB), `userdata`, `boot`,
`recovery` und `misc`, aber kein `vendor`. Optionen:

1. Vendor im System-Image lassen (`/vendor` als Symlink nach `/system/vendor`). Am wenigsten Aufwand, bricht aber das
   Treble-Modell (Vendor lässt sich nicht getrennt aktualisieren).
2. Eine Partition neu anlegen (`cache` ist mit 256 MB vermutlich zu klein, also aus `userdata`). Verlangt
   Neupartitionierung mit Datenverlust und eine eigene fstab.

## Weg zu Android 17

Erst wenn 23.0 bootet: auf `lineage-24.0` heben. Dann müssen die msm8996-HALs selbst ins Manifest und auf Android 17
gebracht werden, weil Lineage sie dort nicht mehr führt. Die Strip-Listen lassen sich mit
`scripts/gen_strip_manifest.py lineage-24.0` neu erzeugen.

Ein bootfähiges Ergebnis ist nicht zugesagt.
