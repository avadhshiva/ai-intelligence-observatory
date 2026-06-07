"""RSS feed sources for AI intelligence collection."""

from __future__ import annotations

# Official feeds where available; community-maintained mirrors for sources without public RSS.
RSS_FEEDS: dict[str, str] = {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://raw.githubusercontent.com/0xSMW/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Meta AI": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_meta_ai.xml",
    "Microsoft AI": "https://blogs.microsoft.com/ai/feed/",
    "AWS AI": "https://aws.amazon.com/blogs/machine-learning/feed/",
    "NVIDIA": "https://blogs.nvidia.com/feed/",
    "Reuters AI": "https://news.google.com/rss/search?q=site:reuters.com+artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
}

NEWSAPI_SOURCES = [
    "openai",
    "anthropic",
    "google",
    "meta",
    "microsoft",
    "nvidia",
    "reuters",
    "techcrunch",
]
