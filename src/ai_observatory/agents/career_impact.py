"""Career Impact Agent — role-specific implications for technology leaders."""

from __future__ import annotations

import re
from typing import Any

from ai_observatory.user_profile import UserProfile, load_user_profile

CAREER_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "TPM": [
        (r"launch|release|roadmap|milestone", "Update program timelines and dependency maps for affected workstreams."),
        (r"governance|compliance|regulation|policy", "Add compliance checkpoints to your program RAID log."),
        (r"agent|automation|copilot", "Identify cross-team integration points for agent-enabled workflows."),
        (r"partnership|vendor|pricing", "Reassess vendor commitments and contract renewal timelines."),
    ],
    "AI Transformation Manager": [
        (r"adoption|enterprise|workplace|productivity", "Refresh your transformation playbook and change narrative."),
        (r"pilot|deployment|rollout", "Prioritize which business units should enter the next adoption wave."),
        (r"workforce|upskill|training", "Align capability-building plans with newly available platform features."),
        (r"roi|cost|pricing", "Update business case assumptions for AI investments and funding requests."),
    ],
    "Delivery Leader": [
        (r"infrastructure|gpu|chip|cloud|compute", "Review capacity planning and production readiness for AI workloads."),
        (r"security|safety|reliability|sla", "Validate operational guardrails before scaling AI services."),
        (r"deployment|production|scale", "Assess delivery team readiness and release cadence impacts."),
        (r"agent|workflow|automation", "Evaluate how automation shifts team responsibilities and SLAs."),
    ],
}

DEFAULT_IMPACTS: dict[str, str] = {
    "TPM": "Monitor how this development affects milestone sequencing, stakeholder expectations, and cross-team dependencies.",
    "AI Transformation Manager": "Consider how this news changes your transformation narrative, adoption priorities, and executive sponsorship asks.",
    "Delivery Leader": "Evaluate operational implications for delivery capacity, release risk, and production support models.",
}


def career_impact_for_role(story: dict[str, Any], role: str) -> str:
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    for pattern, message in CAREER_PATTERNS.get(role, []):
        if re.search(pattern, text):
            return message
    return DEFAULT_IMPACTS.get(role, f"Track implications for your work as a {role}.")


def apply_career_impact(
    stories: list[dict[str, Any]], profile: UserProfile | None = None
) -> list[dict[str, Any]]:
    profile = profile or load_user_profile()
    enriched: list[dict[str, Any]] = []
    for story in stories:
        item = dict(story)
        impacts = {role: career_impact_for_role(item, role) for role in profile.roles}
        item["career_impact"] = impacts
        item["career_impact_summary"] = " | ".join(
            f"{role}: {impacts[role]}" for role in profile.roles[:2]
        )
        enriched.append(item)
    return enriched
