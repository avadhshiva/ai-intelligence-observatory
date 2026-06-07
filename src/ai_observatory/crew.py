"""CrewAI agents, tasks, and crew orchestration."""

from __future__ import annotations

from datetime import date
from typing import Any

from ai_observatory.analysis import stories_to_json
from ai_observatory.collectors import NewsCollector
from ai_observatory.config import settings
from ai_observatory.crew_parser import CrewExecutionTimer, ParseResult, parse_crew_output
from ai_observatory.intelligence import analyze_stories, build_briefing_payload, intelligence_bundle_from_payload
from ai_observatory.logging_setup import logger


def _crewai_types():
    """Lazy-import CrewAI to avoid loading heavy deps until LLM pipeline runs."""
    from crewai import Agent, Crew, LLM, Process, Task

    return Agent, Crew, LLM, Process, Task


def _llm() -> Any:
    """Create a CrewAI-native LLM instance (CrewAI 1.14+ expects str | BaseLLM)."""
    _, _, LLM, _, _ = _crewai_types()
    return LLM(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )


def run_observatory_crew(send_email: bool = False) -> dict[str, Any]:
    """
    Execute the full Scout -> Analyst -> Executive -> Email pipeline.

    Falls back to deterministic analysis when USE_LLM=false or no API key.
    """
    collector = NewsCollector()
    raw_stories = collector.collect_all()

    if not raw_stories:
        logger.warning("No stories collected")
        return {"success": False, "error": "No stories collected"}

    if not settings.use_llm or not settings.openai_api_key:
        logger.info("Running deterministic analysis (LLM disabled)")
        return _run_deterministic_pipeline(raw_stories, send_email=send_email)

    return _run_crewai_pipeline(raw_stories, send_email=send_email)


def _run_deterministic_pipeline(
    raw_stories: list[dict[str, Any]], send_email: bool = False
) -> dict[str, Any]:
    from ai_observatory.email_service import EmailService
    from ai_observatory.pipeline import finalize_briefing

    top_stories = analyze_stories(raw_stories)
    payload = build_briefing_payload(top_stories)
    briefing_date = date.today()
    subject = f"Executive AI Intelligence Brief — {briefing_date.isoformat()}"

    html_body = EmailService.render_html(
        briefing_date=briefing_date,
        stories=top_stories,
        themes=payload["themes"],
        actions=payload["recommended_actions"],
        executive_summary=payload["executive_summary"],
        company_intelligence=payload.get("company_intelligence"),
        profile_name=payload.get("profile_name"),
        profile_roles=payload.get("profile_roles"),
        job_market=payload.get("job_market"),
        enterprise_adoption=payload.get("enterprise_adoption"),
        personal_cto=payload.get("personal_cto"),
    )

    email_sent = False
    if send_email:
        email_sent = EmailService().send(subject=subject, html_body=html_body)

    briefing_id = finalize_briefing(
        briefing_date=briefing_date,
        subject=subject,
        html_body=html_body,
        stories=top_stories,
        themes=payload["themes"],
        actions=payload["recommended_actions"],
        email_sent=email_sent,
        intelligence=intelligence_bundle_from_payload(payload),
    )

    return {
        "success": True,
        "mode": "deterministic",
        "briefing_id": briefing_id,
        "story_count": len(top_stories),
        "email_sent": email_sent,
        "themes": payload["themes"],
    }


def _run_crewai_pipeline(
    raw_stories: list[dict[str, Any]], send_email: bool = False
) -> dict[str, Any]:
    from ai_observatory.email_service import EmailService
    from ai_observatory.pipeline import finalize_briefing

    Agent, Crew, _, Process, Task = _crewai_types()
    llm = _llm()
    stories_json = stories_to_json(raw_stories[:40])

    scout = Agent(
        role="AI Intelligence Scout",
        goal="Collect and summarize the most important AI news for enterprise technology leaders.",
        backstory=(
            "You monitor OpenAI, Anthropic, Google DeepMind, Meta, Microsoft, NVIDIA, "
            "Reuters, and TechCrunch for strategic AI developments."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )

    analyst = Agent(
        role="AI Intelligence Analyst",
        goal="Deduplicate stories, score relevance 1-10, and keep the top 10 with rationale.",
        backstory=(
            "You translate AI news into enterprise relevance for CIOs, TPMs, and AI "
            "transformation leaders."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )

    executive = Agent(
        role="Executive Briefing Author",
        goal="Produce an executive AI intelligence brief with themes and recommended actions.",
        backstory=(
            "You write concise executive briefings for technology leadership teams and PMOs."
        ),
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )

    email_agent = Agent(
        role="Email Briefing Publisher",
        goal="Prepare a polished HTML email briefing ready for SMTP delivery.",
        backstory="You format executive communications for daily email distribution.",
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )

    scout_task = Task(
        description=(
            "Review the collected AI news JSON below. Confirm coverage and highlight any "
            "gaps for enterprise leaders.\n\n"
            f"RAW STORIES JSON:\n{stories_json}"
        ),
        expected_output="A short summary of collected stories and source coverage.",
        agent=scout,
    )

    analyst_task = Task(
        description=(
            "Analyze the raw stories. Deduplicate near-duplicates, score each story 1-10 "
            "for enterprise technology leaders, keep top 10, and explain why each matters. "
            "Return ONLY valid JSON with this schema:\n"
            '{"stories":[{"title":"","url":"","source":"","relevance_score":8.5,'
            '"why_it_matters":"","enterprise_impact":"","summary":""}],'
            '"executive_summary":"","themes":[],"recommended_actions":[]}'
            f"\n\nRAW STORIES JSON:\n{stories_json}"
        ),
        expected_output="Valid JSON briefing object with stories array.",
        agent=analyst,
        context=[scout_task],
    )

    executive_task = Task(
        description=(
            "Using the analyst output, produce an executive briefing JSON with:\n"
            "- executive_summary\n- themes (list)\n- recommended_actions (list)\n"
            "- stories (top 10 with why_it_matters and enterprise_impact)\n"
            "Return ONLY valid JSON."
        ),
        expected_output="Executive briefing JSON with themes and recommended actions.",
        agent=executive,
        context=[analyst_task],
    )

    email_task = Task(
        description=(
            "Using the executive briefing, produce email-ready content JSON with:\n"
            "- subject\n- executive_summary\n- html_body (full responsive HTML email)\n"
            "- stories, themes, recommended_actions\n"
            "Use professional styling suitable for CIOs and technology leaders."
        ),
        expected_output="Valid JSON with subject, html_body, and briefing fields.",
        agent=email_agent,
        context=[executive_task],
    )

    crew = Crew(
        agents=[scout, analyst, executive, email_agent],
        tasks=[scout_task, analyst_task, executive_task, email_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("Starting CrewAI pipeline")
    with CrewExecutionTimer() as timer:
        result = crew.kickoff()

    parsed, parse_result = _parse_crew_output(result, raw_stories, timer.elapsed_ms)

    briefing_date = date.today()
    subject = parsed.get("subject") or f"Executive AI Intelligence Brief — {briefing_date.isoformat()}"
    html_body = parsed.get("html_body") or EmailService.render_html(
        briefing_date=briefing_date,
        stories=parsed["stories"],
        themes=parsed["themes"],
        actions=parsed["recommended_actions"],
        executive_summary=parsed.get("executive_summary", ""),
        company_intelligence=parsed.get("company_intelligence"),
        profile_name=parsed.get("profile_name"),
        profile_roles=parsed.get("profile_roles"),
        job_market=parsed.get("job_market"),
        enterprise_adoption=parsed.get("enterprise_adoption"),
        personal_cto=parsed.get("personal_cto"),
    )

    email_sent = False
    if send_email:
        email_sent = EmailService().send(subject=subject, html_body=html_body)

    briefing_id = finalize_briefing(
        briefing_date=briefing_date,
        subject=subject,
        html_body=html_body,
        stories=parsed["stories"],
        themes=parsed["themes"],
        actions=parsed["recommended_actions"],
        email_sent=email_sent,
        intelligence=intelligence_bundle_from_payload(parsed),
    )

    return {
        "success": True,
        "mode": "crewai",
        "briefing_id": briefing_id,
        "story_count": len(parsed["stories"]),
        "email_sent": email_sent,
        "themes": parsed["themes"],
        "crew_parse_status": parse_result.parse_status,
        "crew_used_fallback": parse_result.used_fallback,
        "crew_execution_time_ms": parse_result.execution_time_ms,
        "crew_token_usage": parse_result.token_usage,
    }


def _parse_crew_output(
    result: Any,
    fallback_stories: list[dict[str, Any]],
    execution_time_ms: float,
) -> tuple[dict[str, Any], ParseResult]:
    """Parse crew output with repair, validation, and deterministic fallback."""
    from ai_observatory.intelligence import enrich_stories

    parse_result = parse_crew_output(result, execution_time_ms)

    if parse_result.success and parse_result.validated_data:
        data = parse_result.validated_data
        enriched = enrich_stories(data["stories"])
        payload = build_briefing_payload(enriched)
        return {
            "stories": enriched,
            "themes": data.get("themes") or payload["themes"],
            "recommended_actions": data.get("recommended_actions") or payload["recommended_actions"],
            "executive_summary": data.get("executive_summary") or payload["executive_summary"],
            "subject": data.get("subject"),
            "html_body": data.get("html_body"),
            "company_intelligence": payload.get("company_intelligence"),
            "profile_name": payload.get("profile_name"),
            "profile_roles": payload.get("profile_roles"),
            "job_market": payload.get("job_market"),
            "enterprise_adoption": payload.get("enterprise_adoption"),
            "personal_cto": payload.get("personal_cto"),
        }, parse_result

    logger.warning(
        "Crew output parse failed; using deterministic fallback",
        extra={
            "parse_status": parse_result.parse_status,
            "parse_error": parse_result.parse_error,
            "repair_steps": parse_result.repair_steps,
        },
    )
    top_stories = analyze_stories(fallback_stories)
    payload = build_briefing_payload(top_stories)
    return {
        "stories": top_stories,
        "themes": payload["themes"],
        "recommended_actions": payload["recommended_actions"],
        "executive_summary": payload["executive_summary"],
        "subject": None,
        "html_body": None,
        "company_intelligence": payload.get("company_intelligence"),
        "profile_name": payload.get("profile_name"),
        "profile_roles": payload.get("profile_roles"),
        "job_market": payload.get("job_market"),
        "enterprise_adoption": payload.get("enterprise_adoption"),
        "personal_cto": payload.get("personal_cto"),
    }, parse_result
