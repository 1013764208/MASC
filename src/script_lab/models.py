from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CharacterCard:
    """角色卡，用于约束人物设定和对白风格。"""

    name: str
    role: str
    personality: str
    motivation: str
    speaking_style: str
    relationship: str


@dataclass
class SceneBeat:
    """单个分场大纲节点。"""

    index: int
    location: str
    time_of_day: str
    mood: str
    purpose: str
    conflict: str


@dataclass
class ScriptRequest:
    """用户输入的剧本生成请求。"""

    genre: str
    title_hint: str
    characters: list[dict[str, str]]
    setting: str
    constraints: list[str] = field(default_factory=list)
    length_hint: str = "中短篇"
    style_hint: str = "自然、电影感"


@dataclass
class ScriptDraft:
    """流水线最终产出的剧本草稿。"""

    title: str
    logline: str
    character_cards: list[CharacterCard]
    outline: list[SceneBeat]
    scenes: list[dict[str, Any]]
    conclusion: str
    quality_score: float
    critic_notes: list[str]
    revision_history: list[dict[str, Any]] = field(default_factory=list)
