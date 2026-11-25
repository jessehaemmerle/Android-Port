#!/usr/bin/env python3
"""Wendet die OnePlus-Import-Patches (3.18) dateiweise auf den 4.4-Kernel an.

Fuer jede Datei im Patch:
  - existiert der Pfad im Ziel nicht und die Datei wird neu angelegt: Pfad bleibt;
  - existiert der Pfad nicht, aber eine Datei gleichen Namens im selben
    Teilbaum (z.B. drivers/power/qpnp-fg.c -> drivers/power/supply/qcom/qpnp-fg.c):
    Pfad wird umgebogen;
  - sonst unveraendert.
Ergebnis pro Datei: ok / fuzz / reject / fehlt. Rejects bleiben als *.rej liegen.

Aufruf: apply_op_patches.py [--skip REGEX] KERNEL_DIR PATCH [PATCH ...]
  --skip: Dateien, deren Pfad auf REGEX passt (und die schon im Ziel existieren), werden nicht angefasst.

Es wird bewusst mit Fuzz 0 gepatcht: ein Hunk, dessen Kontext nicht exakt passt, wird abgelehnt
statt an eine falsche Stelle gesetzt.
"""
import os
import re
import subprocess
import sys

argv = sys.argv[1:]
skip = None
if argv and argv[0] == "--skip":
    skip = re.compile(argv[1])
    argv = argv[2:]
kdir, patches = argv[0], [os.path.abspath(p) for p in argv[1:]]
os.chdir(kdir)


def find_target(path):
    if os.path.exists(path):
        return path
    base = os.path.basename(path)
    top = "/".join(path.split("/")[:2])
    hits = []
    for root, _, files in os.walk(top):
        if base in files:
            hits.append(os.path.join(root, base))
    return hits[0] if len(hits) == 1 else None


def split(text):
    parts = re.split(r"(?m)^(?=diff --git )", text)
    return parts[0], [p for p in parts[1:] if p.strip()]


for pf in patches:
    head, files = split(open(pf, errors="replace").read())
    print(f"== {os.path.basename(pf)}: {len(files)} Dateien")
    for d in files:
        m = re.match(r"diff --git a/(\S+) b/(\S+)", d)
        path = m.group(2)
        is_new = "\nnew file mode" in d[:300]
        target = path if is_new else find_target(path)
        if skip and skip.search(path) and not is_new:
            print(f"   SKIP    {path}")
            continue
        if target is None:
            print(f"   FEHLT   {path}")
            continue
        if target != path:
            d = d.replace(f"a/{path}", f"a/{target}").replace(f"b/{path}", f"b/{target}")
        if is_new and os.path.exists(target):
            print(f"   EXISTIERT {target}")
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        r = subprocess.run(
            ["patch", "-p1", "-F0", "-N", "--no-backup-if-mismatch", "-s"],
            input=d, text=True, capture_output=True)
        tag = "ok     " if r.returncode == 0 else "REJECT "
        note = f" (von {path})" if target != path else ""
        print(f"   {tag} {target}{note}")
