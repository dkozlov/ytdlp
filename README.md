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

Format sorting keeps the extractor's language preference first, then prefers
H.264 video, AAC audio, and SDR to reduce conversion work. See yt-dlp's
[format sorting documentation](https://github.com/yt-dlp/yt-dlp#sorting-formats).

### iPhone playback

Downloads are checked after merging/remuxing. H.264 video with 8-bit 4:2:0
pixels and AAC audio can be kept as-is; other codecs are converted to these
formats in MP4. Original audio remains preferred even when it needs conversion
from Opus. HDR video is tone-mapped to SDR when converting. A failed conversion
leaves the downloaded input intact and reports an error.

Conversion takes additional time and can increase file size: the 500 MB limit
applies to downloaded streams, not the final converted file.

To repair an existing download while keeping the original (requires Python 3,
ffmpeg, and ffprobe on your computer):

```bash
python3 iphone_compatible.py input.mp4 output_iphone.mp4
```

Omit the output path to replace an MP4 in place after a successful conversion.
Existing files at a separate output path are never overwritten.

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
| `iphone_compatible.py` | Checks codecs and converts incompatible streams for iPhone playback |
| `upload.sh` | Uploads downloaded files to an FTP server |
