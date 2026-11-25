# Port-Notizen: OnePlus 3 → lineage-23.0 / Android 16

Geprüft heißt: am 2026-11-24 per `git ls-remote` bzw. durch Lesen der Dateien bestätigt.
Vermutung heißt: aus Fachwissen abgeleitet, nicht ausprobiert.

## Geprüft (2026-11-24/25, per `git ls-remote` bzw. durch Lesen der Dateien)

- Neuestes AOSP-Tag: `android-17.0.0_r1` (`lineage-24.0`). `lineage-23.0` basiert auf `android-16.0.0_r1`.
- Der Device-Tree `LineageOS/android_device_oneplus_oneplus3` hat als neuesten Zweig `lineage-18.1`; der Kernel
  `android_kernel_oneplus_msm8996` ebenso (3.18). Beide liegen also fünf Lineage-Versionen hinter 23.0.
- `lineage-23.0` führt die msm8996-HALs im eigenen Manifest (`hardware/qcom-caf/msm8996/{audio,display,media}`).
  `lineage-24.0` tut das nicht mehr. Display und Media haben den Zweig `lineage-23.0-caf-msm8996`.
  **Audio nicht:** Das Manifest verweist auf `lineage-23.0-caf-msm8996`, der Zweig fehlt auf GitHub. Ohne Gegenmaßnahme
  scheitert `repo sync`. `manifests/oneplus3.xml` biegt Audio per `extend-project` auf `lineage-22.2-caf-msm8996` um
  (Android 15, ob der gegen die 23.0-Basis baut, ist offen).
- Blobs (`TheMuppets/proprietary_vendor_oneplus`): neuester Zweig mit oneplus3 ist `lineage-19.1`.
- Der Device-Tree hat 50 HIDL-HAL-Einträge in `device.mk` (Composer 2.1, Allocator/Mapper 2.0, Keymaster 3.0,
  Gatekeeper 1.0, Health 2.1, Light 2.0, Camera 2.4, Audio 2/6 ...). Der Fingerprint ist Android 9 (OxygenOS-Blobs).
- Die Strip-Listen: Das Skript lässt keine Liste zu, die Projekte entfernt, die bleiben müssen (Settings, Dialer,
  msm8996-HALs, vendor/lineage ...). Muster ohne Treffer im Branch sind eine Warnung.
- MindTheGapps `baklava` existiert und hat `arm64/arm64-vendor.mk`. `common_mini_phone.mk` existiert in `lineage-23.0`.

## Nicht geprüft (kein Build möglich)

- Ob nach dem Entfernen der Projekte aus den Strip-Listen noch alle Soong-/Make-Abhängigkeiten stimmen.
  Fehlende Module melden sich im ersten Build, der Fix ist dann, den Eintrag aus `CORE`/`APPS` zu streichen.
- Ob das Produkt `lineage_oneplus3` mit `common_mini_phone.mk` alles Nötige erbt.

## Wahrscheinliche Blocker (Vermutung, nach Gewicht sortiert)

1. **Kernel 3.18.** Android 16 erwartet für neue Geräte Kernel ab 6.x. Ältere Kernel laufen nur mit Anpassungen
   (eBPF-Netzwerkzählung, Cgroup v2, Memory-Management). Rückportieren oder auf einen neueren Kernel (4.4+) heben
   ist der größte Aufwand und kann scheitern.
2. **Vendor-Schnittstelle.** Die Blobs sind Android 9. Android 16 verlangt für Grafik, Keymint, Gatekeeper usw. AIDL-HALs.
   Die 50 HIDL-HALs brauchen Adapter oder neue Implementierungen; ein Teil davon (Composer, Gralloc, Keymaster)
   liegt in Qualcomm-Blobs, für die es keinen Quellcode gibt.
3. **SELinux.** Der Sepolicy-Baum des Geräts ist von 2019; Android 16 hat die Plattform-Policy stark verändert.
4. **32-Bit-Anteil.** Das Gerät baut `arm64` + `arm`. Neuere Android-Versionen drängen auf 64-Bit-only; ob sich der
   32-Bit-Teil der Blobs noch laden lässt, ist offen.

## Weg zu Android 17

Erst wenn 23.0 bootet: auf `lineage-24.0` heben. Dann müssen die msm8996-HALs selbst ins Manifest und auf Android 17
gebracht werden, weil Lineage sie dort nicht mehr führt. Die Strip-Listen lassen sich mit
`scripts/gen_strip_manifest.py lineage-24.0` neu erzeugen.

Ein bootfähiges Ergebnis ist nicht zugesagt.
