"""Company Intelligence Agent — track major AI vendors."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

TRACKED_COMPANIES: dict[str, list[str]] = {
    "OpenAI": [r"openai", r"\bgpt\b", r"chatgpt", r"\bo1\b", r"\bo3\b"],
    "Anthropic": [r"anthropic", r"\bclaude\b"],
    "Google": [r"google", r"deepmind", r"\bgemini\b", r"alphabet"],
    "Microsoft": [r"microsoft", r"\bcopilot\b", r"azure ai", r"\bazure\b"],
    "AWS": [r"\baws\b", r"amazon web services", r"\bbedrock\b", r"sagemaker"],
    "NVIDIA": [r"nvidia", r"\bcuda\b", r"\bh100\b", r"\bb200\b", r"\bblackwell\b"],
}

SOURCE_COMPANY_MAP: dict[str, str] = {
    "OpenAI": "OpenAI",
    "Anthropic": "Anthropic",
    "Google DeepMind": "Google",
    "Microsoft AI": "Microsoft",
    "AWS AI": "AWS",
    "NVIDIA": "NVIDIA",
}


def detect_companies(story: dict[str, Any]) -> list[str]:
    text = f"{story.get('title', '')} {story.get('summary', '')} {story.get('url', '')}".lower()
    source = story.get("source", "")
    found: set[str] = set()

    mapped = SOURCE_COMPANY_MAP.get(source)
    if mapped:
        found.add(mapped)

    for company, patterns in TRACKED_COMPANIES.items():
        if any(re.search(pattern, text) for pattern in patterns):
            found.add(company)

    return sorted(found)


def tag_story_companies(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for story in stories:
        item = dict(story)
        item["companies"] = detect_companies(item)
        item["primary_company"] = item["companies"][0] if item["companies"] else "Other"
        tagged.append(item)
    return tagged


def build_company_intelligence(stories: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate company activity from a story set."""
    activity: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"story_count": 0, "headlines": [], "avg_relevance": 0.0, "scores": []}
    )

    for story in stories:
        companies = story.get("companies") or detect_companies(story)
        score = float(story.get("final_score") or story.get("relevance_score") or 0)
        for company in companies:
            bucket = activity[company]
            bucket["story_count"] += 1
            bucket["scores"].append(score)
            if len(bucket["headlines"]) < 3:
                bucket["headlines"].append(
                    {"title": story.get("title", ""), "url": story.get("url", ""), "score": score}
                )

    summary: dict[str, Any] = {}
    for company in TRACKED_COMPANIES:
        bucket = activity.get(company, {"story_count": 0, "headlines": [], "scores": []})
        scores = bucket.get("scores", [])
        summary[company] = {
            "story_count": bucket.get("story_count", 0),
            "avg_relevance": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "headlines": bucket.get("headlines", []),
            "active": bucket.get("story_count", 0) > 0,
        }

    ranked = sorted(
        [(c, d["story_count"]) for c, d in summary.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    return {
        "companies": summary,
        "most_active": [c for c, count in ranked if count > 0][:3],
        "quiet_companies": [c for c, count in ranked if count == 0],
    }
