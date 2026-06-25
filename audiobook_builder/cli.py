import re
import shutil
import sys
import tempfile
from pathlib import Path

import click

from .models import BookMetadata, Chapter


@click.group()
def cli():
    """Build M4B audiobooks compatible with Apple Books."""


@cli.command('from-text')
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option('--title', '-t', default=None, help='Audiobook title (defaults to filename)')
@click.option('--author', '-a', default='Unknown', show_default=True, help='Author name')
@click.option('--narrator', '-n', default='', help='Narrator name')
@click.option('--year', '-y', default='', help='Publication year')
@click.option('--cover', '-c', default=None, type=click.Path(path_type=Path), help='Cover image (JPG or PNG)')
@click.option('--voice', default='alloy', show_default=True,
              type=click.Choice(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']),
              help='OpenAI TTS voice')
@click.option('--model', default='tts-1-hd', show_default=True,
              type=click.Choice(['tts-1', 'tts-1-hd']),
              help='OpenAI TTS model (tts-1-hd = higher quality)')
@click.option('--output', '-o', default=None, type=click.Path(path_type=Path),
              help='Output path for the .m4b file')
@click.option('--keep-work-dir', is_flag=True, help='Keep intermediate per-chapter MP3s')
def from_text(input_file, title, author, narrator, year, cover, voice, model, output, keep_work_dir):
    """Convert a .txt, .epub, or .pdf file to an M4B audiobook via OpenAI TTS.

    Requires the OPENAI_API_KEY environment variable and ffmpeg installed on PATH.
    """
    from .extractor import extract
    from .packager import package
    from .tts import synthesize_chapter

    if title is None:
        title = re.sub(r'[-_]+', ' ', input_file.stem).title()

    if output is None:
        output = Path(re.sub(r'\s+', '_', title) + '.m4b')

    click.echo(f"Extracting chapters from {input_file} ...")
    chapters = extract(input_file)
    click.echo(f"Found {len(chapters)} chapter(s).")

    meta = BookMetadata(title=title, author=author, narrator=narrator, year=year, cover_image=cover)

    work_dir = Path(tempfile.mkdtemp(prefix='audiobook_'))
    try:
        click.echo(f"Synthesizing audio with OpenAI TTS (voice={voice}, model={model}) ...")
        with click.progressbar(enumerate(chapters), length=len(chapters), label='  Chapters') as bar:
            for i, chapter in bar:
                audio_path = work_dir / f'chapter_{i:03d}.mp3'
                if not audio_path.exists():
                    synthesize_chapter(
                        text=chapter.text,
                        output_path=audio_path,
                        voice=voice,
                        model=model,
                        work_dir=work_dir,
                    )
                chapter.audio_path = audio_path

        click.echo(f"Packaging {output} ...")
        package(chapters, meta, output)

        if keep_work_dir:
            click.echo(f"Work files kept in: {work_dir}")
        else:
            shutil.rmtree(work_dir, ignore_errors=True)

        click.echo(f"Done -> {output}")

    except Exception as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command('from-audio')
@click.argument('audio_files', nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option('--title', '-t', required=True, help='Audiobook title')
@click.option('--author', '-a', default='Unknown', show_default=True, help='Author name')
@click.option('--narrator', '-n', default='', help='Narrator name')
@click.option('--year', '-y', default='', help='Publication year')
@click.option('--cover', '-c', default=None, type=click.Path(path_type=Path), help='Cover image (JPG or PNG)')
@click.option('--chapter-names', default=None, type=click.Path(path_type=Path),
              help='Text file with one chapter name per line (overrides filename-based names)')
@click.option('--output', '-o', default=None, type=click.Path(path_type=Path),
              help='Output path for the .m4b file')
def from_audio(audio_files, title, author, narrator, year, cover, chapter_names, output):
    """Package existing audio files (MP3, WAV, M4A, ...) into an M4B audiobook.

    Each file becomes one chapter. Files are processed in the order given.
    Requires ffmpeg installed on PATH.
    """
    from .packager import package

    if output is None:
        output = Path(re.sub(r'\s+', '_', title) + '.m4b')

    names: list[str] = []
    if chapter_names:
        names = [l.strip() for l in chapter_names.read_text(encoding='utf-8').splitlines() if l.strip()]

    chapters: list[Chapter] = []
    for i, af in enumerate(audio_files):
        if i < len(names):
            name = names[i]
        else:
            stem = re.sub(r'^\d+[\s._-]*', '', Path(af).stem)
            name = re.sub(r'[-_]+', ' ', stem).strip() or f"Chapter {i + 1}"
        chapters.append(Chapter(title=name, audio_path=Path(af)))

    meta = BookMetadata(title=title, author=author, narrator=narrator, year=year, cover_image=cover)

    click.echo(f"Packaging {len(chapters)} chapter(s) into {output} ...")
    package(chapters, meta, output)
    click.echo(f"Done -> {output}")
