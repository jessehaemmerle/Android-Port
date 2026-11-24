# Port-Notizen: OnePlus 3 → lineage-24.0 / Android 17

Geprüft heißt: am 2026-11-24 per `git ls-remote` bzw. durch Lesen der Dateien bestätigt.
Vermutung heißt: aus Fachwissen abgeleitet, nicht ausprobiert.

## Geprüft

- Neuestes AOSP-Tag: `android-17.0.0_r1`. `lineage-24.0` basiert darauf.
- Der Device-Tree `LineageOS/android_device_oneplus_oneplus3` hat als neuesten Zweig `lineage-18.1`; der Kernel
  `android_kernel_oneplus_msm8996` ebenso (3.18).
- `lineage-24.0` enthält **keine** msm8996-HAL-Projekte (`hardware/qcom-caf/` kennt nur msm8953, sdm660, sm8150 und neuer).
  Es gibt noch gepflegte Zweige: Audio bis `lineage-22.2-caf-msm8996`, Display und Media bis `lineage-23.0-caf-msm8996`.
  Sie passen zu Android 15/16, nicht zu 17. Das Manifest zeigt darauf.
- Blobs (`TheMuppets/proprietary_vendor_oneplus`): neuester Zweig mit oneplus3 ist `lineage-19.1`.
- Der Device-Tree hat 50 HIDL-HAL-Einträge in `device.mk` (Composer 2.1, Allocator/Mapper 2.0, Keymaster 3.0,
  Gatekeeper 1.0, Health 2.1, Light 2.0, Camera 2.4, Audio 2/6 ...). Der Fingerprint ist Android 9 (OxygenOS-Blobs).
- Die Strip-Listen: jeder Pfad existiert im Manifest, siehe `scripts/gen_strip_manifest.py`.
- MindTheGapps `cinnamonbun` existiert und hat `arm64/arm64-vendor.mk`.

## Nicht geprüft (kein Build möglich)

- Ob nach dem Entfernen der Projekte aus den Strip-Listen noch alle Soong-/Make-Abhängigkeiten stimmen.
  Fehlende Module melden sich im ersten Build, der Fix ist dann, den Eintrag aus `CORE`/`APPS` zu streichen.
- Ob das Produkt `lineage_oneplus3` mit `common_mini_phone.mk` alles Nötige erbt.

## Wahrscheinliche Blocker (Vermutung, nach Gewicht sortiert)

1. **Kernel 3.18.** Android 17 erwartet für neue Geräte Kernel ab 6.x. Ältere Kernel laufen nur mit Anpassungen
   (eBPF-Netzwerkzählung, Cgroup v2, Memory-Management). Rückportieren oder auf einen neueren Kernel (4.4+) heben
   ist der größte Aufwand und kann scheitern.
2. **Vendor-Schnittstelle.** Die Blobs sind Android 9. Android 17 verlangt für Grafik, Keymint, Gatekeeper usw. AIDL-HALs.
   Die 50 HIDL-HALs brauchen Adapter oder neue Implementierungen; ein Teil davon (Composer, Gralloc, Keymaster)
   liegt in Qualcomm-Blobs, für die es keinen Quellcode gibt.
3. **SELinux.** Der Sepolicy-Baum des Geräts ist von 2019; Android 17 hat die Plattform-Policy stark verändert.
4. **32-Bit-Anteil.** Das Gerät baut `arm64` + `arm`. Neuere Android-Versionen drängen auf 64-Bit-only; ob sich der
   32-Bit-Teil der Blobs noch laden lässt, ist offen.

## Empfohlener Weg

1. Zuerst `lineage-22.2` (Android 15) oder `lineage-23.0` (Android 16) bauen: Die msm8996-HAL-Zweige existieren dafür.
   Das zeigt, welche Blocker real sind. `scripts/sync.sh` und das Manifest lassen sich dafür anpassen (`BRANCH`, `revision`).
2. Erst wenn das bootet, auf `lineage-24.0` heben.

Ein bootfähiges Ergebnis ist nicht zugesagt.
