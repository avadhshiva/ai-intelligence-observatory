"""Pydantic schemas for CrewAI briefing output validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CrewStorySchema(BaseModel):
    title: str = Field(min_length=1)
    url: str = ""
    source: str = ""
    relevance_score: float = Field(default=5.0, ge=1.0, le=10.0)
    why_it_matters: str = ""
    enterprise_impact: str = ""
    summary: str = ""


class CrewBriefingSchema(BaseModel):
    stories: list[CrewStorySchema] = Field(min_length=1)
    executive_summary: str | None = None
    themes: list[str] | None = None
    recommended_actions: list[str] | None = None
    subject: str | None = None
    html_body: str | None = None

    @field_validator("stories")
    @classmethod
    def validate_stories_not_empty(cls, value: list[CrewStorySchema]) -> list[CrewStorySchema]:
        if not value:
            raise ValueError("stories must contain at least one item")
        return value
