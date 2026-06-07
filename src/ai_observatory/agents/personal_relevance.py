"""Personal Relevance Agent — profile-driven scoring for leadership roles."""

from __future__ import annotations

import re
from typing import Any

from ai_observatory.user_profile import UserProfile, load_user_profile

ROLE_KEYWORDS: dict[str, list[str]] = {
    "TPM": [
        "program",
        "delivery",
        "roadmap",
        "milestone",
        "stakeholder",
        "cross-functional",
        "launch",
        "timeline",
        "risk",
    ],
    "AI Transformation Manager": [
        "transformation",
        "adoption",
        "change",
        "workforce",
        "capability",
        "upskilling",
        "operating model",
        "roi",
        "pilot",
    ],
    "Delivery Leader": [
        "deployment",
        "production",
        "scale",
        "operations",
        "sla",
        "reliability",
        "execution",
        "team",
        "delivery",
    ],
}

FOCUS_KEYWORDS: dict[str, list[str]] = {
    "enterprise adoption": ["enterprise", "business", "workplace", "adoption", "rollout"],
    "program delivery": ["program", "delivery", "milestone", "execution", "launch"],
    "governance": ["governance", "policy", "compliance", "risk", "audit"],
    "agents": ["agent", "automation", "copilot", "assistant", "workflow"],
    "infrastructure": ["infrastructure", "gpu", "chip", "cloud", "compute", "datacenter"],
    "vendor strategy": ["partnership", "vendor", "ecosystem", "platform", "pricing"],
}


def score_personal_relevance(story: dict[str, Any], profile: UserProfile) -> float:
    """Score story personal relevance 1-10 based on user profile."""
    text = f"{story.get('title', '')} {story.get('summary', '')} {story.get('source', '')}".lower()
    score = 3.5

    for role in profile.roles:
        for keyword in ROLE_KEYWORDS.get(role, []):
            if keyword in text:
                score += 0.35

    for area in profile.focus_areas:
        for keyword in FOCUS_KEYWORDS.get(area, [area]):
            if keyword in text:
                score += 0.45

    companies = story.get("companies") or tag_companies_from_text(text, profile.priority_companies)
    for company in companies:
        if company in profile.priority_companies:
            score += 0.8

    if story.get("category") in {"Enterprise & Adoption", "Agents & Automation", "Governance & Safety"}:
        score += 0.5

    return max(1.0, min(10.0, round(score, 1)))


def tag_companies_from_text(text: str, companies: list[str]) -> list[str]:
    found: list[str] = []
    for company in companies:
        if re.search(rf"\b{re.escape(company.lower())}\b", text):
            found.append(company)
    return found


def personal_relevance_note(story: dict[str, Any], profile: UserProfile) -> str:
    roles = ", ".join(profile.roles[:2])
    companies = ", ".join(story.get("companies", [])[:2]) or "industry-wide"
    return (
        f"Relevant to your profile ({roles}): this {companies} development aligns with "
        f"focus areas including {', '.join(profile.focus_areas[:3])}."
    )


def apply_personal_relevance(
    stories: list[dict[str, Any]], profile: UserProfile | None = None
) -> list[dict[str, Any]]:
    profile = profile or load_user_profile()
    enriched: list[dict[str, Any]] = []
    for story in stories:
        item = dict(story)
        item["personal_relevance_score"] = score_personal_relevance(item, profile)
        base = float(item.get("relevance_score", 5.0))
        personal = float(item["personal_relevance_score"])
        item["final_score"] = round(0.55 * base + 0.45 * personal, 1)
        item["personal_relevance_note"] = personal_relevance_note(item, profile)
        enriched.append(item)
    enriched.sort(key=lambda s: s.get("final_score", 0), reverse=True)
    return enriched
