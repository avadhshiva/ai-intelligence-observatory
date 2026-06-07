"""HTML email rendering and Gmail SMTP delivery."""

from __future__ import annotations

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from jinja2 import Template

from ai_observatory.config import settings
from ai_observatory.logging_setup import logger

EMAIL_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ subject }}</title>
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; line-height: 1.6; margin: 0; padding: 0; background: #f4f6fb; }
    .container { max-width: 720px; margin: 0 auto; background: #ffffff; }
    .header { background: linear-gradient(135deg, #0f3460, #16213e); color: #fff; padding: 28px 32px; }
    .header h1 { margin: 0 0 8px; font-size: 24px; }
    .header p { margin: 0; opacity: 0.9; }
    .section { padding: 24px 32px; border-bottom: 1px solid #e8ecf4; }
    .section h2 { color: #0f3460; font-size: 18px; margin-top: 0; }
    .story { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px dashed #dde3ef; }
    .story:last-child { border-bottom: none; }
    .score { display: inline-block; background: #e94560; color: #fff; font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 12px; margin-right: 6px; }
    .score-personal { background: #2563eb; }
    .meta { color: #6b7280; font-size: 13px; margin: 4px 0; }
    .tag { display: inline-block; background: #eef2ff; color: #3730a3; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-right: 4px; }
    ul { padding-left: 20px; }
    li { margin-bottom: 8px; }
    .footer { padding: 20px 32px; font-size: 12px; color: #6b7280; background: #f9fafb; }
    a { color: #2563eb; text-decoration: none; }
    .source-link { display: inline-block; margin-top: 8px; font-weight: 600; }
    .company-row { margin-bottom: 8px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Executive AI Intelligence Brief</h1>
      <p>{{ briefing_date }} · Personalized for {{ profile_name }} ({{ profile_roles|join(', ') }})</p>
    </div>

    <div class="section">
      <h2>Executive Summary</h2>
      <p>{{ executive_summary }}</p>
    </div>

    {% if company_intelligence and company_intelligence.most_active %}
    <div class="section">
      <h2>Company Intelligence</h2>
      {% for company in company_intelligence.most_active %}
      <div class="company-row">
        <strong>{{ company }}</strong> — {{ company_intelligence.companies[company].story_count }} stories
        {% if company_intelligence.companies[company].headlines %}
        <ul>
          {% for h in company_intelligence.companies[company].headlines %}
          <li><a href="{{ h.url }}">{{ h.title }}</a></li>
          {% endfor %}
        </ul>
        {% endif %}
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <div class="section">
      <h2>Top {{ stories|length }} Stories</h2>
      {% for story in stories %}
      <div class="story">
        <div>
          <span class="score">{{ story.final_score or story.relevance_score }}/10</span>
          {% if story.personal_relevance_score %}
          <span class="score score-personal">Personal {{ story.personal_relevance_score }}/10</span>
          {% endif %}
          {% if story.category %}<span class="tag">{{ story.category }}</span>{% endif %}
          {% for co in story.companies or [] %}<span class="tag">{{ co }}</span>{% endfor %}
        </div>
        <h3 style="margin:8px 0 4px;font-size:16px;">
          <a href="{{ story.url }}">{{ story.title }}</a>
        </h3>
        <div class="meta">{{ story.source }}</div>
        <a class="source-link" href="{{ story.url }}">Read source →</a>
        <p><strong>Why it matters:</strong> {{ story.why_it_matters }}</p>
        <p><strong>Enterprise impact:</strong> {{ story.enterprise_impact }}</p>
        {% if story.why_this_matters_to_me %}
        <p><strong>Why this matters to me:</strong> {{ story.why_this_matters_to_me }}</p>
        {% endif %}
        {% if story.cto_recommended_action %}
        <p><strong>Recommended action:</strong> {{ story.cto_recommended_action }}</p>
        {% endif %}
        {% if story.career_impact_summary %}
        <p><strong>Career impact:</strong> {{ story.career_impact_summary }}</p>
        {% endif %}
      </div>
      {% endfor %}
    </div>

    {% if personal_cto and personal_cto.skills_to_learn %}
    <div class="section">
      <h2>Personal CTO — Skills To Learn</h2>
      <ul>
        {% for skill in personal_cto.skills_to_learn %}
        <li>{{ skill }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    {% if job_market %}
    <div class="section">
      <h2>AI Job Market Pulse</h2>
      <p>{{ job_market.summary }}</p>
      {% if job_market.top_categories %}
      <p><strong>Top role demand:</strong> {{ job_market.top_categories|join(', ') }}</p>
      {% endif %}
      {% if job_market.emerging_skills %}
      <ul>
        {% for s in job_market.emerging_skills[:5] %}
        <li>{{ s.skill }} ({{ s.demand_signal }})</li>
        {% endfor %}
      </ul>
      {% endif %}
    </div>
    {% endif %}

    {% if enterprise_adoption and enterprise_adoption.active_industries %}
    <div class="section">
      <h2>Enterprise Adoption Tracker</h2>
      <p>{{ enterprise_adoption.summary }}</p>
      <ul>
        {% for note in enterprise_adoption.notable_implementations[:4] %}
        <li>{{ note }}</li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}

    <div class="section">
      <h2>Emerging Themes</h2>
      <ul>
        {% for theme in themes %}
        <li>{{ theme }}</li>
        {% endfor %}
      </ul>
    </div>

    <div class="section">
      <h2>Recommended Actions</h2>
      <ul>
        {% for action in actions %}
        <li>{{ action }}</li>
        {% endfor %}
      </ul>
    </div>

    <div class="footer">
      Generated by AI Intelligence Observatory · Personal AI Intelligence Observatory
    </div>
  </div>
</body>
</html>
"""
)


class EmailService:
    """Render and send executive briefing emails."""

    @staticmethod
    def render_html(
        briefing_date: date,
        stories: list[dict[str, Any]],
        themes: list[str],
        actions: list[str],
        executive_summary: str,
        company_intelligence: dict[str, Any] | None = None,
        profile_name: str | None = None,
        profile_roles: list[str] | None = None,
        job_market: dict[str, Any] | None = None,
        enterprise_adoption: dict[str, Any] | None = None,
        personal_cto: dict[str, Any] | None = None,
    ) -> str:
        subject = f"Executive AI Intelligence Brief — {briefing_date.isoformat()}"
        return EMAIL_TEMPLATE.render(
            subject=subject,
            briefing_date=briefing_date.isoformat(),
            stories=stories,
            themes=themes,
            actions=actions,
            executive_summary=executive_summary,
            company_intelligence=company_intelligence,
            profile_name=profile_name or "Technology Leader",
            profile_roles=profile_roles or ["TPM", "AI Transformation Manager", "Delivery Leader"],
            job_market=job_market,
            enterprise_adoption=enterprise_adoption,
            personal_cto=personal_cto,
        )

    def send(self, subject: str, html_body: str, recipients: list[str] | None = None) -> bool:
        recipients = recipients or settings.email_recipients
        if not recipients:
            logger.warning("No email recipients configured")
            return False
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("SMTP credentials not configured")
            return False

        sender = settings.email_from or settings.smtp_user
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(sender, recipients, message.as_string())
            logger.info("Email sent", extra={"recipients": recipients, "subject": subject})
            return True
        except Exception as exc:
            logger.error("Email send failed", extra={"error": str(exc)})
            return False
