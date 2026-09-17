"""Markdown-aware chunking.

Naive fixed-size chunking cuts through headers and code blocks mid-way,
which is exactly the failure mode week 2 of the study plan calls out.
Instead we split on markdown structure first (headers, then paragraphs),
and only fall back to a hard character cut if a single paragraph is
still too big.
"""

import re
from dataclasses import dataclass

from rag.config import CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS

HEADER_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    source: str
    heading: str


def _split_on_headers(markdown: str) -> list[tuple[str, str]]:
    """Return (heading, section_text) pairs. Text before the first header
    is kept under an empty heading."""
    matches = list(HEADER_RE.finditer(markdown))
    if not matches:
        return [("", markdown)]

    sections = []
    if matches[0].start() > 0:
        sections.append(("", markdown[: matches[0].start()]))

    for i, match in enumerate(matches):
        heading = match.group().lstrip("#").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        sections.append((heading, markdown[start:end]))

    return sections


def _split_paragraph(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE_CHARS:
        return [text]
    step = CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS
    return [text[i : i + CHUNK_SIZE_CHARS] for i in range(0, len(text), step)]


def chunk_markdown(markdown: str, source: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, section in _split_on_headers(markdown):
        section = section.strip()
        if not section:
            continue

        paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
        buffer = ""
        for para in paragraphs:
            candidate = f"{buffer}\n\n{para}" if buffer else para
            if len(candidate) <= CHUNK_SIZE_CHARS:
                buffer = candidate
            else:
                if buffer:
                    chunks.append(Chunk(text=buffer, source=source, heading=heading))
                pieces = _split_paragraph(para)
                for piece in pieces[:-1]:
                    chunks.append(Chunk(text=piece, source=source, heading=heading))
                buffer = pieces[-1]
        if buffer:
            chunks.append(Chunk(text=buffer, source=source, heading=heading))

    return chunks
