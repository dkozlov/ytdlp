"""Integration checks for the iPhone conversion helper (requires FFmpeg)."""

import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).with_name("iphone_compatible.py")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe are required")
class IPhoneCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoders = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            check=True, capture_output=True, text=True,
        ).stdout
        if "libx264" not in cls.encoders or "libopus" not in cls.encoders:
            raise unittest.SkipTest("FFmpeg needs libx264 and libopus encoders")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def make_video(self, name="input.mp4", video="libx264", audio="aac", transfer=None,
                   duration="0.6", faststart=False):
        path = self.directory / name
        command = [
            "ffmpeg", "-v", "error", "-nostdin", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=5",
        ]
        if audio:
            command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
        command += ["-t", duration, "-c:v", video, "-pix_fmt",
                    "yuv420p10le" if transfer else "yuv420p", "-threads", "2"]
        if transfer:
            command += ["-color_primaries", "bt2020", "-color_trc", transfer,
                        "-colorspace", "bt2020nc"]
        if video == "libaom-av1":
            command += ["-cpu-used", "8"]
        if audio:
            command += ["-c:a", audio, "-metadata:s:a:0", "language=fra"]
        if faststart:
            command += ["-movflags", "+faststart"]
        command += [str(path)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return path

    def run_helper(self, *paths, env=None, success=True):
        result = subprocess.run(
            [sys.executable, str(HELPER), *map(str, paths)],
            capture_output=True, text=True, env=env,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def probe(self, path):
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        return json.loads(result.stdout)

    def packet_hashes(self, path, stream):
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", stream,
             "-show_packets", "-show_data_hash", "sha256",
             "-show_entries", "packet=data_hash", "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        return [packet["data_hash"] for packet in json.loads(result.stdout)["packets"]]

    def assert_compatible(self, path, audio=True):
        info = self.probe(path)
        self.assertIn("mp4", info["format"]["format_name"])
        videos = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
        audios = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["codec_name"], "h264")
        self.assertEqual(videos[0]["pix_fmt"], "yuv420p")
        self.assertEqual(len(audios), int(audio))
        if audio:
            self.assertEqual(audios[0]["codec_name"], "aac")
            self.assertEqual(audios[0]["tags"]["language"], "fra")

    def assert_faststart(self, path):
        atoms = []
        with path.open("rb") as video:
            while header := video.read(8):
                size, kind = struct.unpack(">I4s", header)
                header_size = 8
                if size == 1:
                    size = struct.unpack(">Q", video.read(8))[0]
                    header_size = 16
                atoms.append(kind)
                if not size:
                    break
                video.seek(size - header_size, os.SEEK_CUR)
        self.assertLess(atoms.index(b"moov"), atoms.index(b"mdat"))

    def test_av1_opus_becomes_h264_aac(self):
        if "libaom-av1" not in self.encoders:
            self.skipTest("FFmpeg needs libaom-av1 for this fixture")
        source = self.make_video(video="libaom-av1", audio="libopus")
        self.run_helper(source)
        self.assert_compatible(source)
        self.assert_faststart(source)

    def test_audio_conversion_keeps_original_video_packets(self):
        source = self.make_video("original language.mp4", audio="libopus")
        before = self.packet_hashes(source, "v:0")
        self.run_helper(source)
        self.assert_compatible(source)
        self.assertEqual(self.packet_hashes(source, "v:0"), before)
        self.assert_faststart(source)

    def test_hdr_video_is_tonemapped_to_sdr(self):
        if "libaom-av1" not in self.encoders:
            self.skipTest("FFmpeg needs libaom-av1 for this fixture")
        for transfer in ("smpte2084", "arib-std-b67"):
            with self.subTest(transfer=transfer):
                source = self.make_video(
                    name=f"{transfer}.mp4", video="libaom-av1", transfer=transfer,
                )
                self.assertEqual(self.probe(source)["streams"][0]["color_transfer"], transfer)
                self.run_helper(source)
                self.assert_compatible(source)
                video = self.probe(source)["streams"][0]
                self.assertEqual(video["color_transfer"], "bt709")
                self.assertEqual(video["color_primaries"], "bt709")
                self.assertEqual(video["color_space"], "bt709")

    def test_compatible_streams_are_not_reencoded(self):
        source = self.make_video()
        video_before = self.packet_hashes(source, "v:0")
        audio_before = self.packet_hashes(source, "a:0")
        self.run_helper(source)
        self.assert_compatible(source)
        self.assertEqual(self.packet_hashes(source, "v:0"), video_before)
        self.assertEqual(self.packet_hashes(source, "a:0"), audio_before)

    def test_separate_output_preserves_input_and_handles_quoted_paths(self):
        source = self.make_video("speaker's original video.mp4", video="mpeg4", audio="libopus")
        original = source.read_bytes()
        output = self.directory / "speaker's iPhone copy.mp4"
        self.run_helper(source, output)
        self.assertEqual(source.read_bytes(), original)
        self.assert_compatible(output)
        self.assert_faststart(output)

    def test_silent_video_is_supported(self):
        source = self.make_video(video="mpeg4", audio=None)
        self.run_helper(source)
        self.assert_compatible(source, audio=False)

    def test_existing_output_is_not_overwritten(self):
        source = self.make_video(video="mpeg4")
        original = source.read_bytes()
        output = self.directory / "existing.mp4"
        output.write_bytes(b"do not overwrite")
        self.run_helper(source, output, success=False)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(output.read_bytes(), b"do not overwrite")

    def test_corrupt_input_is_preserved(self):
        source = self.directory / "broken.mp4"
        source.write_bytes(b"not a video")
        self.run_helper(source, success=False)
        self.assertEqual(source.read_bytes(), b"not a video")
        self.assertEqual(set(self.directory.iterdir()), {source})

    def test_truncated_video_is_rejected_without_replacing_input(self):
        source = self.make_video(video="mpeg4", duration="2", faststart=True)
        self.assert_faststart(source)
        complete = source.read_bytes()
        truncated = complete[:len(complete) * 4 // 5]
        source.write_bytes(truncated)
        # The metadata remains readable, even though media packets are missing.
        self.assertGreaterEqual(float(self.probe(source)["format"]["duration"]), 2)
        self.run_helper(source, success=False)
        self.assertEqual(source.read_bytes(), truncated)
        self.assertEqual(set(self.directory.iterdir()), {source})

    @unittest.skipIf(os.name == "nt", "uses a shell executable to simulate an FFmpeg failure")
    def test_failed_conversion_preserves_input_and_cleans_temporary_output(self):
        source = self.make_video(video="mpeg4")
        original = source.read_bytes()
        fake_bin = self.directory / "bin"
        fake_bin.mkdir()
        fake_ffmpeg = fake_bin / "ffmpeg"
        fake_ffmpeg.write_text("#!/bin/sh\nexit 7\n")
        fake_ffmpeg.chmod(0o755)
        env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))
        self.run_helper(source, env=env, success=False)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(set(self.directory.iterdir()), {source, fake_bin})


if __name__ == "__main__":
    unittest.main()
