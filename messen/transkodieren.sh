#!/bin/sh
# 4K-HEVC -> 1080p-H.264 auf der eingebauten Arc-iGPU (VAAPI), gibt Bilder je Sekunde aus.
#   transkodieren.sh anlegen      erzeugt einmal den 60-s-Testclip
#   transkodieren.sh              ein Durchlauf
set -eu
DIR=$(cd "$(dirname "$0")" && pwd)
ARC=$(readlink -f /dev/dri/by-path/pci-0000:00:02.0-render)
FF="docker run --rm --device $ARC -v $DIR:/w --entrypoint ffmpeg linuxserver/ffmpeg -hide_banner -loglevel error -stats"
if [ "${1:-}" = anlegen ]; then
  $FF -y -vaapi_device $ARC -f lavfi -i testsrc2=size=3840x2160:rate=30 -t 60 -vf format=nv12,hwupload -c:v hevc_vaapi -b:v 40M /w/testclip-4k.mkv
  ls -la "$DIR/testclip-4k.mkv"; exit 0
fi
$FF -benchmark -hwaccel vaapi -hwaccel_device $ARC -hwaccel_output_format vaapi -i /w/testclip-4k.mkv \
  -vf scale_vaapi=w=1920:h=1080 -c:v h264_vaapi -b:v 8M -f null - 2>&1 | tr '\r' '\n' | grep -E "^frame=|rtime" | tail -2
