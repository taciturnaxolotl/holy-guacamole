#!/usr/bin/env bash
# Stitch Motion Canvas PNG sequence into an MP4.
# Usage: ./render.sh [output.mp4]

set -euo pipefail

OUT="${1:-output/project.mp4}"
FRAMES="output/project/%06d.png"
FPS=24

if ! ls output/project/*.png >/dev/null 2>&1; then
  echo "no frames found in output/project/" >&2
  exit 1
fi

ffmpeg -y -framerate "$FPS" -i "$FRAMES" \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 18 \
  -movflags +faststart \
  "$OUT"

echo "wrote $OUT ($(du -h "$OUT" | cut -f1))"
