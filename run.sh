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

$DOCKER run -it --rm \
  -e HOST_UID="$(id -u)" \
  -e HOST_GID="$(id -g)" \
  -v "$(pwd)":/work \
  -w /work \
  python:3 \
  bash -c '
    apt-get update -y && apt-get install -y --no-install-recommends ffmpeg
    groupadd -g "$HOST_GID" hostuser 2>/dev/null
    useradd -u "$HOST_UID" -g "$HOST_GID" -d /work -s /bin/bash hostuser 2>/dev/null
    runuser -u hostuser -- bash -c "
      export HOME=/work PATH=/work/.local/bin:\$PATH
      pip install -U yt-dlp
      bash ./download.sh $*
    "
  '
