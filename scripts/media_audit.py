"""Probe and fully decode a video without modifying it or exposing local paths."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('video', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--max-bytes', type=int)
    parser.add_argument('--expected-duration', type=float)
    parser.add_argument('--duration-tolerance', type=float, default=0.1)
    args = parser.parse_args()
    if not args.video.is_file():
        parser.error('Input video does not exist')
    if args.report.exists():
        parser.error('Report already exists; choose a new report path')
    if args.duration_tolerance < 0 or (args.max_bytes is not None and args.max_bytes <= 0):
        parser.error('Invalid tolerance or byte limit')
    if not shutil.which('ffprobe') or not shutil.which('ffmpeg'):
        parser.error('ffmpeg and ffprobe must be provided on PATH')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                            '-of', 'json', str(args.video)], capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    if probe.returncode:
        parser.error('ffprobe failed; inspect the media locally')
    data = json.loads(probe.stdout)
    streams = data.get('streams', [])
    duration = float(data.get('format', {}).get('duration', 0))
    has_video = any(s.get('codec_type') == 'video' for s in streams)
    has_audio = any(s.get('codec_type') == 'audio' for s in streams)
    before = args.video.stat()
    digest = hashlib.sha256()
    with args.video.open('rb') as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i',
                              str(args.video), '-map', '0:v:0', '-map', '0:a?',
                              '-f', 'null', '-'], capture_output=True)
    after = args.video.stat()
    stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    under_limit = args.max_bytes is None or before.st_size < args.max_bytes
    duration_matches = args.expected_duration is None or abs(duration - args.expected_duration) <= args.duration_tolerance
    passed = has_video and has_audio and duration > 0 and decoded.returncode == 0 and stable and under_limit and duration_matches
    keys = ('codec_type', 'codec_name', 'width', 'height', 'avg_frame_rate', 'sample_rate', 'channels')
    report = {
        'filename': args.video.name, 'bytes': before.st_size, 'sha256': digest.hexdigest(),
        'duration_seconds': duration, 'streams': [{k:s[k] for k in keys if k in s} for s in streams],
        'has_video':has_video, 'has_audio':has_audio, 'full_decode_passed':decoded.returncode == 0,
        'source_stable_during_check':stable, 'limit_bytes':args.max_bytes, 'under_limit':under_limit,
        'expected_duration':args.expected_duration, 'duration_matches':duration_matches,
        'file_checks_passed':passed, 'visual_review':'not_performed', 'listening_review':'not_performed',
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({'file_checks_passed':passed, 'full_decode_passed':decoded.returncode == 0}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
