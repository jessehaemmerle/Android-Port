# Vendor-Partition auf dem OnePlus 3 anlegen

Android 16 verlangt ein eigenes `/vendor`, das der OnePlus 3 ab Werk nicht hat. Der Device-Tree ist darauf
umgestellt (`/vendor` aus Partition `vendor`, 1 GiB, ext4; `first_stage_mount` für `system` und `vendor`).
Die Partition entsteht, indem `tools/repartition/op3_add_vendor.py` **1 GiB vom Anfang von `userdata` abschneidet**.
Alle Daten in `userdata` gehen dabei verloren (Datenverlust ist vereinbart).

## Was geprüft ist und was nicht

| | |
|---|---|
| GPT-Logik an Abbildern mit 512-Byte-Sektoren, erzeugt und danach geprüft mit dem echten `sgdisk` (`sgdisk -v`: keine Probleme, `-p` zeigt `vendor` und `userdata`) | ja |
| GPT-Logik an einem selbst gebauten Abbild mit 4096-Byte-Sektoren (UFS) | ja, aber mit eigenem Prüfcode, nicht mit `sgdisk` |
| Sicherung und Wiederherstellung der alten GPT | ja (Test) |
| Fehlerfälle (vendor existiert, zu wenig Platz, kein freier Eintrag, kaputte CRC, userdata außerhalb der Platte) | ja (Tests) |
| **Lauf auf einem echten OnePlus 3 über adb** | **nein** |
| Ob Bootloader/Firmware des OnePlus 3 die geänderte Tabelle akzeptieren | **nein** |

## Risiko

Das Werkzeug ändert nur die GPT der Platte, auf der `userdata` liegt, und sichert die alte vorher. Eine falsche
Partitionstabelle kann ein Gerät trotzdem unbrauchbar machen (Brick). Wiederherstellung per `--restore` geht nur, solange
das Recovery noch startet. Daten sind egal, das Gerät nicht: erst den Trockenlauf lesen.

## Ablauf

Voraussetzungen: entsperrter Bootloader, ein Recovery mit `adb root` (z. B. das aus diesem Build), `adb` am Rechner.

```sh
adb reboot recovery
adb root
python3 tools/repartition/op3_add_vendor.py --adb                 # Trockenlauf, schreibt nichts
```

Die Ausgabe prüfen: Sektorgröße (bei UFS erwartet 4096), neue Partition `vendor` 1024 MiB, `userdata` kleiner,
der Rest der Tabelle unverändert. Weicht etwas ab, **abbrechen** und mir die Ausgabe geben.

```sh
python3 tools/repartition/op3_add_vendor.py --adb --write --yes-i-accept-brick-risk
```

Das Skript sichert die alte GPT in `op3-gpt-backup.bin` (aufheben!), schreibt Primär- und Backup-GPT, liest zurück und
vergleicht. Danach im Recovery neu starten, `userdata` formatieren („Daten löschen"), dann das Lineage-Zip flashen
(`scripts/build.sh`).

Zurück zum Original: `python3 tools/repartition/op3_add_vendor.py --adb --restore op3-gpt-backup.bin --write`.

Tests: `python3 -I tools/repartition/test_op3_add_vendor.py` (braucht `sgdisk` für den 512-Byte-Test, sonst übersprungen).

## Offen

- **Systempartition:** `system` hat 3,15 GB (`BOARD_SYSTEMIMAGE_PARTITION_SIZE`). Ein Android-16-System mit
  `system_ext`, `product` und GApps kann größer werden. Der Build bricht dann mit einer Größenmeldung ab. Dann wäre
  dieselbe Aktion für `system` nötig; das Werkzeug kann das noch nicht.
- Die ext4-only-Konfiguration von `/data` mit `fileencryption=ice` ist dem Xiaomi-msm8996-Tree entnommen. Ob die
  OnePlus-3-Blobs (Keymaster, ICE) FBE tragen, ist ungeprüft.
