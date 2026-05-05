#!/usr/bin/env bash
set -x

# Select best quality that fits under 500M:
#  1) best single file <500M
#  2) video <450M (<=1080p) + audio <50M
#  3) fallback to 720p (usually well under 500M)
FORMAT="best[filesize<500M]"
FORMAT="$FORMAT/bestvideo[filesize<450M][height<=1080]+bestaudio[filesize<50M]"
FORMAT="$FORMAT/bestvideo[height<=720]+bestaudio"
FORMAT="$FORMAT/best[height<=720]"
FORMAT="$FORMAT/best"

if [ $# -gt 0 ]; then
  YT_INPUT=("$@")
else
  YT_INPUT=(-a list.txt)
fi

yt-dlp \
  --js-runtimes node \
  --remote-components ejs:github \
  -f "$FORMAT" \
  --merge-output-format mp4 \
  --max-filesize 500M \
  -o "ytdlp_%(channel_id)s_%(id)s.%(ext)s" \
  "${YT_INPUT[@]}"

rm -rf ytdlp_*.part
