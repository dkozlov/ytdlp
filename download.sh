#!/usr/bin/env bash
set -x

# Try the original audio first, then fall back when it isn't identified/available.
# Apply the audio filter only to combined formats and audio-only streams.
# Within each pass, keep the existing size/quality preferences:
#  1) best single file <500M
#  2) video <450M (<=1080p) + audio <50M
#  3) fallback to 720p (usually well under 500M)
# Exclude known oversized fallback streams before --max-filesize aborts a download.
format_choices() {
  local audio_filter="${1:-}"
  local format="best${audio_filter}[filesize<500M]"
  format="$format/bestvideo[filesize<450M][height<=1080]+bestaudio${audio_filter}[filesize<50M]"
  format="$format/bestvideo[height<=720][filesize<=?500M]+bestaudio${audio_filter}[filesize<=?500M]"
  format="$format/best${audio_filter}[height<=720][filesize<=?500M]"
  format="$format/best${audio_filter}[filesize<=?500M]"
  printf '%s' "$format"
}

FORMAT="$(format_choices '[format_note~="(?i)\boriginal\b"]')/$(format_choices)"

if [ $# -gt 0 ]; then
  YT_INPUT=("$@")
else
  YT_INPUT=(-a list.txt)
fi

yt-dlp \
  --js-runtimes node \
  --remote-components ejs:github \
  -f "$FORMAT" \
  --format-sort lang \
  --merge-output-format mp4 \
  --max-filesize 500M \
  -o "ytdlp_%(channel_id)s_%(id)s.%(ext)s" \
  "${YT_INPUT[@]}"

rm -rf ytdlp_*.part
