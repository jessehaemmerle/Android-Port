# Gemeinsame Hilfen fuer sync.sh, build.sh und extract-blobs.sh (wird mit "source" geladen).

# Standard-Zielordner: neben diesem Repo (z.B. /mnt/daten2/lineage), NICHT im Home-Verzeichnis.
# Ueberschreiben: erstes Argument des Skripts oder Umgebungsvariable LINEAGE_ROOT.
default_root() {
  local src; src="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
  printf '%s\n' "${LINEAGE_ROOT:-$(dirname "$src")/lineage}"
}

# Naechster vorhandener Ordner oberhalb von $1 (der Zielordner existiert beim ersten Lauf noch nicht).
existing_ancestor() {
  local d="$1"
  while [ ! -d "$d" ] && [ "$d" != "/" ]; do d="$(dirname "$d")"; done
  printf '%s\n' "$d"
}

# Prueft Platz, Arbeitsspeicher und Werkzeuge. Gibt WARNUNGEN aus; Rueckgabewert 1, wenn Werkzeuge fehlen.
preflight() {
  local root="$1" where free_gb ram_kb swap_kb mem_gb missing=() t
  where="$(existing_ancestor "$root")"
  free_gb=$(df -BG --output=avail "$where" | tail -1 | tr -dc 0-9)
  echo "Zielordner: $root  (Platte von $where: ${free_gb} GB frei)"
  if (( free_gb < 350 )); then
    echo "WARNUNG: nur ${free_gb} GB frei, Quellbaum + Build brauchen ca. 350 GB." >&2
    echo "         Anderen Ordner angeben, z.B.: $0 /mnt/daten2/lineage" >&2
  fi
  # /proc/meminfo statt "free": die Ausgabe von free ist uebersetzt (Mem: / Speicher:)
  ram_kb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
  swap_kb=$(awk '/^SwapTotal:/{print $2}' /proc/meminfo)
  mem_gb=$(( (ram_kb + swap_kb) / 1024 / 1024 ))
  echo "Arbeitsspeicher: $(( ram_kb / 1024 / 1024 )) GiB RAM + $(( swap_kb / 1024 / 1024 )) GiB Swap"
  if (( mem_gb < 30 )); then
    echo "WARNUNG: nur ${mem_gb} GiB RAM+Swap, der Build will etwa 32 GiB (Swap als Puffer anlegen)." >&2
  fi
  # repo init fragt die Git-Identitaet ab und bricht ohne sie mit einem Python-Traceback ab
  if command -v git >/dev/null && { [ -z "$(git config --get user.name)" ] || [ -z "$(git config --get user.email)" ]; }; then
    cat >&2 <<'MSG'
FEHLT: Git-Identitaet. 'repo init' braucht Name und E-Mail (nur lokal fuer Git, es wird nichts gesendet).
Einmalig mit DEINEN Angaben setzen:

    git config --global user.name  "Dein Name"
    git config --global user.email "du@example.com"

MSG
    return 1
  fi
  for t in repo git git-lfs rsync python3 curl; do
    command -v "$t" >/dev/null || missing+=("$t")
  done
  if (( ${#missing[@]} )); then
    echo "FEHLT: ${missing[*]}" >&2
    if [[ " ${missing[*]} " == *" repo "* ]]; then
      cat >&2 <<'MSG'

'repo' ist Googles Werkzeug, das die vielen Git-Repositories von Android zu einem Quellbaum zusammensetzt.
Es ist kein Debian-Paket, das man sicher voraussetzen kann; die offizielle Installation:

    mkdir -p ~/bin
    curl https://storage.googleapis.com/git-repo-downloads/repo > ~/bin/repo
    chmod a+rx ~/bin/repo
    export PATH="$HOME/bin:$PATH"      # fuer immer: diese Zeile in ~/.bashrc eintragen

Danach noch einmal starten. Anleitung: https://source.android.com/docs/setup/download#installing-repo
MSG
    fi
    return 1
  fi
}
