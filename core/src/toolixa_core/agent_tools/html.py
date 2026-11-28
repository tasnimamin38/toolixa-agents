"""Bounded extraction from a supplied local HTML file; no network access."""

from __future__ import annotations

import posixpath
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from toolixa_core.agent_tools.workspace import read_workspace_text
from toolixa_core.tools.base import ToolCallContext, ToolSpec


class _DocumentParser(HTMLParser):
    def __init__(self, base_url: str | None, max_links: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.max_links = max_links
        self.title_parts = []
        self.headings = []
        self.links = []
        self.description = None
        self.canonical = None
        self._capture = None
        self._buffer = []
        self._heading_level = None
        self._seen_links = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title":
            self._capture, self._buffer = "title", []
        elif tag in {"h1", "h2", "h3"}:
            self._capture, self._buffer, self._heading_level = "heading", [], int(tag[1])
        elif tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content", "").strip()[:1000] or None
        elif tag == "link" and "canonical" in values.get("rel", "").lower():
            candidate = values.get("href", "").strip()
            if candidate:
                self.canonical = urljoin(self.base_url or "", candidate)
        elif tag == "a" and "href" in values and len(self.links) < self.max_links:
            href = values["href"].strip()
            resolved = urljoin(self.base_url or "", href)
            scheme = urlsplit(resolved).scheme.lower()
            if href and scheme in {"", "http", "https"} and resolved not in self._seen_links:
                self._seen_links.add(resolved)
                self.links.append({"href": resolved, "text": ""})
                self._capture, self._buffer = "link", []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._capture == "title":
            self.title_parts.append(" ".join(" ".join(self._buffer).split())[:300])
            self._capture = None
        elif tag in {"h1", "h2", "h3"} and self._capture == "heading":
            value = " ".join(" ".join(self._buffer).split())
            if value and len(self.headings) < 150:
                self.headings.append({"level": self._heading_level, "text": value[:500]})
            self._capture = None
        elif tag == "a" and self._capture == "link":
            if self.links:
                self.links[-1]["text"] = " ".join(" ".join(self._buffer).split())[:300]
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._capture in {"title", "heading", "link"}:
            self._buffer.append(data)


class ExtractHTMLFileTool:
    spec = ToolSpec(
        "html.extract_file",
        "Extract metadata, heading hierarchy and links from a bounded local HTML file. Never fetches the base URL or any link.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 500},
                "base_url": {"type": "string", "maxLength": 2048},
                "max_links": {"type": "integer", "minimum": 0, "maximum": 200},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, source = read_workspace_text(context, arguments["path"], max_bytes=1_000_000)
        if len(source) > 1_000_000:
            raise ValueError("HTML source exceeds the 1 MB limit")
        base_url = arguments.get("base_url")
        if base_url:
            parsed = urlsplit(base_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("base_url must be an absolute HTTP(S) URL without credentials")
        maximum = arguments.get("max_links", 100)
        if not 0 <= maximum <= 200:
            raise ValueError("max_links must be between 0 and 200")
        parser = _DocumentParser(base_url, maximum)
        parser.feed(source)
        parser.close()
        return {
            "path": relative.as_posix(),
            "title": parser.title_parts[0] if parser.title_parts else None,
            "description": parser.description,
            "canonical": parser.canonical,
            "headings": parser.headings,
            "links": parser.links,
            "links_returned": len(parser.links),
            "network_requests": 0,
            "scope": "local_html_only",
        }


class CrawlLocalHTMLSiteTool:
    spec = ToolSpec(
        "html.crawl_local_site",
        "Crawl a bounded multi-page static HTML snapshot inside the approved workspace, extract page metadata and build an internal link graph. External links are recorded only as counts; no network requests are made.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "start_path": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 100},
                "max_depth": {"type": "integer", "minimum": 0, "maximum": 5},
            },
            "required": ["start_path"],
            "additionalProperties": False,
        },
    )

    @staticmethod
    def _local_target(current_path: str, href: str) -> str | None:
        base = "https://snapshot.invalid/" + current_path.lstrip("/")
        resolved = urljoin(base, href)
        parsed = urlsplit(resolved)
        if parsed.scheme != "https" or parsed.hostname != "snapshot.invalid":
            return None
        candidate = unquote(parsed.path).lstrip("/")
        if candidate.endswith("/"):
            candidate += "index.html"
        normalized = posixpath.normpath(candidate)
        if (
            normalized in {"", ".", ".."}
            or normalized.startswith("../")
            or normalized.startswith("/")
            or posixpath.splitext(normalized)[1].lower() not in {".html", ".htm"}
        ):
            return None
        return normalized

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        start_path = arguments["start_path"]
        maximum = arguments.get("max_pages", 30)
        max_depth = arguments.get("max_depth", 3)
        if not 1 <= maximum <= 100:
            raise ValueError("max_pages must be between 1 and 100")
        if not 0 <= max_depth <= 5:
            raise ValueError("max_depth must be between 0 and 5")
        queue: list[tuple[str, int]] = [(start_path, 0)]
        visited: set[str] = set()
        pages: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        external_links = 0
        unavailable_links: list[str] = []
        truncated = False
        while queue:
            current_path, depth = queue.pop(0)
            if current_path in visited:
                continue
            if len(pages) >= maximum:
                truncated = True
                break
            try:
                relative, source = read_workspace_text(
                    context, current_path, max_bytes=1_000_000
                )
            except (OSError, ValueError, PermissionError):
                unavailable_links.append(current_path)
                continue
            parser = _DocumentParser(
                "https://snapshot.invalid/" + relative.as_posix(),
                200,
            )
            parser.feed(source)
            parser.close()
            visited.add(relative.as_posix())
            internal_targets: list[str] = []
            for link in parser.links:
                target = self._local_target(relative.as_posix(), link["href"])
                if target is None:
                    external_links += 1
                    continue
                internal_targets.append(target)
                edges.append({"from": relative.as_posix(), "to": target})
                if depth < max_depth and target not in visited:
                    queue.append((target, depth + 1))
            pages.append(
                {
                    "path": relative.as_posix(),
                    "depth": depth,
                    "title": parser.title_parts[0] if parser.title_parts else None,
                    "description": parser.description,
                    "canonical": parser.canonical,
                    "headings": parser.headings,
                    "internal_links": sorted(set(internal_targets)),
                }
            )
        return {
            "start_path": start_path,
            "pages": pages,
            "pages_crawled": len(pages),
            "link_edges": edges[:500],
            "external_links_observed": external_links,
            "unavailable_internal_paths": sorted(set(unavailable_links))[:100],
            "max_depth": max_depth,
            "truncated": truncated or bool(queue),
            "network_requests": 0,
            "scope": "workspace_local_html_snapshot",
        }
