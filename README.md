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

Prefers formats whose audio is marked **original** by the source (including
YouTube), in any language, before falling back to other audio. Within each pass:

1. Best single file < 500 MB
2. Video < 450 MB (up to 1080p) + audio < 50 MB
3. Fallback to 720p

The existing 500 MB download limit still applies. Original audio may take
priority over a higher-quality dubbed version. If the source does not identify
or provide an original track that matches these choices, the usual format
fallbacks are used; these can contain translated audio.

`--format-sort lang` also keeps the extractor's language preference ahead of
quality when choosing among formats. See yt-dlp's
[format sorting documentation](https://github.com/yt-dlp/yt-dlp#sorting-formats).

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
