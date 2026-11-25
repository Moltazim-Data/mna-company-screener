"""Read a company website and turn it into clean text sections.

Works with a local HTML file (sample data) or a live URL. Navigation, footer,
scripts and styles are removed so only real content reaches the retriever.
"""
from html.parser import HTMLParser
from pathlib import Path

import requests

SKIP_TAGS = {"script", "style", "nav", "footer", "noscript", "header"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "td"}


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip_depth = 0
        self.section = "General"
        self.current_heading = None
        self.buffer = []
        self.blocks = []            # (section, text)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag in ("h1", "h2", "h3"):
            self.current_heading = []

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in ("h1", "h2", "h3") and self.current_heading is not None:
            self.section = " ".join("".join(self.current_heading).split()) or self.section
            self.current_heading = None
            self.buffer = []
            return
        if tag in BLOCK_TAGS:
            text = " ".join("".join(self.buffer).split())
            if text:
                self.blocks.append((self.section, text))
            self.buffer = []

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.current_heading is not None:
            self.current_heading.append(data)
        else:
            self.buffer.append(data)


def html_to_blocks(html: str) -> list[tuple[str, str]]:
    """Return [(section_title, paragraph_text), ...] without menus, scripts or footers."""
    parser = _Extractor()
    parser.feed(html)
    return parser.blocks


def load_html(source: str | Path, timeout: int = 15) -> str:
    """Load HTML from a local file or an http(s) URL."""
    s = str(source)
    if s.startswith(("http://", "https://")):
        resp = requests.get(s, timeout=timeout, headers={"User-Agent": "mna-company-screener/2.0"})
        resp.raise_for_status()
        return resp.text
    return Path(s).read_text(encoding="utf-8")
