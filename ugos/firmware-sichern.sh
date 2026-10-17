#!/bin/bash
# Sichert die nachgelegte gfx1100-Firmware nach /volume1/gpu-firmware (ueberlebt UGOS-Updates),
# damit firmware-pruefen.sh sie nach einem Update zurueckkopieren kann.

set -uo pipefail
BASE=/volume1/gpu-firmware
FW=/lib/firmware/amdgpu
mkdir -p "$BASE/files"

FILES="dcn_3_2_0_dmcub.bin gc_11_0_0_imu.bin gc_11_0_0_me.bin gc_11_0_0_mec.bin
gc_11_0_0_mes1.bin gc_11_0_0_mes_2.bin gc_11_0_0_mes.bin gc_11_0_0_pfp.bin
gc_11_0_0_rlc_1.bin gc_11_0_0_rlc.bin psp_13_0_0_sos.bin psp_13_0_0_ta.bin
sdma_6_0_0.bin smu_13_0_0.bin vcn_4_0_0.bin"

n=0
for f in $FILES; do
  if [ -f "$FW/$f" ]; then cp -p "$FW/$f" "$BASE/files/$f"; n=$((n+1))
  else echo "FEHLT bereits: $f"; fi
done
( cd "$BASE/files" && md5sum * > "$BASE/manifest.md5" )
tar -czf "$BASE/amdgpu-gfx1100-20250410.tar.gz" -C "$BASE" files manifest.md5
echo "gesichert: $n Dateien, Archiv $(du -h "$BASE/amdgpu-gfx1100-20250410.tar.gz" | cut -f1)"
install -m 755 "$(dirname "$0")/firmware-pruefen.sh" "$BASE/firmware-pruefen.sh"
echo "Pruefskript nach $BASE kopiert. Unit einrichten: amdgpu-gfx1100-restore.service nach /etc/systemd/system, dann systemctl enable."
