from rag.chunking import chunk_markdown


def test_splits_on_headers():
    markdown = "# Title\n\nintro text\n\n## Section A\n\nbody a\n\n## Section B\n\nbody b"
    chunks = chunk_markdown(markdown, source="test.md")
    headings = [c.heading for c in chunks]
    assert "Section A" in headings
    assert "Section B" in headings


def test_long_paragraph_is_split_with_overlap():
    long_text = "x" * 3000
    markdown = f"## Big Section\n\n{long_text}"
    chunks = chunk_markdown(markdown, source="test.md")
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 1200


def test_empty_input_returns_no_chunks():
    assert chunk_markdown("", source="test.md") == []
