"""Rule-based story analysis fallback and helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from ai_observatory.config import settings
from ai_observatory.logging_setup import logger

ENTERPRISE_KEYWORDS = {
    "enterprise": 2.0,
    "regulation": 2.0,
    "policy": 1.5,
    "security": 1.5,
    "governance": 1.5,
    "deployment": 1.5,
    "partnership": 1.0,
    "cloud": 1.0,
    "infrastructure": 1.0,
    "agent": 1.5,
    "model": 1.0,
    "openai": 1.5,
    "anthropic": 1.5,
    "google": 1.0,
    "nvidia": 1.5,
    "microsoft": 1.0,
    "meta": 1.0,
    "benchmark": 1.0,
    "safety": 1.5,
    "compliance": 2.0,
    "cost": 1.0,
    "productivity": 1.5,
    "workforce": 1.5,
}

PRIORITY_SOURCES = {
    "OpenAI": 1.5,
    "Anthropic": 1.5,
    "Google DeepMind": 1.5,
    "Microsoft AI": 1.2,
    "NVIDIA": 1.2,
    "Reuters AI": 1.3,
    "TechCrunch AI": 1.0,
    "Meta AI": 1.2,
    "AWS AI": 1.2,
}

STORY_CATEGORIES = {
    "Model & Product": r"\b(model|gpt|claude|gemini|llama|release|launch|product)\b",
    "Enterprise & Adoption": r"\b(enterprise|business|workplace|productivity|deployment|adoption)\b",
    "Governance & Safety": r"\b(safety|governance|regulation|policy|compliance|ethics|security)\b",
    "Infrastructure & Hardware": r"\b(nvidia|gpu|chip|infrastructure|cloud|compute|datacenter)\b",
    "Agents & Automation": r"\b(agent|automation|copilot|assistant|workflow)\b",
    "Partnerships & Ecosystem": r"\b(partnership|vendor|ecosystem|integrat|collaborat)\b",
}


def categorize_story(story: dict[str, Any]) -> str:
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    for category, pattern in STORY_CATEGORIES.items():
        if re.search(pattern, text):
            return category
    return "General AI News"


def ensure_story_urls(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure every story has a clickable URL."""
    ensured: list[dict[str, Any]] = []
    for story in stories:
        item = dict(story)
        url = (item.get("url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            title = item.get("title", "story")
            item["url"] = f"https://www.google.com/search?q={title.replace(' ', '+')}"
            item["url_fallback"] = True
        else:
            item["url_fallback"] = False
        ensured.append(item)
    return ensured


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def score_story(story: dict[str, Any]) -> float:
    """Score story relevance from 1-10 for technology leaders."""
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    score = 4.0

    for keyword, weight in ENTERPRISE_KEYWORDS.items():
        if keyword in text:
            score += weight * 0.3

    source = story.get("source", "")
    score += PRIORITY_SOURCES.get(source, 0.0)

    if story.get("collection_method") == "rss":
        score += 0.5

    published = story.get("published_at")
    if isinstance(published, datetime):
        age_hours = (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).total_seconds() / 3600
        if age_hours < 24:
            score += 1.5
        elif age_hours < 72:
            score += 0.5

    return max(1.0, min(10.0, round(score, 1)))


def why_it_matters(story: dict[str, Any]) -> str:
    title = story.get("title", "This development")
    source = story.get("source", "the market")
    return (
        f"{title} signals momentum from {source}. Technology leaders should track how "
        "this affects AI strategy, vendor selection, and enterprise readiness."
    )


def enterprise_impact(story: dict[str, Any]) -> str:
    summary = story.get("summary", "")
    if not summary:
        return (
            "Potential impact on AI roadmaps, budget planning, and cross-functional "
            "governance across product, security, and operations teams."
        )
    return (
        f"Enterprise teams should evaluate operational implications: {summary[:220]}..."
        if len(summary) > 220
        else f"Enterprise teams should evaluate operational implications: {summary}"
    )


def analyze_stories(stories: list[dict[str, Any]], top_n: int | None = None) -> list[dict[str, Any]]:
    """Deduplicate, score, enrich, and return top stories (base scoring only)."""
    top_n = top_n or settings.top_story_count
    scored: list[dict[str, Any]] = []
    for story in stories:
        enriched = dict(story)
        enriched["relevance_score"] = score_story(story)
        enriched["why_it_matters"] = why_it_matters(story)
        enriched["enterprise_impact"] = enterprise_impact(story)
        enriched["category"] = categorize_story(story)
        if enriched.get("published_at"):
            enriched["published_at"] = _serialize_datetime(enriched["published_at"])
        scored.append(enriched)

    scored.sort(key=lambda s: s["relevance_score"], reverse=True)
    return ensure_story_urls(scored[:top_n])


def extract_themes(stories: list[dict[str, Any]]) -> list[str]:
    theme_patterns = {
        "Model releases & capabilities": r"\b(model|gpt|claude|gemini|llama|release|launch)\b",
        "Enterprise AI adoption": r"\b(enterprise|business|workplace|productivity|deployment)\b",
        "AI safety & governance": r"\b(safety|governance|regulation|policy|compliance|ethics)\b",
        "Infrastructure & chips": r"\b(nvidia|gpu|chip|infrastructure|cloud|compute)\b",
        "Agents & automation": r"\b(agent|automation|copilot|assistant|workflow)\b",
    }
    combined = " ".join(
        f"{s.get('title', '')} {s.get('summary', '')}" for s in stories
    ).lower()
    themes = [name for name, pattern in theme_patterns.items() if re.search(pattern, combined)]
    if not themes:
        themes = ["General AI market momentum"]
    return themes[:5]


def recommended_actions(stories: list[dict[str, Any]], themes: list[str]) -> list[str]:
    actions = [
        "Review top stories with your AI steering committee and map each to active initiatives.",
        "Update vendor and model risk assessments based on today's announcements.",
        "Identify one pilot or production use case affected by emerging themes this week.",
    ]
    if any("safety" in t.lower() or "governance" in t.lower() for t in themes):
        actions.append("Schedule a governance checkpoint on data, security, and compliance controls.")
    if stories:
        top = stories[0]
        actions.append(
            f"Assign an owner to brief stakeholders on: \"{top.get('title', 'top story')[:80]}\"."
        )
    return actions[:5]


def build_briefing_payload(stories: list[dict[str, Any]]) -> dict[str, Any]:
    themes = extract_themes(stories)
    actions = recommended_actions(stories, themes)
    return {
        "stories": stories,
        "themes": themes,
        "recommended_actions": actions,
        "executive_summary": (
            f"Today's briefing highlights {len(stories)} high-relevance AI developments "
            f"across themes including {', '.join(themes[:3])}."
        ),
    }


def stories_to_json(stories: list[dict[str, Any]]) -> str:
    return json.dumps(stories, indent=2, default=str)


def parse_llm_json(raw: str) -> dict[str, Any] | None:
    """Best-effort parse of JSON from LLM output with repair pipeline."""
    from ai_observatory.crew_parser import parse_json_with_repair

    data, _, error = parse_json_with_repair(raw)
    if data is None and error:
        logger.warning("parse_llm_json failed", extra={"error": error})
    return data
