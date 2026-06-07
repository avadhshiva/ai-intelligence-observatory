"""News collection from NewsAPI and RSS feeds."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from ai_observatory.config import settings
from ai_observatory.logging_setup import logger
from ai_observatory.sources import RSS_FEEDS


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def _story_key(title: str, url: str) -> str:
    normalized = _normalize_title(title)
    if normalized:
        return hashlib.sha256(normalized.encode()).hexdigest()
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


class NewsCollector:
    """Collects raw AI news from NewsAPI and configured RSS feeds."""

    def __init__(self, newsapi_key: str | None = None, timeout: float = 15.0) -> None:
        self.newsapi_key = newsapi_key or settings.newsapi_key
        self.timeout = timeout

    def collect_all(self) -> list[dict[str, Any]]:
        stories: list[dict[str, Any]] = []
        stories.extend(self.collect_rss())
        stories.extend(self.collect_newsapi())
        deduped = self.deduplicate(stories)
        logger.info(
            "Collection complete",
            extra={
                "raw_count": len(stories),
                "deduped_count": len(deduped),
            },
        )
        return deduped[: settings.max_raw_stories]

    def collect_rss(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for source_name, feed_url in RSS_FEEDS.items():
            try:
                results.extend(self._fetch_rss_feed(source_name, feed_url))
            except Exception as exc:
                logger.warning(
                    "RSS feed failed",
                    extra={"source": source_name, "url": feed_url, "error": str(exc)},
                )
        return results

    def _fetch_rss_feed(self, source_name: str, feed_url: str) -> list[dict[str, Any]]:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(feed_url, headers={"User-Agent": "AI-Observatory/0.1"})
            response.raise_for_status()
            parsed = feedparser.parse(response.text)

        stories: list[dict[str, Any]] = []
        for entry in parsed.entries[:15]:
            title = getattr(entry, "title", "").strip()
            url = getattr(entry, "link", "").strip()
            if not title or not url:
                continue
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = re.sub(r"<[^>]+>", "", str(summary))[:500]
            stories.append(
                {
                    "title": title,
                    "url": url,
                    "source": source_name,
                    "summary": summary,
                    "published_at": _parse_published(entry),
                    "domain": _domain(url),
                    "collection_method": "rss",
                }
            )
        logger.info("RSS feed fetched", extra={"source": source_name, "count": len(stories)})
        return stories

    def collect_newsapi(self) -> list[dict[str, Any]]:
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured; skipping NewsAPI collection")
            return []

        params = {
            "q": settings.newsapi_query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 30,
            "apiKey": self.newsapi_key,
        }
        url = "https://newsapi.org/v2/everything"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        articles = payload.get("articles", [])
        stories: list[dict[str, Any]] = []
        for article in articles:
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url or title == "[Removed]":
                continue
            published_raw = article.get("publishedAt")
            published_at = None
            if published_raw:
                try:
                    published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                except ValueError:
                    published_at = None
            stories.append(
                {
                    "title": title,
                    "url": url,
                    "source": article.get("source", {}).get("name", "NewsAPI"),
                    "summary": (article.get("description") or "")[:500],
                    "published_at": published_at,
                    "domain": _domain(url),
                    "collection_method": "newsapi",
                }
            )
        logger.info("NewsAPI fetched", extra={"count": len(stories)})
        return stories

    @staticmethod
    def deduplicate(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for story in stories:
            key = _story_key(story.get("title", ""), story.get("url", ""))
            if key in seen:
                continue
            seen.add(key)
            story["story_key"] = key
            unique.append(story)
        return unique
