#!/usr/bin/env python3
"""Sucht im Device-Tree nach Zuweisungen an Variablen, die das Build-System von
AOSP als obsolet markiert (KATI_obsolete_var): solche Zuweisungen brechen den Build.

Die Liste kommt direkt aus build/make/core/*.mk des angegebenen AOSP-Tags.
Aufruf: scripts/check_obsolete_vars.py [AOSP-Tag] [Verzeichnis ...]
Default: android-16.0.0_r1, device/
"""
import base64
import json
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

tag = sys.argv[1] if len(sys.argv) > 1 else "android-16.0.0_r1"
roots = sys.argv[2:] or [str(Path(__file__).resolve().parent.parent / "device")]
base = f"https://android.googlesource.com/platform/build/+/refs/{'tags' if tag.startswith('android-') else 'heads'}/{tag}/core/"


CACHE = Path(tempfile.gettempdir()) / f"aosp-core-{tag}"
CACHE.mkdir(exist_ok=True)


def get(url):
    """HTTP-GET mit Cache und Wiederholung bei 429 (googlesource begrenzt die Rate)."""
    f = CACHE / re.sub(r"\W", "_", url)
    if f.exists():
        return f.read_bytes()
    for wait in (0, 5, 15, 30, 60, 90):
        time.sleep(wait or 0.2)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                f.write_bytes(r.read())
                return f.read_bytes()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise SystemExit(f"429 Too Many Requests, gab nach mehreren Versuchen auf: {url}")


listing = json.loads(get(base + "?format=JSON").split(b"\n", 1)[1])
names = [e["name"] for e in listing["entries"] if e["name"].endswith(".mk") or e["name"] == "Makefile"]
obsolete = set()
for n in names:
    text = base64.b64decode(get(base + n + "?format=TEXT")).decode(errors="replace")
    obsolete |= set(re.findall(r"KATI_obsolete_var[ (]+([A-Z][A-Z0-9_]+)", text))
print(f"{tag}: {len(obsolete)} obsolete Variablen aus {len(names)} Dateien")

hits = 0
rx = re.compile(r"^\s*(?:override\s+)?(%s)\s*[:+?]*=" % "|".join(sorted(obsolete)))
for root in roots:
    for f in Path(root).rglob("*.mk"):
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            m = rx.match(line)
            if m:
                hits += 1
                print(f"{f}:{i}: {m.group(1)}")
print("FEHLER: obsolete Zuweisungen gefunden" if hits else "ok: keine obsoleten Zuweisungen")
sys.exit(1 if hits else 0)
