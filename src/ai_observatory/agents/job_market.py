"""AI Job Market Intelligence Agent — demand trends and emerging skills."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

JOB_CATEGORIES: dict[str, list[str]] = {
    "AI Transformation": [
        r"ai transformation",
        r"digital transformation",
        r"transformation lead",
        r"transformation manager",
        r"ai adoption",
    ],
    "TPM": [
        r"\btpm\b",
        r"technical program manager",
        r"tech program manager",
        r"program manager",
    ],
    "Delivery Leadership": [
        r"delivery lead",
        r"delivery manager",
        r"delivery director",
        r"engineering director",
        r"head of delivery",
    ],
    "AI Governance": [
        r"ai governance",
        r"responsible ai",
        r"ai ethics",
        r"model governance",
        r"ai compliance",
        r"ai policy",
    ],
    "Program Management": [
        r"program management",
        r"portfolio management",
        r"\bpmo\b",
        r"program director",
        r"initiative lead",
    ],
}

SKILL_SIGNALS: dict[str, list[str]] = {
    "Agent orchestration": [r"\bagent", r"multi-agent", r"agentic"],
    "RAG & retrieval": [r"\brag\b", r"retrieval", r"vector", r"embedding"],
    "Prompt engineering": [r"prompt", r"in-context", r"few-shot"],
    "MLOps / LLMOps": [r"mlops", r"llmops", r"model deployment", r"model serving"],
    "AI governance": [r"governance", r"compliance", r"responsible ai", r"audit"],
    "Cloud AI platforms": [r"bedrock", r"azure ai", r"vertex", r"sagemaker"],
    "Evaluation & safety": [r"evaluation", r"red team", r"safety", r"benchmark"],
    "Program delivery": [r"program", r"roadmap", r"stakeholder", r"delivery"],
}


def _story_text(story: dict[str, Any]) -> str:
    return f"{story.get('title', '')} {story.get('summary', '')}".lower()


def detect_job_signals(stories: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for story in stories:
        text = _story_text(story)
        for category, patterns in JOB_CATEGORIES.items():
            if any(re.search(p, text) for p in patterns):
                counts[category] += 1
    return dict(counts)


def detect_emerging_skills(stories: list[dict[str, Any]], top_n: int = 8) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for story in stories:
        text = _story_text(story)
        for skill, patterns in SKILL_SIGNALS.items():
            if any(re.search(p, text) for p in patterns):
                counts[skill] += 1

    ranked = counts.most_common(top_n)
    return [
        {"skill": skill, "mentions": count, "demand_signal": _demand_label(count, len(stories))}
        for skill, count in ranked
    ]


def _demand_label(count: int, total: int) -> str:
    if total == 0:
        return "Low"
    ratio = count / total
    if ratio >= 0.25:
        return "High"
    if ratio >= 0.10:
        return "Rising"
    return "Emerging"


def build_daily_job_market_summary(
    stories: list[dict[str, Any]], briefing_date: date | None = None
) -> dict[str, Any]:
    briefing_date = briefing_date or date.today()
    category_demand = detect_job_signals(stories)
    skills = detect_emerging_skills(stories)
    top_categories = sorted(category_demand.items(), key=lambda x: x[1], reverse=True)

    summary_lines = []
    if top_categories:
        leader = top_categories[0]
        summary_lines.append(
            f"Strongest demand signal today: {leader[0]} ({leader[1]} story mentions)."
        )
    if skills:
        summary_lines.append(
            f"Top emerging skill: {skills[0]['skill']} ({skills[0]['demand_signal']} demand)."
        )

    return {
        "date": briefing_date.isoformat(),
        "category_demand": category_demand,
        "top_categories": [c for c, _ in top_categories[:3]],
        "emerging_skills": skills,
        "summary": " ".join(summary_lines) or "Limited job-market signals in today's news cycle.",
        "total_stories_analyzed": len(stories),
    }


def build_weekly_job_market_summary(daily_snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    category_totals: Counter[str] = Counter()
    skill_totals: Counter[str] = Counter()

    for snap in daily_snapshots:
        for cat, count in snap.get("category_demand", {}).items():
            category_totals[cat] += count
        for skill_item in snap.get("emerging_skills", []):
            skill_totals[skill_item["skill"]] += skill_item.get("mentions", 1)

    top_skills = [
        {"skill": s, "mentions": c, "demand_signal": _demand_label(c, max(len(daily_snapshots), 1))}
        for s, c in skill_totals.most_common(8)
    ]

    return {
        "category_demand": dict(category_totals),
        "top_categories": [c for c, _ in category_totals.most_common(5)],
        "emerging_skills": top_skills,
        "days_analyzed": len(daily_snapshots),
        "summary": (
            f"Weekly job-market pulse: top role demand in "
            f"{', '.join(c for c, _ in category_totals.most_common(3)) or 'N/A'}. "
            f"Skills to watch: {', '.join(s['skill'] for s in top_skills[:3]) or 'N/A'}."
        ),
    }
