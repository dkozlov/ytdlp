#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker &>/dev/null; then
  echo "Docker not found. Installing..."
  sudo curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "Docker installed. Added $USER to docker group."
  echo "Continuing with sudo for this run..."
fi

DOCKER=docker
if ! docker info &>/dev/null; then
  DOCKER="sudo docker"
fi

# Split args that may contain multiple space-separated URLs in a single string
# This lets users single-quote a batch of URLs to protect & from the shell:
#   ./run.sh 'https://youtube.com/watch?v=aaa https://youtube.com/watch?v=bbb&t=3s'
URLS=()
for arg in "$@"; do
  for url in $arg; do
    URLS+=("$url")
  done
done

$DOCKER run --rm --init \
  -e HOST_UID="$(id -u)" \
  -e HOST_GID="$(id -g)" \
  -v "$(pwd)":/work \
  -w /work \
  python:3 \
  bash -c '
    apt-get update -y && apt-get install -y --no-install-recommends ffmpeg nodejs
    groupadd -g "$HOST_GID" hostuser 2>/dev/null
    useradd -u "$HOST_UID" -g "$HOST_GID" -d /work -s /bin/bash hostuser 2>/dev/null
    runuser -u hostuser -- bash -c "
      export HOME=/work PATH=/work/.local/bin:\$PATH
      pip install -U yt-dlp
      bash ./download.sh \"\$@\"
    " _ "$@"
  ' _ "${URLS[@]}"
