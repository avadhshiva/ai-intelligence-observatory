"""Executive Streamlit dashboard — trends, companies, categories, evolution."""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_observatory.agents.company_intelligence import TRACKED_COMPANIES
from ai_observatory.crew_metrics import (
    get_crew_diagnostics_summary,
    list_crew_parse_runs,
    load_raw_crew_output_file,
)
from ai_observatory.database import (
    get_briefing_by_date,
    get_category_history,
    get_company_activity_history,
    get_enterprise_adoption_history,
    get_latest_job_market_snapshot,
    get_trend_data,
    init_db,
    list_briefings,
    list_weekly_pdfs,
    list_weekly_reports,
)
from ai_observatory.user_profile import load_user_profile

st.set_page_config(page_title="AI Intelligence Observatory", page_icon="🔭", layout="wide")

profile = load_user_profile()
st.title("Personal AI Intelligence Observatory")
st.caption(
    f"Executive dashboard for {profile.name} · "
    f"{', '.join(profile.roles)} · "
    f"Tracking {', '.join(profile.priority_companies)}"
)

init_db()

briefings = list_briefings(limit=90)
trends = get_trend_data(days=60)
company_history = get_company_activity_history(days=60)
category_history = get_category_history(days=60)
weekly_reports = list_weekly_reports(limit=8)
weekly_pdfs = list_weekly_pdfs(limit=8)
job_market = get_latest_job_market_snapshot()
enterprise_history = get_enterprise_adoption_history(days=60)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Briefings Stored", len(briefings))
with c2:
    st.metric("Weekly Reports", len(weekly_reports))
with c3:
    avg = round(sum(b["avg_relevance"] or 0 for b in briefings) / len(briefings), 2) if briefings else 0
    st.metric("Avg Final Score", avg)
with c4:
    st.metric("Tracked Companies", len(TRACKED_COMPANIES))

st.divider()

(
    tab_exec,
    tab_briefing,
    tab_trends,
    tab_companies,
    tab_categories,
    tab_weekly,
    tab_job,
    tab_cto,
    tab_enterprise,
    tab_pdf,
    tab_diag,
) = st.tabs(
    [
        "Executive Overview",
        "Briefing Detail",
        "Trends",
        "Company Activity",
        "Story Categories",
        "Weekly Reports",
        "Job Market",
        "Personal CTO",
        "Enterprise Adoption",
        "Weekly PDF",
        "CrewAI Diagnostics",
    ]
)

with tab_exec:
    st.subheader("Generate Briefing")
    send_email = st.checkbox("Send email after generation", value=False, key="send_email")
    if st.button("Generate Today's Briefing", type="primary"):
        from ai_observatory.crew import run_observatory_crew

        with st.spinner("Running intelligence pipeline..."):
            result = run_observatory_crew(send_email=send_email)
        if result.get("success"):
            msg = f"Briefing complete ({result.get('mode')}) — {result.get('story_count')} stories"
            if result.get("mode") == "crewai":
                msg += (
                    f" | parse: {result.get('crew_parse_status')}"
                    f" | fallback: {'yes' if result.get('crew_used_fallback') else 'no'}"
                    f" | {result.get('crew_execution_time_ms', 0):.0f} ms"
                )
            st.success(msg)
            st.rerun()
        else:
            st.error(result.get("error", "Failed"))

    if briefings:
        st.subheader("Recent Briefings")
        df = pd.DataFrame(briefings)
        st.dataframe(
            df[["briefing_date", "story_count", "avg_relevance", "email_sent", "subject"]],
            width="stretch",
            hide_index=True,
        )

with tab_briefing:
    if not briefings:
        st.info("No briefings yet.")
    else:
        selected = st.selectbox("Briefing date", [b["briefing_date"] for b in briefings])
        briefing = get_briefing_by_date(date.fromisoformat(selected))
        if briefing:
            st.markdown(f"### {briefing['subject']}")
            intel = briefing.get("intelligence", {}).get("company_intelligence", {})
            if intel.get("most_active"):
                st.markdown(f"**Most active companies:** {', '.join(intel['most_active'])}")

            for idx, story in enumerate(briefing["stories"], start=1):
                score = story.get("final_score", story.get("relevance_score", "N/A"))
                label = f"{idx}. [{score}/10] {story.get('title', '')}"
                with st.expander(label):
                    url = story.get("url", "")
                    if url:
                        st.markdown(f"[Read source →]({url})")
                    st.markdown(f"**Source:** {story.get('source', '')}")
                    st.markdown(f"**Category:** {story.get('category', 'N/A')}")
                    st.markdown(f"**Companies:** {', '.join(story.get('companies', [])) or 'N/A'}")
                    st.markdown(f"**Personal relevance:** {story.get('personal_relevance_score', 'N/A')}/10")
                    st.markdown(f"**Why it matters:** {story.get('why_it_matters', '')}")
                    st.markdown(f"**Why this matters to me:** {story.get('why_this_matters_to_me', 'N/A')}")
                    st.markdown(f"**Enterprise impact:** {story.get('enterprise_impact', '')}")
                    if story.get("career_impact"):
                        st.markdown("**Career impact by role:**")
                        for role, impact in story["career_impact"].items():
                            st.markdown(f"- **{role}:** {impact}")

            with st.expander("Preview HTML Email"):
                st.html(briefing["html_body"], width="stretch")

with tab_trends:
    if trends:
        trend_df = pd.DataFrame(trends)
        trend_df["date"] = pd.to_datetime(trend_df["date"])
        st.plotly_chart(
            px.line(trend_df, x="date", y="story_count", markers=True, title="Stories per Briefing"),
            width="stretch",
        )
        st.plotly_chart(
            px.line(trend_df, x="date", y="avg_relevance", markers=True, title="Average Score Over Time"),
            width="stretch",
        )
        theme_counter: Counter[str] = Counter()
        for row in trends:
            for theme in row.get("themes", []):
                theme_counter[theme] += 1
        if theme_counter:
            theme_df = pd.DataFrame([{"theme": k, "count": v} for k, v in theme_counter.most_common()])
            st.plotly_chart(px.bar(theme_df, x="theme", y="count", title="Theme Frequency"), width="stretch")
    else:
        st.info("Trend data appears after briefings are stored.")

with tab_companies:
    st.subheader("Company Activity Over Time")
    if company_history:
        rows = []
        for day in company_history:
            for company, count in day["companies"].items():
                rows.append({"date": day["date"], "company": company, "stories": count})
        company_df = pd.DataFrame(rows)
        if not company_df.empty:
            company_df["date"] = pd.to_datetime(company_df["date"])
            st.plotly_chart(
                px.line(company_df, x="date", y="stories", color="company", markers=True, title="Daily Company Mentions"),
                width="stretch",
            )
            latest = briefings[0] if briefings else None
            if latest:
                full = get_briefing_by_date(date.fromisoformat(latest["briefing_date"]))
                if full:
                    intel = full.get("intelligence", {}).get("company_intelligence", {})
                    for company in TRACKED_COMPANIES:
                        data = intel.get("companies", {}).get(company, {})
                        st.markdown(f"**{company}** — {data.get('story_count', 0)} stories today")
                        for headline in data.get("headlines", []):
                            st.markdown(f"- [{headline.get('title')}]({headline.get('url')})")
    else:
        st.info("Company activity history builds as briefings accumulate.")

with tab_categories:
    st.subheader("Story Category Evolution")
    if category_history:
        rows = []
        for day in category_history:
            for category, count in day["categories"].items():
                rows.append({"date": day["date"], "category": category, "count": count})
        cat_df = pd.DataFrame(rows)
        cat_df["date"] = pd.to_datetime(cat_df["date"])
        st.plotly_chart(
            px.area(cat_df, x="date", y="count", color="category", title="Category Distribution Over Time"),
            width="stretch",
        )
        totals = cat_df.groupby("category")["count"].sum().reset_index().sort_values("count", ascending=False)
        st.plotly_chart(px.bar(totals, x="category", y="count", title="Total Stories by Category"), width="stretch")
    else:
        st.info("Category history appears after briefings are stored.")

with tab_weekly:
    st.subheader("Weekly Trend Reports")
    if st.button("Generate Weekly Report Now"):
        from ai_observatory.agents.weekly_trends import generate_weekly_report

        report = generate_weekly_report()
        st.success(report.get("executive_summary", "Report generated"))
        st.rerun()

    if weekly_reports:
        pick = st.selectbox(
            "Select week",
            [f"{r['week_start']} → {r['week_end']}" for r in weekly_reports],
        )
        report = next(r["report"] for r in weekly_reports if f"{r['week_start']} → {r['week_end']}" == pick)
        st.markdown(f"**Summary:** {report.get('executive_summary', '')}")
        st.markdown(f"**Briefings:** {report.get('briefing_count', 0)} · **Stories:** {report.get('story_count', 0)}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Rising Themes")
            for theme in report.get("rising_themes", []):
                st.markdown(f"- {theme}")
        with c2:
            st.markdown("#### Most Active Companies")
            for company in report.get("most_active_companies", []):
                st.markdown(f"- {company}")

        if report.get("category_frequency"):
            cat_df = pd.DataFrame(
                [{"category": k, "count": v} for k, v in report["category_frequency"].items()]
            )
            st.plotly_chart(px.pie(cat_df, names="category", values="count", title="Weekly Category Mix"), width="stretch")
    else:
        st.info("Weekly reports generate automatically on Sundays or via the button above.")

with tab_job:
    st.subheader("AI Job Market Intelligence")
    if job_market:
        st.markdown(f"**Daily summary:** {job_market.get('summary', '')}")
        if job_market.get("category_demand"):
            jdf = pd.DataFrame(
                [{"role": k, "mentions": v} for k, v in job_market["category_demand"].items()]
            ).sort_values("mentions", ascending=False)
            st.plotly_chart(px.bar(jdf, x="role", y="mentions", title="Role Demand Signals (Today)"), width="stretch")
        if job_market.get("emerging_skills"):
            st.markdown("#### Emerging Skills")
            for skill in job_market["emerging_skills"]:
                st.markdown(f"- **{skill['skill']}** — {skill['demand_signal']} ({skill['mentions']} mentions)")
    else:
        st.info("Run a briefing to populate job market intelligence.")

with tab_cto:
    st.subheader("Personal CTO Agent")
    if briefings:
        latest = get_briefing_by_date(date.fromisoformat(briefings[0]["briefing_date"]))
        cto = (latest or {}).get("intelligence", {}).get("personal_cto", {})
        if cto:
            st.markdown(f"**{cto.get('executive_summary', '')}**")
            st.markdown(f"**Daily priority:** {cto.get('daily_priority', 'N/A')}")
            st.markdown("#### Recommended Actions")
            for action in cto.get("recommended_actions", []):
                st.markdown(f"- {action}")
            st.markdown("#### Skills To Learn")
            for skill in cto.get("skills_to_learn", []):
                st.markdown(f"- {skill}")
            st.markdown("#### Story Insights")
            for insight in cto.get("story_insights", []):
                with st.expander(insight.get("title", "Story")):
                    st.markdown(f"[Read source →]({insight.get('url', '')})")
                    st.markdown(insight.get("why_this_matters_to_me", ""))
                    st.markdown(f"**Action:** {insight.get('recommended_action', '')}")
        else:
            st.info("Personal CTO brief appears after the next briefing run.")
    else:
        st.info("No briefings available.")

with tab_enterprise:
    st.subheader("Enterprise Adoption Tracker")
    if enterprise_history:
        rows = []
        for day in enterprise_history:
            for industry, data in day.get("industries", {}).items():
                if data.get("active"):
                    rows.append({"date": day["date"], "industry": industry, "stories": data.get("story_count", 0)})
        if rows:
            edf = pd.DataFrame(rows)
            edf["date"] = pd.to_datetime(edf["date"])
            st.plotly_chart(
                px.line(edf, x="date", y="stories", color="industry", markers=True, title="Industry Adoption Signals"),
                width="stretch",
            )
        latest = enterprise_history[-1]
        st.markdown(f"**Latest:** {latest.get('summary', '')}")
        for note in latest.get("notable_implementations", []):
            st.markdown(f"- {note}")
    else:
        st.info("Enterprise adoption data builds as briefings accumulate.")

with tab_pdf:
    st.subheader("Weekly Executive PDF Reports")
    if st.button("Generate Weekly PDF Now"):
        from ai_observatory.reports.pdf_generator import generate_weekly_pdf

        path = generate_weekly_pdf()
        st.success(f"PDF generated: {path}")
        st.rerun()

    if weekly_pdfs:
        for item in weekly_pdfs:
            st.markdown(f"**Week of {item['week_start']}** — `{item['pdf_path']}`")
            payload = item.get("payload", {})
            st.markdown(payload.get("personal_cto_summary", ""))
            with open(item["pdf_path"], "rb") as f:
                st.download_button(
                    label=f"Download PDF ({item['week_start']})",
                    data=f.read(),
                    file_name=Path(item["pdf_path"]).name,
                    mime="application/pdf",
                )
    else:
        st.info("Weekly PDFs generate on Sundays or via the button above.")

with tab_diag:
    st.subheader("CrewAI Output Diagnostics")
    summary = get_crew_diagnostics_summary()
    runs = list_crew_parse_runs(limit=30)
    raw_history = load_raw_crew_output_file()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Runs", summary["total_runs"])
    m2.metric("Success Rate", f"{summary['success_rate']}%")
    m3.metric("Fallback Rate", f"{summary['fallback_rate']}%")
    m4.metric("Avg Execution (ms)", summary["avg_execution_time_ms"])
    m5.metric("Avg Tokens / Run", summary["avg_tokens_per_run"])

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Parse Status")
        if runs:
            status_df = pd.DataFrame(
                [
                    {
                        "run_at": r["run_at"],
                        "parse_status": r["parse_status"],
                        "used_fallback": r["used_fallback"],
                        "execution_time_ms": r["execution_time_ms"],
                    }
                    for r in runs
                ]
            )
            st.dataframe(status_df, width="stretch", hide_index=True)
        else:
            st.info("No CrewAI parse runs recorded yet. Run with USE_LLM=true to populate.")

        st.markdown("#### Fallback Usage")
        if runs:
            fallback_df = pd.DataFrame(
                [{"run_at": r["run_at"], "used_fallback": r["used_fallback"]} for r in runs]
            )
            fallback_df["used_fallback"] = fallback_df["used_fallback"].map(
                {True: "Yes", False: "No"}
            )
            st.dataframe(fallback_df, width="stretch", hide_index=True)

    with col_right:
        st.markdown("#### Parse Errors")
        error_rows = [r for r in runs if r.get("parse_error")]
        if error_rows:
            for row in error_rows[:10]:
                st.error(f"**{row['run_at']}** — {row['parse_error']}")
                if row.get("repair_steps"):
                    st.caption(f"Repair steps attempted: {', '.join(row['repair_steps'])}")
        else:
            st.success("No parse errors in recent runs.")

        st.markdown("#### Token Usage")
        if runs:
            token_rows = []
            for r in runs:
                usage = r.get("token_usage") or {}
                token_rows.append(
                    {
                        "run_at": r["run_at"],
                        "total_tokens": usage.get("total_tokens", 0),
                        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                        "completion_tokens": usage.get(
                            "completion_tokens", usage.get("output_tokens", 0)
                        ),
                    }
                )
            st.dataframe(pd.DataFrame(token_rows), width="stretch", hide_index=True)
        else:
            st.info("Token usage appears after CrewAI runs.")

    st.divider()
    st.markdown("#### CrewAI Raw Output")
    if raw_history:
        selected_idx = st.selectbox(
            "Select capture",
            range(len(raw_history)),
            format_func=lambda i: (
                f"{raw_history[-(i + 1)].get('timestamp', 'unknown')} — "
                f"{raw_history[-(i + 1)].get('parse_status', 'unknown')}"
            ),
        )
        record = raw_history[-(selected_idx + 1)]
        st.caption(
            f"Status: **{record.get('parse_status')}** | "
            f"Execution: **{record.get('execution_time_ms', 0):.0f} ms** | "
            f"Repair: **{', '.join(record.get('repair_steps') or []) or 'none'}**"
        )
        if record.get("parse_error"):
            st.warning(record["parse_error"])
        st.code(record.get("raw_output", ""), language="json")
    else:
        st.info(
            "Raw CrewAI output is saved to `logs/raw_crewai_output.json` after each LLM run."
        )
