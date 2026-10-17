#!/bin/bash
# Prueft und stellt die manuell nachgelegte gfx1100-Firmware wieder her,
# falls ein UGOS-Update /lib/firmware/amdgpu zurueckgesetzt hat.
#
#   check    nur pruefen   (Exit 0 = vollstaendig, 1 = etwas fehlt)
#   restore  fehlende oder abweichende Dateien zurueckkopieren
#   auto     wie restore, danach amdgpu neu laden, falls keine AMD-Karte da ist
set -uo pipefail
BASE=/volume1/gpu-firmware
SRC="$BASE/files"
FW=/lib/firmware/amdgpu
MODE="${1:-check}"
log(){ echo "[gfx1100-restore] $*"; }

gpu_present(){ grep -qs 0x1002 /sys/class/drm/card*/device/vendor; }

[ -d "$SRC" ] || { log "Sicherung fehlt: $SRC"; exit 2; }

missing=""
for p in "$SRC"/*.bin; do
  f=$(basename "$p")
  if   [ ! -f "$FW/$f" ];        then missing="$missing $f"
  elif ! cmp -s "$p" "$FW/$f";   then missing="$missing $f(abweichend)"
  fi
done

if [ -z "$missing" ]; then
  log "vollstaendig: $(ls "$SRC" | wc -l) Dateien vorhanden und identisch, $(ls $FW | wc -l) Dateien insgesamt"
  exit 0
fi

log "fehlend oder abweichend:$missing"
[ "$MODE" = check ] && exit 1

mkdir -p "$FW"
cp -p "$SRC"/*.bin "$FW"/ && log "wiederhergestellt nach $FW"

if [ "$MODE" = auto ]; then
  if gpu_present; then
    log "AMD-Karte ist gebunden - kein Modul-Reload noetig"
  else
    log "keine AMD-Karte gebunden, versuche Modul-Reload"
    if modprobe -r amdgpu 2>/dev/null && modprobe amdgpu 2>/dev/null; then
      sleep 3
      if gpu_present; then log "GPU nach Reload verfuegbar"; else log "GPU weiterhin nicht da - Neustart noetig"; fi
    else
      log "Reload nicht moeglich (Modul in Benutzung) - Neustart noetig"
    fi
  fi
fi
