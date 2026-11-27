"""Parse supplied local HTML without making network requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def extract_html(
    html: str, *, base_url: str | None = None, max_links: int = 200
) -> dict[str, object]:
    if max_links < 0:
        raise ValueError("max_links cannot be negative")
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""
    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag.get("href") if canonical_tag else None
    if canonical and base_url:
        canonical = urljoin(base_url, canonical)

    headings = [
        {"level": int(tag.name[1]), "text": tag.get_text(" ", strip=True)}
        for tag in soup.find_all(["h1", "h2", "h3"])
        if tag.get_text(" ", strip=True)
    ]
    links: list[dict[str, str]] = []
    if max_links == 0:
        return {
            "title": title,
            "description": description or None,
            "canonical": canonical,
            "headings": headings,
            "links": links,
            "links_returned": 0,
            "network_requests": 0,
            "mode": "local-html-only",
        }
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        if not href:
            continue
        resolved = urljoin(base_url, href) if base_url else href
        scheme = urlsplit(resolved).scheme.lower()
        if scheme not in {"", "http", "https"}:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        links.append({"text": anchor.get_text(" ", strip=True), "href": resolved})
        if len(links) >= max_links:
            break

    return {
        "title": title,
        "description": description or None,
        "canonical": canonical,
        "headings": headings,
        "links": links,
        "links_returned": len(links),
        "network_requests": 0,
        "mode": "local-html-only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Saved local HTML file")
    parser.add_argument(
        "--base-url", default=None, help="Optional URL used only to resolve relative links"
    )
    parser.add_argument("--max-links", type=int, default=200)
    args = parser.parse_args()
    source = Path(args.file).expanduser().resolve(strict=True)
    if not source.is_file() or source.stat().st_size > 5_000_000:
        raise ValueError("input must be a file no larger than 5 MB")
    html = source.read_text(encoding="utf-8", errors="replace")
    print(
        json.dumps(extract_html(html, base_url=args.base_url, max_links=args.max_links), indent=2)
    )


if __name__ == "__main__":
    main()