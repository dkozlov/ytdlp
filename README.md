# ytdlp

Download videos with [yt-dlp](https://github.com/yt-dlp/yt-dlp) inside Docker and optionally upload them to an FTP server.

## Prerequisites

- Docker (auto-installed by `run.sh` if missing)

## Usage

### Download videos

Pass URLs directly:

```bash
./run.sh https://youtube.com/watch?v=VIDEO_ID
```

Pass multiple URLs (quote to protect `&` from the shell):

```bash
./run.sh 'https://youtube.com/watch?v=aaa https://youtube.com/watch?v=bbb&t=3s'
```

Or list them in `list.txt` (one per line) and run with no arguments:

```bash
./run.sh
```

Videos are saved to the current directory as `ytdlp_<channel_id>_<video_id>.mp4`.

### Format selection

Downloads the best quality that fits under 500 MB:

1. Best single file < 500 MB
2. Video < 450 MB (up to 1080p) + audio < 50 MB
3. Fallback to 720p

### Upload to FTP

```bash
bash upload.sh [HOST] [PORT] [USER] [PASS]
```

Defaults: `192.168.1.119:2121`, user `asdf`. Uploads all `ytdlp_*` files into a timestamped directory on the FTP server.

## Scripts

| Script | Purpose |
|---|---|
| `run.sh` | Runs the download inside a Docker container with ffmpeg and yt-dlp |
| `download.sh` | Invoked inside the container; calls yt-dlp with format/size constraints |
| `upload.sh` | Uploads downloaded files to an FTP server |
