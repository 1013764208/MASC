from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class RuntimeConfig:
    """运行时配置。

    通过环境变量读取模型名称、API key、base URL、超时时间和重试次数。
    兼容 OpenAI-style API，也可以通过 KIMI_* 环境变量接入 Kimi/Moonshot。
    """

    model_name: str = getenv("AGENTSCOPE_MODEL_NAME", "kimi-k2.5")
    api_key: str | None = getenv("OPENAI_API_KEY") or getenv("KIMI_API_KEY")
    api_base: str | None = getenv("OPENAI_BASE_URL") or getenv("KIMI_BASE_URL")
    timeout_seconds: float = float(getenv("SCRIPT_LAB_TIMEOUT", "120"))
    max_retries: int = int(getenv("SCRIPT_LAB_MAX_RETRIES", "2"))


# 每个 Agent 的系统提示词。更具体的 JSON schema 会在 agents.py 的 prompt builder 中补充。
SYSTEM_PROMPTS = {
    "planner": (
        "你是 Planner Agent，负责将用户需求拆成分幕分场大纲。"
        "输出必须结构化，强调开端、冲突、升级、高潮、收束。"
    ),
    "character": "你是 Character Agent，负责生成角色卡，并检查人物动机、关系和口癖的一致性。",
    "dialogue": "你是 Dialogue Agent，负责根据分场大纲生成自然对白，避免角色串台。",
    "editor": "你是 Editor Agent，负责润色、去重、修复矛盾并统一格式。",
    "critic": "你是 Critic / Judge Agent，负责从结构、人物、连贯性和可控性四个维度打分。",
}
