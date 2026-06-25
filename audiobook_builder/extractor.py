import re
from pathlib import Path
from typing import List

from .models import Chapter

_CHAPTER_RE = re.compile(
    r'^(?:chapter|part|section|book|prologue|epilogue|preface|introduction|conclusion)\b.*',
    re.IGNORECASE,
)
_NUMBERED_RE = re.compile(r'^\d+[\.)\]\s+.{1,80}$')


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 120:
        return False
    return bool(_CHAPTER_RE.match(s)) or bool(_NUMBERED_RE.match(s))


def _split_by_headings(text: str, fallback_title: str) -> List[Chapter]:
    lines = text.splitlines()
    chapters: List[Chapter] = []
    current_title: str = fallback_title
    current_lines: List[str] = []

    for line in lines:
        if _is_heading(line):
            body = '\n'.join(current_lines).strip()
            if body:
                chapters.append(Chapter(title=current_title, text=body))
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    body = '\n'.join(current_lines).strip()
    if body:
        chapters.append(Chapter(title=current_title, text=body))

    if not chapters:
        chapters = [Chapter(title=fallback_title, text=text.strip())]

    return [c for c in chapters if c.text]


def _from_txt(path: Path) -> List[Chapter]:
    text = path.read_text(encoding='utf-8', errors='replace')
    return _split_by_headings(text, path.stem)


def _from_epub(path: Path) -> List[Chapter]:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "ePub support requires: pip install ebooklib beautifulsoup4"
        )

    book = epub.read_epub(str(path))
    chapters: List[Chapter] = []

    for idref, _linear in book.spine:
        item = book.get_item_with_id(idref)
        if item is None:
            continue

        soup = BeautifulSoup(item.get_content(), 'html.parser')

        heading = soup.find(['h1', 'h2', 'h3'])
        title = heading.get_text(strip=True) if heading else item.get_name()

        for tag in soup.find_all(['h1', 'h2', 'h3', 'script', 'style', 'nav']):
            tag.decompose()

        text = soup.get_text(separator='\n', strip=True)
        if text:
            chapters.append(Chapter(title=title, text=text))

    if not chapters:
        raise ValueError("No readable content found in ePub.")

    return chapters


def _from_pdf(path: Path) -> List[Chapter]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PDF support requires: pip install PyMuPDF")

    doc = fitz.open(str(path))
    toc = doc.get_toc()  # [[level, title, page], ...]

    if toc:
        chapters: List[Chapter] = []
        top_level = toc[0][0]
        filtered = [(lvl, title, pg) for lvl, title, pg in toc if lvl <= top_level + 1]

        for i, (_, title, start_pg) in enumerate(filtered):
            end_pg = filtered[i + 1][2] if i + 1 < len(filtered) else len(doc) + 1
            text = '\n'.join(doc[p].get_text() for p in range(start_pg - 1, min(end_pg - 1, len(doc))))
            if text.strip():
                chapters.append(Chapter(title=title, text=text.strip()))

        return chapters

    full_text = '\n'.join(page.get_text() for page in doc)
    return _split_by_headings(full_text, path.stem)


def extract(path: Path) -> List[Chapter]:
    suffix = path.suffix.lower()
    if suffix == '.txt':
        return _from_txt(path)
    elif suffix == '.epub':
        return _from_epub(path)
    elif suffix == '.pdf':
        return _from_pdf(path)
    else:
        raise ValueError(f"Unsupported format '{suffix}'. Supported: .txt, .epub, .pdf")
