#!/usr/bin/env python3
"""Make an H.264/AAC MP4, replacing the input only after successful conversion."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def probe(path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def compatible_video(stream):
    return stream.get('codec_name') == 'h264' and stream.get('pix_fmt') == 'yuv420p'


def convert(source, destination=None):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve() if destination else source
    if destination.suffix.lower() != '.mp4':
        raise ValueError('The output must have an .mp4 extension; supply an output path for other inputs.')
    if destination != source and destination.exists():
        raise FileExistsError(f'Refusing to overwrite {destination}')

    info = probe(source)
    videos = [s for s in info['streams'] if s['codec_type'] == 'video'
              and not s.get('disposition', {}).get('attached_pic')]
    audio = [s for s in info['streams'] if s['codec_type'] == 'audio']
    if not videos:
        raise ValueError(f'No video stream in {source}')
    video = videos[0]
    copy_video = compatible_video(video)
    copy_audio = all(s.get('codec_name') == 'aac' for s in audio)
    is_mp4 = 'mp4' in info['format'].get('format_name', '').split(',')
    if copy_video and copy_audio and is_mp4:
        if destination != source:
            # Exclusive creation protects an existing file even if it appeared after probing.
            with destination.open('xb') as output, source.open('rb') as original:
                shutil.copyfileobj(original, output)
        print(f'Already compatible: {destination}', flush=True)
        return

    fd, temporary = tempfile.mkstemp(prefix='.iphone-', suffix='.mp4', dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        command = [
            'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-stats', '-stats_period', '30',
            '-nostdin', '-y', '-xerror',
            '-threads', '8', '-i', str(source),
            '-map', f'0:{video["index"]}', '-map', '0:a?',
            '-map_metadata', '0', '-map_chapters', '0',
        ]
        if copy_video:
            command += ['-c:v', 'copy']
        else:
            filters = []
            if video.get('color_transfer') in ('smpte2084', 'arib-std-b67'):
                # Convert HDR to SDR before reducing to 8-bit H.264.
                filters += [
                    'zscale=t=linear:npl=100', 'format=gbrpf32le', 'zscale=p=bt709',
                    'tonemap=tonemap=hable:desat=0', 'zscale=t=bt709:m=bt709:r=limited',
                ]
                command += ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']
            filters += ['pad=ceil(iw/2)*2:ceil(ih/2)*2', 'format=yuv420p']
            command += [
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-profile:v', 'high',
                '-threads', '8', '-vf', ','.join(filters), '-pix_fmt', 'yuv420p',
            ]
        command += ['-c:a', 'copy'] if copy_audio else ['-c:a', 'aac', '-b:a', '160k']
        command += ['-movflags', '+faststart', '-f', 'mp4', str(temporary)]
        print(f'Preparing iPhone video: {source.name} (video: {"copy" if copy_video else "H.264"}, '
              f'audio: {"copy" if copy_audio else "AAC"})', flush=True)
        subprocess.run(command, check=True)

        result = probe(temporary)
        result_video = [s for s in result['streams'] if s['codec_type'] == 'video']
        result_audio = [s for s in result['streams'] if s['codec_type'] == 'audio']
        if (len(result_video) != 1 or not compatible_video(result_video[0])
                or len(result_audio) != len(audio)
                or any(s.get('codec_name') != 'aac' for s in result_audio)):
            raise ValueError('Conversion did not produce the expected H.264/AAC streams.')
        source_duration = float(info['format'].get('duration', 0))
        result_duration = float(result['format'].get('duration', 0))
        if source_duration and abs(source_duration - result_duration) > 1:
            raise ValueError('Converted duration differs from the input; keeping the original.')
        shutil.copystat(source, temporary)
        if destination == source:
            os.replace(temporary, destination)
        else:
            # Publish without overwriting a file created while ffmpeg was running.
            os.link(temporary, destination)
        print(f'iPhone-compatible MP4 ready: {destination}', flush=True)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path, nargs='?', help='Save a separate copy; defaults to replacing input.')
    args = parser.parse_args()
    try:
        convert(args.input, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'iPhone conversion failed: {error}\n')
