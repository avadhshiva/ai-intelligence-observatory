"""Personal CTO Agent — profile-aligned daily guidance."""

from __future__ import annotations

import re
from typing import Any

from ai_observatory.user_profile import UserProfile, load_user_profile

ACTION_PATTERNS: list[tuple[str, str]] = [
    (r"launch|release|model|product", "Schedule a 30-minute vendor review with your platform team."),
    (r"governance|regulation|compliance|policy", "Update your AI risk register and compliance checklist."),
    (r"agent|automation|copilot", "Identify one workflow where agentic automation could reduce cycle time."),
    (r"enterprise|adoption|deployment", "Align your transformation roadmap with today's adoption signals."),
    (r"partnership|vendor|pricing", "Revisit vendor contracts and total cost of ownership assumptions."),
    (r"infrastructure|gpu|chip|cloud", "Validate capacity and cost forecasts for AI workloads."),
]

SKILL_RECOMMENDATIONS: dict[str, list[str]] = {
    "agents": ["Agent orchestration", "Tool-use design", "Workflow automation"],
    "governance": ["AI governance frameworks", "Model risk management", "Policy design"],
    "enterprise adoption": ["Change management", "AI value realization", "Stakeholder storytelling"],
    "program delivery": ["Program roadmapping", "Dependency management", "Executive reporting"],
    "infrastructure": ["Cloud AI platforms", "Cost optimization", "LLMOps"],
    "vendor strategy": ["Vendor evaluation", "Build vs buy analysis", "Contract negotiation"],
}


def why_this_matters_to_me(story: dict[str, Any], profile: UserProfile) -> str:
    roles = " and ".join(profile.roles[:2])
    companies = ", ".join(story.get("companies", [])[:2]) or "the broader market"
    focus_hit = _matching_focus_areas(story, profile)
    focus_text = f" It connects to your focus on {', '.join(focus_hit[:2])}." if focus_hit else ""
    return (
        f"As a {roles}, this story from {companies} may affect your program priorities, "
        f"stakeholder narrative, and delivery plans.{focus_text}"
    )


def _matching_focus_areas(story: dict[str, Any], profile: UserProfile) -> list[str]:
    text = f"{story.get('title', '')} {story.get('summary', '')}".lower()
    hits = []
    for area in profile.focus_areas:
        tokens = area.lower().split()
        if any(token in text for token in tokens):
            hits.append(area)
    return hits


def recommend_actions(
    stories: list[dict[str, Any]],
    profile: UserProfile,
    job_market: dict[str, Any] | None = None,
) -> list[str]:
    actions: list[str] = []
    combined = " ".join(f"{s.get('title', '')} {s.get('summary', '')}" for s in stories[:5]).lower()

    for pattern, action in ACTION_PATTERNS:
        if re.search(pattern, combined) and action not in actions:
            actions.append(action)
        if len(actions) >= 4:
            break

    if job_market and job_market.get("top_categories"):
        actions.append(
            f"Review hiring and upskilling plans for {job_market['top_categories'][0]} demand."
        )

    if stories:
        top = stories[0]
        actions.append(
            f"Block 15 minutes to discuss: \"{top.get('title', 'top story')[:70]}\" with your leadership team."
        )

    actions.append(f"Align today's intelligence with your {profile.industry} industry context.")
    return actions[:5]


def skills_to_learn(
    stories: list[dict[str, Any]],
    profile: UserProfile,
    job_market: dict[str, Any] | None = None,
) -> list[str]:
    skills: list[str] = []
    text = " ".join(f"{s.get('title', '')} {s.get('summary', '')}" for s in stories).lower()

    for area in profile.focus_areas:
        for skill in SKILL_RECOMMENDATIONS.get(area, []):
            if skill not in skills:
                skills.append(skill)

    if job_market:
        for item in job_market.get("emerging_skills", [])[:3]:
            skill = item.get("skill", "")
            if skill and skill not in skills:
                skills.append(skill)

    if re.search(r"agent|automation", text) and "Agent orchestration" not in skills:
        skills.insert(0, "Agent orchestration")
    if re.search(r"governance|compliance", text) and "AI governance frameworks" not in skills:
        skills.insert(0, "AI governance frameworks")

    return skills[:6]


def build_personal_cto_brief(
    stories: list[dict[str, Any]],
    profile: UserProfile | None = None,
    job_market: dict[str, Any] | None = None,
    enterprise_adoption: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = profile or load_user_profile()
    story_insights = []
    for story in stories[:5]:
        story_insights.append(
            {
                "title": story.get("title", ""),
                "url": story.get("url", ""),
                "why_this_matters_to_me": why_this_matters_to_me(story, profile),
                "recommended_action": _story_action(story),
            }
        )

    actions = recommend_actions(stories, profile, job_market)
    skills = skills_to_learn(stories, profile, job_market)

    exec_summary = (
        f"Personal CTO brief for {profile.name}: {len(stories)} priority stories today. "
        f"Focus on {', '.join(profile.focus_areas[:2])}. "
    )
    if enterprise_adoption and enterprise_adoption.get("active_industries"):
        exec_summary += (
            f"Notable enterprise activity in {', '.join(enterprise_adoption['active_industries'][:2])}."
        )

    return {
        "profile_name": profile.name,
        "profile_roles": profile.roles,
        "executive_summary": exec_summary,
        "daily_priority": stories[0].get("title", "") if stories else "",
        "story_insights": story_insights,
        "recommended_actions": actions,
        "skills_to_learn": skills,
    }


def _story_action(story: dict[str, Any]) -> str:
    text = _story_text(story)
    for pattern, action in ACTION_PATTERNS:
        if re.search(pattern, text):
            return action
    return "Share this story with your program stakeholders and capture one follow-up action."


def _story_text(story: dict[str, Any]) -> str:
    return f"{story.get('title', '')} {story.get('summary', '')}".lower()


def apply_personal_cto_to_stories(
    stories: list[dict[str, Any]], profile: UserProfile | None = None
) -> list[dict[str, Any]]:
    profile = profile or load_user_profile()
    enriched = []
    for story in stories:
        item = dict(story)
        item["why_this_matters_to_me"] = why_this_matters_to_me(item, profile)
        item["cto_recommended_action"] = _story_action(item)
        enriched.append(item)
    return enriched
