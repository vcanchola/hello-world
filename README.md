# audiobook-builder

A Python CLI that builds **M4B audiobooks** compatible with Apple Books.

Two modes:
- **`from-text`** — converts `.txt`, `.epub`, or `.pdf` to speech via OpenAI TTS, then packages as M4B
- **`from-audio`** — packages existing audio files (MP3, WAV, M4A, etc.) into M4B with chapters and metadata

M4B is Apple's native audiobook format. It supports chapter navigation, cover art, and remembers your playback position.

---

## Requirements

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html) installed on your PATH
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
  - Windows: download from ffmpeg.org
- An [OpenAI API key](https://platform.openai.com/api-keys) (only needed for `from-text`)

## Installation

```bash
git clone https://github.com/vcanchola/audiobook-builder.git
cd audiobook-builder
pip install -e .
```

---

## Usage

### Convert a book file to an audiobook

```bash
audiobook-builder from-text mybook.epub \
  --title "My Book" \
  --author "Jane Doe" \
  --voice nova \
  --cover cover.jpg
```

This reads `mybook.epub`, splits it into chapters, synthesizes each chapter with OpenAI TTS, and outputs `My_Book.m4b`.

**Options:**

| Flag | Description | Default |
|------|-------------|--------|
| `--title / -t` | Audiobook title | filename |
| `--author / -a` | Author name | `Unknown` |
| `--narrator / -n` | Narrator name | |
| `--year / -y` | Publication year | |
| `--cover / -c` | Cover image path (JPG/PNG) | |
| `--voice` | TTS voice: `alloy` `echo` `fable` `onyx` `nova` `shimmer` | `alloy` |
| `--model` | `tts-1` (faster) or `tts-1-hd` (higher quality) | `tts-1-hd` |
| `--output / -o` | Output `.m4b` path | `<title>.m4b` |
| `--keep-work-dir` | Keep the per-chapter MP3s after packaging | off |

Requires the `OPENAI_API_KEY` environment variable to be set.

---

### Package existing audio files

```bash
audiobook-builder from-audio ch1.mp3 ch2.mp3 ch3.mp3 \
  --title "My Book" \
  --author "Jane Doe" \
  --cover cover.jpg
```

Each file becomes one chapter. Chapter names are inferred from filenames (leading numbers stripped) or supplied via a names file.

**Options:**

| Flag | Description | Default |
|------|-------------|--------|
| `--title / -t` | Audiobook title | *required* |
| `--author / -a` | Author name | `Unknown` |
| `--narrator / -n` | Narrator name | |
| `--year / -y` | Publication year | |
| `--cover / -c` | Cover image path (JPG/PNG) | |
| `--chapter-names` | Text file with one chapter name per line | |
| `--output / -o` | Output `.m4b` path | `<title>.m4b` |

---

## Project structure

```
audiobook_builder/
├── cli.py         # Click-based CLI entry points
├── extractor.py   # Text extraction from .txt / .epub / .pdf
├── tts.py         # OpenAI TTS synthesis with chunking
├── packager.py    # M4B creation via ffmpeg
└── models.py      # Chapter and BookMetadata dataclasses
```
