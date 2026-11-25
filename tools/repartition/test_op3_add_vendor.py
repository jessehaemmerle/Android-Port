#!/usr/bin/env python3
"""Tests fuer op3_add_vendor.py.

1. 512-Byte-Sektoren: Abbild mit dem echten `sgdisk` erzeugen, Werkzeug anwenden, mit `sgdisk -v/-p`
   (unabhaengiges Werkzeug) pruefen. Braucht `sgdisk` (Paket gdisk), sonst wird der Test uebersprungen.
2. 4096-Byte-Sektoren (UFS): sgdisk kann das auf Dateien nicht, daher baut der Test die GPT selbst
   (anderer Code als im Werkzeug) und prueft CRCs, Lage und Grenzen neu.
3. Fehlerfaelle: vendor existiert schon, zu wenig Platz, kaputte CRC.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
import zlib

sys.path.insert(0, os.path.dirname(__file__))
import op3_add_vendor as T  # noqa: E402

SYS_T = "97D7B011-54DA-4835-B3C4-917AD6E73D74"
UD_T = "1B81E7E6-F50D-419B-A739-2AEEF8DA3335"


def build_gpt_image(path, sector, total_bytes, parts, n_entries=128):
    """Eigener GPT-Schreiber (unabhaengig vom Werkzeug): parts = [(name, typeguid, first, last)]."""
    total = total_bytes // sector
    ents = bytearray(n_entries * 128)
    for i, (name, tg, a, b) in enumerate(parts):
        e = uuid.UUID(tg).bytes_le + uuid.uuid4().bytes_le + struct.pack("<QQQ", a, b, 0) + name.encode("utf-16le").ljust(72, b"\0")
        ents[i * 128:(i + 1) * 128] = e
    esec = (n_entries * 128 + sector - 1) // sector
    first, last = 2 + esec, total - 2 - esec
    guid = uuid.uuid4().bytes_le

    def hdr(my, alt, elba):
        h = bytearray(struct.pack("<8sIIIIQQQQ16sQIII", b"EFI PART", 0x10000, 92, 0, 0, my, alt, first, last, guid, elba, n_entries, 128, zlib.crc32(bytes(ents))))
        struct.pack_into("<I", h, 16, zlib.crc32(bytes(h)))
        return bytes(h)

    with open(path, "wb") as f:  # Sparse-Datei, nur die GPT-Bereiche werden geschrieben
        f.truncate(total_bytes)
        for off, data in ((sector, hdr(1, total - 1, 2)), (2 * sector, bytes(ents)),
                          ((total - 1 - esec) * sector, bytes(ents)),
                          ((total - 1) * sector, hdr(total - 1, 1, total - 1 - esec))):
            f.seek(off)
            f.write(data)


def verify_independent(tc, path, sector, expect_vendor_mib):
    g, alt, es = T.load(T.ImageIO(path))
    v, u = g.find("vendor"), g.find("userdata")
    tc.assertIsNotNone(v)
    tc.assertIsNotNone(u)
    vs, ve = g.first_lba(v), g.last_lba(v)
    us, ue = g.first_lba(u), g.last_lba(u)
    tc.assertEqual((ve - vs + 1) * sector, expect_vendor_mib << 20)
    tc.assertEqual(ve + 1, us)  # lueckenlos
    tc.assertTrue(ue <= g.h["last"])
    tc.assertEqual((vs * sector) % (1 << 20), 0)
    # Backup-Header muss dieselben Eintraege tragen
    back = bytes(g.backup[:g.h["n"] * 128])
    prim = bytes(g.primary[g.h["e_lba"] * sector:g.h["e_lba"] * sector + g.h["n"] * 128])
    tc.assertEqual(back, prim)
    # Backup-Header-CRC
    off = es * sector
    bh = bytearray(g.backup[off:off + 92])
    crc = struct.unpack_from("<I", bh, 16)[0]
    bh[16:20] = b"\0\0\0\0"
    tc.assertEqual(zlib.crc32(bytes(bh)), crc)


class Sgdisk512(unittest.TestCase):
    @unittest.skipUnless(shutil.which("sgdisk"), "sgdisk fehlt")
    def test_real_sgdisk_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            img = os.path.join(d, "disk.img")
            with open(img, "wb") as f:
                f.truncate(8 << 30)
            cmds = [["-n", "1:2048:+64M", "-t", f"1:{SYS_T}", "-c", "1:boot"],
                    ["-n", "2:0:+2G", "-t", f"2:{SYS_T}", "-c", "2:system"],
                    ["-n", "3:0:+256M", "-t", f"3:{SYS_T}", "-c", "3:cache"],
                    ["-n", "4:0:0", "-t", f"4:{UD_T}", "-c", "4:userdata"]]
            for c in cmds:
                subprocess.run(["sgdisk"] + c + [img], check=True, capture_output=True)
            self.assertEqual(T.main(["--image", img]), 0)  # Trockenlauf
            def gpt_bytes():
                with open(img, "rb") as f:
                    return f.read(34 * 512)
            before = gpt_bytes()
            self.assertEqual(T.main(["--image", img, "--write", "--backup", os.path.join(d, "bak.bin")]), 0)
            self.assertNotEqual(before, gpt_bytes())
            out = subprocess.run(["sgdisk", "-v", img], capture_output=True, text=True)
            self.assertIn("No problems found", out.stdout, out.stdout + out.stderr)
            info = subprocess.run(["sgdisk", "-p", img], capture_output=True, text=True).stdout
            self.assertIn("vendor", info)
            self.assertIn("userdata", info)
            verify_independent(self, img, 512, 1024)
            # Wiederherstellung
            self.assertEqual(T.main(["--image", img, "--restore", os.path.join(d, "bak.bin"), "--write"]), 0)
            self.assertEqual(before, gpt_bytes())
            self.assertNotIn("vendor", subprocess.run(["sgdisk", "-p", img], capture_output=True, text=True).stdout)


class Sector4096(unittest.TestCase):
    def make(self, d, ud_gib=5, n_entries=128):
        img = os.path.join(d, "ufs.img")
        s = 4096
        total_bytes = 10 << 30
        parts = [("boot", SYS_T, 256, 256 + (64 << 20) // s - 1),
                 ("system", SYS_T, (1 << 30) // s, (1 << 30) // s + (2 << 30) // s - 1),
                 ("userdata", UD_T, (4 << 30) // s, (4 << 30) // s + (ud_gib << 30) // s - 1)]
        build_gpt_image(img, s, total_bytes, parts, n_entries)
        return img

    def test_ufs_4k(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d)
            self.assertEqual(T.main(["--image", img, "--write", "--backup", os.path.join(d, "b")]), 0)
            verify_independent(self, img, 4096, 1024)

    def test_vendor_already_exists(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d)
            T.main(["--image", img, "--write", "--backup", os.path.join(d, "b")])
            self.assertEqual(T.main(["--image", img]), 2)

    def test_too_small(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d, ud_gib=1)
            self.assertEqual(T.main(["--image", img]), 2)

    def test_userdata_beyond_disk_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d, ud_gib=7)  # endet hinter dem nutzbaren Bereich
            self.assertEqual(T.main(["--image", img]), 2)

    def test_no_free_entry(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d, n_entries=3)
            self.assertEqual(T.main(["--image", img]), 2)

    def test_corrupt_crc_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            img = self.make(d)
            with open(img, "r+b") as f:
                f.seek(2 * 4096 + 5)
                c = f.read(1)
                f.seek(2 * 4096 + 5)
                f.write(bytes([c[0] ^ 0xFF]))  # Eintrag veraendern, CRC passt nicht mehr
            self.assertEqual(T.main(["--image", img, "--write", "--backup", os.path.join(d, "b")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
