"""Basic tests for HN and ArXiv sensors."""
import sys
import os

# sensors use `from sensors.base import ...` so src/ must be on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sensors.hacker_news import fetch_top_stories, HNStory
from sensors.arxiv_ai import fetch_ai_papers, ArxivPaper


def test_hn_import():
    """HNStory dataclass can be instantiated."""
    story = HNStory(
        id=1,
        title="Test",
        url="https://example.com",
        score=100,
        by="user",
        descendants=10,
    )
    assert isinstance(story, HNStory)
    assert story.hn_url == "https://news.ycombinator.com/item?id=1"


def test_arxiv_import():
    """ArxivPaper dataclass can be instantiated."""
    paper = ArxivPaper(
        id="2401.00001v1",
        title="Test Paper",
        summary="A test summary.",
        authors=["Alice"],
        published="2024-01-01",
        categories=["cs.AI"],
    )
    assert isinstance(paper, ArxivPaper)
    assert paper.url == "https://arxiv.org/abs/2401.00001v1"
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.00001v1.pdf"


def test_fetch_top_stories_returns_list():
    """fetch_top_stories returns a list."""
    result = fetch_top_stories(limit=2)
    assert isinstance(result, list)
    if result:
        assert isinstance(result[0], HNStory)


def test_fetch_ai_papers_returns_list():
    """fetch_ai_papers returns a list."""
    result = fetch_ai_papers(limit=2)
    assert isinstance(result, list)
    if result:
        assert isinstance(result[0], ArxivPaper)
