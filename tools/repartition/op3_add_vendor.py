#!/usr/bin/env python3
"""Legt auf dem OnePlus 3 eine Partition "vendor" an, indem sie vom Anfang der
Partition "userdata" abgeschnitten wird.  ALLE DATEN IN userdata GEHEN VERLOREN
(das Dateisystem beginnt danach an einer anderen Stelle und muss neu formatiert werden).

Das Skript aendert nur die GPT (Primaer + Backup) der Platte, auf der "userdata" liegt.
Es ist absichtlich vorsichtig:

  * Standard ist ein Trockenlauf: es zeigt die geplante Aenderung und schreibt nichts.
  * Vor dem Schreiben wird die alte GPT in eine Datei gesichert (--restore stellt sie wieder her).
  * Nach dem Schreiben wird alles zurueckgelesen und verglichen.

Betriebsarten
  Abbild (zum Testen oder fuer einen Dump):
      op3_add_vendor.py --image disk.img [--write]
  Geraet ueber adb (muss im Recovery mit root-adb laufen):
      op3_add_vendor.py --adb [--serial XYZ] [--write --yes-i-accept-brick-risk]

Nicht auf dem Geraet getestet. Getestet ist nur die GPT-Logik an Abbildern (siehe test_op3_add_vendor.py).
"""
import argparse
import os
import struct
import subprocess
import sys
import uuid
import zlib

ENTRY_FMT = "<16s16sQQQ72s"  # 128 Byte
HDR_FMT = "<8sIIIIQQQQ16sQIII"  # 92 Byte
SIG = b"EFI PART"


class GptError(Exception):
    pass


class Gpt:
    """Primaere GPT-Daten (LBA 0 .. Ende der Eintragstabelle) und Backup-Bereich."""

    def __init__(self, sector, primary, backup):
        self.sector = sector
        self.primary = bytearray(primary)  # LBA0 .. entries_end
        self.backup = bytearray(backup)  # backup entries .. backup header
        self.parse()

    # ---- Lesen -------------------------------------------------------
    def parse(self):
        s = self.sector
        h = struct.unpack(HDR_FMT, bytes(self.primary[s:s + 92]))
        (sig, rev, hsize, hcrc, _res, my, alt, first, last, guid,
         e_lba, n, esz, ecrc) = h
        if sig != SIG:
            raise GptError("keine GPT-Signatur bei LBA1")
        if hsize < 92 or hsize > s:
            raise GptError(f"unplausible Header-Groesse {hsize}")
        if esz != 128:
            raise GptError(f"Eintragsgroesse {esz} statt 128 wird nicht unterstuetzt")
        hdr = bytearray(self.primary[s:s + hsize])
        hdr[16:20] = b"\0\0\0\0"
        if zlib.crc32(bytes(hdr)) != hcrc:
            raise GptError("Header-CRC der primaeren GPT stimmt nicht")
        self.h = dict(rev=rev, hsize=hsize, my=my, alt=alt, first=first, last=last,
                      guid=guid, e_lba=e_lba, n=n, esz=esz)
        self.e_sectors = (n * esz + s - 1) // s
        ent = bytes(self.primary[e_lba * s:e_lba * s + n * esz])
        if len(ent) != n * esz:
            raise GptError("Eintragstabelle unvollstaendig gelesen")
        if zlib.crc32(ent) != ecrc:
            raise GptError("CRC der Eintragstabelle stimmt nicht")
        self.entries = [bytearray(ent[i * esz:(i + 1) * esz]) for i in range(n)]

    @staticmethod
    def name_of(e):
        return bytes(e[56:128]).decode("utf-16le", "ignore").split("\0")[0]

    def find(self, name):
        for i, e in enumerate(self.entries):
            if self.name_of(e) == name and bytes(e[0:16]) != bytes(16):
                return i
        return None

    def first_lba(self, i):
        return struct.unpack_from("<Q", self.entries[i], 32)[0]

    def last_lba(self, i):
        return struct.unpack_from("<Q", self.entries[i], 40)[0]

    # ---- Aendern -----------------------------------------------------
    def add_vendor(self, vendor_bytes, label="vendor"):
        if self.find(label) is not None:
            raise GptError(f"Partition '{label}' existiert schon, nichts zu tun")
        ud = self.find("userdata")
        if ud is None:
            raise GptError("Partition 'userdata' nicht gefunden")
        sysi = self.find("system")
        if sysi is None:
            raise GptError("Partition 'system' nicht gefunden (Typ-GUID fuer vendor)")
        free = next((i for i, e in enumerate(self.entries) if bytes(e[0:16]) == bytes(16)), None)
        if free is None:
            raise GptError("kein freier Eintrag in der Partitionstabelle")
        s = self.sector
        if self.last_lba(ud) > self.h["last"] or self.first_lba(ud) < self.h["first"]:
            raise GptError("userdata liegt ausserhalb des nutzbaren GPT-Bereichs, die Tabelle ist nicht plausibel")
        if vendor_bytes % (1 << 20):
            raise GptError("Vendor-Groesse muss ein Vielfaches von 1 MiB sein")
        vs = vendor_bytes // s
        u0, u1 = self.first_lba(ud), self.last_lba(ud)
        if (u0 * s) % (1 << 20):
            raise GptError("userdata beginnt nicht an einer 1-MiB-Grenze, Ausrichtung nicht sicher")
        if u1 - u0 + 1 <= vs + (1 << 30) // s:
            raise GptError("userdata ist zu klein (weniger als 1 GiB blieben uebrig)")
        # Kein anderer Eintrag darf den Bereich ueberlappen
        for i, e in enumerate(self.entries):
            if i in (ud,) or bytes(e[0:16]) == bytes(16):
                continue
            a, b = self.first_lba(i), self.last_lba(i)
            if not (b < u0 or a > u1):
                raise GptError(f"Eintrag {i} ({self.name_of(e)}) ueberlappt userdata")
        v_entry = bytearray(128)
        v_entry[0:16] = self.entries[sysi][0:16]  # Typ-GUID wie system
        v_entry[16:32] = uuid.uuid4().bytes_le
        struct.pack_into("<QQQ", v_entry, 32, u0, u0 + vs - 1, 0)
        v_entry[56:128] = label.encode("utf-16le").ljust(72, b"\0")
        struct.pack_into("<Q", self.entries[ud], 32, u0 + vs)  # neuer userdata-Anfang
        self.entries[ud][16:32] = uuid.uuid4().bytes_le  # neue eindeutige GUID
        self.entries[free] = v_entry
        self.rebuild()
        return free + 1, ud + 1, (u0, u0 + vs - 1), (u0 + vs, u1)

    def rebuild(self):
        s, h = self.sector, self.h
        ent = b"".join(bytes(e) for e in self.entries)
        ecrc = zlib.crc32(ent)
        # Primaer
        self.primary[h["e_lba"] * s:h["e_lba"] * s + len(ent)] = ent
        self.primary[s:s + h["hsize"]] = self._header(h["my"], h["alt"], h["e_lba"], ecrc)
        # Backup: Eintraege liegen direkt vor dem Backup-Header
        b_e_lba = h["alt"] - self.e_sectors
        self.backup[:len(ent)] = ent
        bh = self._header(h["alt"], h["my"], b_e_lba, ecrc)
        off = self.e_sectors * s
        self.backup[off:off + h["hsize"]] = bh

    def _header(self, my, alt, e_lba, ecrc):
        h = self.h
        raw = bytearray(struct.pack(HDR_FMT, SIG, h["rev"], h["hsize"], 0, 0, my, alt,
                                    h["first"], h["last"], h["guid"], e_lba, h["n"],
                                    h["esz"], ecrc))
        raw += bytes(h["hsize"] - len(raw))
        struct.pack_into("<I", raw, 16, zlib.crc32(bytes(raw)))
        return bytes(raw)


# ---------------------------------------------------------------------------
# Ein-/Ausgabe: Abbilddatei oder adb
# ---------------------------------------------------------------------------
class ImageIO:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "r+b")  # noqa: SIM115
        self.size = os.path.getsize(path)

    def read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def write(self, off, data):
        self.f.seek(off)
        self.f.write(data)
        self.f.flush()
        os.fsync(self.f.fileno())

    def sector_size(self):
        for s in (512, 4096):
            if self.read(s, 8) == SIG:
                return s
        raise GptError("keine GPT gefunden (weder 512 noch 4096 Byte Sektoren)")

    def total(self):
        return self.size


class AdbIO:
    def __init__(self, serial):
        self.base = ["adb"] + (["-s", serial] if serial else [])
        out = self.sh("id -u").strip()
        if out != "0":
            raise GptError("adb shell ist nicht root (id -u = %r); im Recovery mit 'adb root' starten" % out)
        link = self.sh("readlink -f /dev/block/bootdevice/by-name/userdata").strip()
        if not link.startswith("/dev/block/"):
            raise GptError(f"userdata-Link nicht aufloesbar: {link!r}")
        base = os.path.basename(link)
        # sdaNN -> sda
        disk = base.rstrip("0123456789")
        if not disk or disk == base:
            # Namen wie mmcblk0p12 / nvme0n1p3
            disk = base.rsplit("p", 1)[0]
        self.dev = "/dev/block/" + disk
        self.sys = f"/sys/block/{disk}"

    def sh(self, cmd):
        return subprocess.run(self.base + ["shell", cmd], capture_output=True, text=True, check=True).stdout

    def sector_size(self):
        return int(self.sh(f"cat {self.sys}/queue/logical_block_size").strip())

    def total(self):
        return int(self.sh(f"cat {self.sys}/size").strip()) * 512

    def read(self, off, n):
        s = self.sector_size()
        assert off % s == 0 and n % s == 0, "unausgerichteter Lesezugriff"
        r = subprocess.run(self.base + ["exec-out", f"dd if={self.dev} bs={s} skip={off // s} count={n // s} 2>/dev/null"],
                           capture_output=True, check=True)
        return r.stdout

    def write(self, off, data):
        s = self.sector_size()
        assert off % s == 0 and len(data) % s == 0
        tmp = "/tmp/op3_gpt_part.bin"
        local = "op3_gpt_part.tmp"
        open(local, "wb").write(data)
        try:
            subprocess.run(self.base + ["push", local, tmp], check=True, capture_output=True)
            self.sh(f"dd if={tmp} of={self.dev} bs={s} seek={off // s} count={len(data) // s} conv=notrunc && sync")
        finally:
            os.unlink(local)


def load(io):
    s = io.sector_size()
    hdr = struct.unpack(HDR_FMT, io.read(s, 92))
    my, alt, e_lba, n, esz = hdr[5], hdr[6], hdr[10], hdr[11], hdr[12]
    e_sectors = (n * esz + s - 1) // s
    primary = io.read(0, (e_lba + e_sectors) * s)
    backup = io.read((alt - e_sectors) * s, (e_sectors + 1) * s)
    return Gpt(s, primary, backup), alt, e_sectors


def apply(io, g, alt, e_sectors):
    s = g.sector
    io.write(0, bytes(g.primary))
    io.write((alt - e_sectors) * s, bytes(g.backup))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="Plattenabbild (Datei)")
    src.add_argument("--adb", action="store_true", help="Geraet ueber adb (Recovery, root)")
    ap.add_argument("--serial")
    ap.add_argument("--vendor-mib", type=int, default=1024, help="Groesse der Vendor-Partition in MiB (Standard 1024)")
    ap.add_argument("--write", action="store_true", help="wirklich schreiben (sonst Trockenlauf)")
    ap.add_argument("--yes-i-accept-brick-risk", action="store_true",
                    help="bei --adb --write verlangt: bestaetigt, dass eine falsche GPT das Geraet unbrauchbar machen kann")
    ap.add_argument("--backup", default="op3-gpt-backup.bin", help="Datei fuer die Sicherung der alten GPT")
    ap.add_argument("--restore", metavar="DATEI", help="alte GPT aus einer Sicherung zurueckschreiben")
    a = ap.parse_args(argv)

    io = ImageIO(a.image) if a.image else AdbIO(a.serial)
    try:
        if a.restore:
            blob = open(a.restore, "rb").read()
            s, alt, es, plen = struct.unpack("<IQII", blob[:20])
            prim, back = blob[20:20 + plen], blob[20 + plen:]
            g = Gpt(s, prim, back)
            if not a.write:
                print("Trockenlauf: Sicherung ist gueltig, wuerde GPT zurueckschreiben (--write zum Ausfuehren)")
                return 0
            apply(io, g, alt, es)
            print("GPT aus Sicherung zurueckgeschrieben.")
            return 0

        g, alt, e_sectors = load(io)
        total = io.total()
        if (alt + 1) * g.sector != total:
            raise GptError("Backup-Header liegt nicht am Plattenende (Plattengroesse %d, erwartet %d)"
                           % (total, (alt + 1) * g.sector))
        old_primary, old_backup = bytes(g.primary), bytes(g.backup)
        n, ud_n, v, u = g.add_vendor(a.vendor_mib << 20)
        s = g.sector
        print(f"Sektorgroesse {s}, {g.h['n']} Eintraege")
        print(f"  neu:      Partition {n} 'vendor'   LBA {v[0]}-{v[1]}  ({(v[1]-v[0]+1)*s/2**20:.0f} MiB)")
        print(f"  geaendert: Partition {ud_n} 'userdata' LBA {u[0]}-{u[1]}  ({(u[1]-u[0]+1)*s/2**30:.2f} GiB)")
        print("  ALLE DATEN IN userdata GEHEN VERLOREN, danach 'userdata' neu formatieren (Recovery: Daten loeschen).")
        if not a.write:
            print("Trockenlauf, nichts geschrieben. Mit --write ausfuehren.")
            return 0
        if a.adb and not a.yes_i_accept_brick_risk:
            raise GptError("--adb --write verlangt zusaetzlich --yes-i-accept-brick-risk")
        with open(a.backup, "wb") as f:
            f.write(struct.pack("<IQII", s, alt, e_sectors, len(old_primary)) + old_primary + old_backup)
        print(f"Alte GPT gesichert in {a.backup}")
        apply(io, g, alt, e_sectors)
        chk, _, _ = load(io)  # liest und prueft CRCs neu
        if chk.find("vendor") is None or bytes(chk.primary) != bytes(g.primary) or bytes(chk.backup) != bytes(g.backup):
            raise GptError("Rueckleseprobe stimmt nicht! Mit --restore %s zurueckschreiben" % a.backup)
        print("Geschrieben und zurueckgelesen: OK. Jetzt Geraet im Recovery neu starten und userdata formatieren.")
        return 0
    except GptError as e:
        print("ABBRUCH:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
