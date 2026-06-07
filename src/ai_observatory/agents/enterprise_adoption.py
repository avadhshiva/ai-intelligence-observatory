"""Enterprise Adoption Tracker — industry-level AI implementation signals."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any

TRACKED_INDUSTRIES: dict[str, list[str]] = {
    "Banking": [
        r"\bbank",
        r"banking",
        r"financial services",
        r"fintech",
        r"insurance",
        r"capital markets",
    ],
    "Retail": [r"\bretail", r"storefront", r"merchandis", r"shopper", r"point of sale"],
    "Healthcare": [
        r"healthcare",
        r"hospital",
        r"clinical",
        r"patient",
        r"medical",
        r"pharma",
        r"biotech",
    ],
    "Logistics": [
        r"logistics",
        r"supply chain",
        r"warehouse",
        r"shipping",
        r"freight",
        r"last-mile",
    ],
    "E-commerce": [
        r"e-commerce",
        r"ecommerce",
        r"online retail",
        r"marketplace",
        r"checkout",
        r"cart",
    ],
}


def detect_industry(story: dict[str, Any]) -> list[str]:
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    found = []
    for industry, patterns in TRACKED_INDUSTRIES.items():
        if any(re.search(p, text) for p in patterns):
            found.append(industry)
    return found


def summarize_implementation(story: dict[str, Any], industry: str) -> str:
    title = story.get("title", "An enterprise initiative")
    summary = story.get("summary", "")
    snippet = summary[:160] + "..." if len(summary) > 160 else summary
    return (
        f"**{industry}**: {title}. "
        f"{snippet or 'Notable AI adoption signal detected in industry news.'}"
    )


def build_enterprise_adoption_report(
    stories: list[dict[str, Any]], briefing_date: date | None = None
) -> dict[str, Any]:
    briefing_date = briefing_date or date.today()
    by_industry: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for story in stories:
        industries = detect_industry(story)
        for industry in industries:
            by_industry[industry].append(
                {
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "summary": summarize_implementation(story, industry),
                    "score": story.get("final_score", story.get("relevance_score", 0)),
                }
            )

    industry_summary = {}
    for industry in TRACKED_INDUSTRIES:
        items = by_industry.get(industry, [])
        industry_summary[industry] = {
            "story_count": len(items),
            "implementations": items[:3],
            "active": len(items) > 0,
        }

    active = [i for i, d in industry_summary.items() if d["active"]]
    notable = []
    for industry in active:
        for item in industry_summary[industry]["implementations"][:1]:
            notable.append(item["summary"])

    return {
        "date": briefing_date.isoformat(),
        "industries": industry_summary,
        "active_industries": active,
        "notable_implementations": notable[:5],
        "summary": (
            f"Enterprise adoption signals detected across {len(active)} industries: "
            f"{', '.join(active) or 'none today'}."
        ),
    }


def tag_stories_with_industries(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged = []
    for story in stories:
        item = dict(story)
        item["industries"] = detect_industry(item)
        tagged.append(item)
    return tagged
