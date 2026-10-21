#!/bin/bash
# Fein-Mitschnitt rund um ein erwartetes Dock-Ereignis (Wochenrhythmus: So ~17:14:45, Mi ~18:43, Stand 15.10.2026).
# Schreibt sekundengenau: neue Kernel-Meldungen, Linkwechsel, AER-Zähler an Dock-Port (00:06.0), NVMe-Port (00:06.2)
# und 10-GbE-Port (00:1c.6), Linkstatus, Leistung der Karte; dazu Slot- und Linkstatus per lspci am Anfang und Ende.
# Nur lesend, braucht root (dmesg, lspci -vvv). Fassung 2 vom 15.10.2026.
# Aufruf:  sudo /volume1/gpu-wacht/mitschnitt.sh 600        # sofort, 600 s lang
# Termine: per systemd-run --on-calendar (siehe Notiz „Dock-Ausfälle der XTX — Ursachensuche“).
set -u
DAUER=${1:-600}
ZIEL=/volume1/gpu-wacht/mitschnitt-$(date +%Y%m%d-%H%M).log
P=/sys/bus/pci/devices/0000:00:06.0
PORTS="0000:00:06.0 0000:00:06.2 0000:00:1c.6"
K=$(ls -d /sys/class/drm/card*/device 2>/dev/null | while read d; do [ "$(cat $d/vendor 2>/dev/null)" = 0x1002 ] && echo $d; done | head -1)
schnappschuss(){ echo "## lspci 00:06.0 $(date -Is)"; lspci -vvv -s 00:06.0 2>&1 | grep -E "LnkSta:|SltSta|SltCtl|DevSta"; }
{
  echo "# Mitschnitt ab $(date -Is), $DAUER s"
  schnappschuss
  dmesg -W --time-format iso &                     # nur NEUE Kernel-Meldungen, mit Zeitstempel
  D=$!
  ip -ts monitor link &                            # Linkwechsel aller Netzwerkschnittstellen
  I=$!
  for i in $(seq 1 "$DAUER"); do
    aer=""
    for p in $PORTS; do
      n=$(grep -oE "TOTAL_ERR_COR [0-9]+" /sys/bus/pci/devices/$p/aer_dev_correctable 2>/dev/null | cut -d' ' -f2)
      aer="$aer ${p:8}=${n:-–}"
    done
    w=$([ -n "$K" ] && cat $K/hwmon/hwmon*/power1_average 2>/dev/null)
    echo "$(date +%H:%M:%S.%N | cut -c1-12) link=$(cat $P/current_link_speed 2>/dev/null | cut -d' ' -f1)/x$(cat $P/current_link_width 2>/dev/null) aer$aer karte_uW=${w:-–}"
    sleep 1
  done
  kill $D $I 2>/dev/null
  schnappschuss
  echo "# Ende $(date -Is)"
} > "$ZIEL" 2>&1
echo "geschrieben: $ZIEL"
