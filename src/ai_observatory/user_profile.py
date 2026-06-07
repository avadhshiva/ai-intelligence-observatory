"""User profile loading for personal relevance scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_observatory.config import PROJECT_ROOT

DEFAULT_PROFILE_PATH = PROJECT_ROOT / "config" / "user_profile.json"
EXAMPLE_PROFILE_PATH = PROJECT_ROOT / "config" / "user_profile.example.json"

DEFAULT_PROFILE: dict[str, Any] = {
    "name": "Technology Leader",
    "roles": ["TPM", "AI Transformation Manager", "Delivery Leader"],
    "focus_areas": [
        "enterprise adoption",
        "program delivery",
        "governance",
        "agents",
        "infrastructure",
        "vendor strategy",
    ],
    "priority_companies": ["OpenAI", "Anthropic", "Google", "Microsoft", "AWS", "NVIDIA"],
    "industry": "Technology",
}


@dataclass
class UserProfile:
    name: str = "Technology Leader"
    roles: list[str] = field(default_factory=lambda: list(DEFAULT_PROFILE["roles"]))
    focus_areas: list[str] = field(default_factory=lambda: list(DEFAULT_PROFILE["focus_areas"]))
    priority_companies: list[str] = field(
        default_factory=lambda: list(DEFAULT_PROFILE["priority_companies"])
    )
    industry: str = "Technology"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserProfile:
        return cls(
            name=data.get("name", DEFAULT_PROFILE["name"]),
            roles=list(data.get("roles", DEFAULT_PROFILE["roles"])),
            focus_areas=list(data.get("focus_areas", DEFAULT_PROFILE["focus_areas"])),
            priority_companies=list(
                data.get("priority_companies", DEFAULT_PROFILE["priority_companies"])
            ),
            industry=data.get("industry", DEFAULT_PROFILE["industry"]),
        )


def load_user_profile(path: Path | None = None) -> UserProfile:
    profile_path = path or DEFAULT_PROFILE_PATH
    if profile_path.exists():
        return UserProfile.from_dict(json.loads(profile_path.read_text(encoding="utf-8")))
    if EXAMPLE_PROFILE_PATH.exists():
        return UserProfile.from_dict(json.loads(EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")))
    return UserProfile.from_dict(DEFAULT_PROFILE)
