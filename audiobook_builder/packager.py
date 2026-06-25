import json
import subprocess
import tempfile
from pathlib import Path
from typing import List

from .models import BookMetadata, Chapter


def _require_ffmpeg() -> None:
    if subprocess.run(['ffmpeg', '-version'], capture_output=True).returncode != 0:
        raise RuntimeError(
            "ffmpeg is required but not found.\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def _duration_ms(path: Path) -> int:
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    duration_s = float(json.loads(result.stdout)['format']['duration'])
    return int(duration_s * 1000)


def _ffmetadata(chapters: List[Chapter], meta: BookMetadata) -> str:
    lines = [
        ';FFMETADATA1',
        f'title={meta.title}',
        f'artist={meta.author}',
        f'album={meta.title}',
        'genre=Audiobook',
    ]
    if meta.narrator:
        lines.append(f'album_artist={meta.narrator}')
    if meta.year:
        lines.append(f'date={meta.year}')
    if meta.description:
        lines.append(f'description={meta.description}')
    lines.append('')

    cursor = 0
    for chapter in chapters:
        end = cursor + chapter.duration_ms
        lines += [
            '[CHAPTER]',
            'TIMEBASE=1/1000',
            f'START={cursor}',
            f'END={end}',
            f'title={chapter.title}',
            '',
        ]
        cursor = end

    return '\n'.join(lines)


def package(chapters: List[Chapter], meta: BookMetadata, output: Path) -> None:
    _require_ffmpeg()

    for chapter in chapters:
        if chapter.duration_ms == 0 and chapter.audio_path:
            chapter.duration_ms = _duration_ms(chapter.audio_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        concat_file = tmp / 'concat.txt'
        concat_file.write_text(
            '\n'.join(f"file '{ch.audio_path}'" for ch in chapters),
            encoding='utf-8',
        )

        meta_file = tmp / 'metadata.txt'
        meta_file.write_text(_ffmetadata(chapters, meta), encoding='utf-8')

        has_cover = bool(meta.cover_image and meta.cover_image.exists())

        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-i', str(meta_file),
        ]

        if has_cover:
            cmd += ['-i', str(meta.cover_image)]
            cmd += [
                '-map', '0:a',
                '-map', '2:v',
                '-map_metadata', '1',
                '-c:v', 'copy',
                '-disposition:v', 'attached_pic',
            ]
        else:
            cmd += [
                '-map', '0:a',
                '-map_metadata', '1',
                '-vn',
            ]

        cmd += ['-c:a', 'aac', '-b:a', '64k', str(output)]

        subprocess.run(cmd, check=True)
