import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

_MAX_CHARS = 4000  # safely under OpenAI's 4096-char limit


def _split_text(text: str) -> list[str]:
    if len(text) <= _MAX_CHARS:
        return [text]

    chunks: list[str] = []
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if len(para) > _MAX_CHARS:
            if current:
                chunks.append('\n\n'.join(current))
                current, current_len = [], 0
            # Split at sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                if current_len + len(sent) + 1 > _MAX_CHARS and current:
                    chunks.append(' '.join(current))
                    current, current_len = [], 0
                current.append(sent)
                current_len += len(sent) + 1
        elif current_len + len(para) + 2 > _MAX_CHARS:
            if current:
                chunks.append('\n\n'.join(current))
            current, current_len = [para], len(para) + 2
        else:
            current.append(para)
            current_len += len(para) + 2

    if current:
        chunks.append('\n\n'.join(current))

    return chunks or [text]


def synthesize_chapter(
    text: str,
    output_path: Path,
    voice: str = "alloy",
    model: str = "tts-1-hd",
    work_dir: Optional[Path] = None,
) -> None:
    from openai import OpenAI

    client = OpenAI()
    chunks = _split_text(text)

    if len(chunks) == 1:
        response = client.audio.speech.create(model=model, voice=voice, input=chunks[0])
        output_path.write_bytes(response.content)
        return

    # Multiple chunks: synthesize each then concatenate via ffmpeg
    tmp = Path(tempfile.mkdtemp(dir=work_dir, prefix='chunks_'))
    try:
        chunk_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            chunk_path = tmp / f'chunk_{i:04d}.mp3'
            response = client.audio.speech.create(model=model, voice=voice, input=chunk)
            chunk_path.write_bytes(response.content)
            chunk_paths.append(chunk_path)

        concat_list = tmp / 'list.txt'
        concat_list.write_text(
            '\n'.join(f"file '{p}'" for p in chunk_paths),
            encoding='utf-8',
        )
        subprocess.run(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
             '-i', str(concat_list), '-c:a', 'copy', str(output_path)],
            check=True,
            capture_output=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
