set -x

FTP_HOST="${1:-192.168.1.119}"
FTP_PORT="${2:-2121}"
FTP_USER="${3:-asdf}"
FTP_PASS="${4:-12345678}"

if ! [ -x "$(command -v ftp)" ]; then
  echo 'ftp is not installed.' >&2
  apt update -y && \
  apt install -y ftp
fi

if ! timeout 5 bash -c "echo >/dev/tcp/$FTP_HOST/$FTP_PORT" 2>/dev/null; then
  echo "FTP server $FTP_HOST:$FTP_PORT is not reachable." >&2
  exit 1
fi

DIRNAME="video_$(date '+%Y%m%d_%H_%M_%S')"

ftp -P "$FTP_PORT" -n "$FTP_HOST" <<EOF
user $FTP_USER $FTP_PASS
mkdir /Download/$DIRNAME
quit
EOF

for FILENAME in ytdlp_*; do ftp -P "$FTP_PORT" -u "ftp://$FTP_USER:$FTP_PASS@$FTP_HOST/Download/$DIRNAME/$FILENAME" "./$FILENAME" ; done
