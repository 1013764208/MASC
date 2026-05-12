from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIMultiAgentFormatter
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel

from .config import RuntimeConfig, SYSTEM_PROMPTS
from .models import ScriptRequest


class AgentFactory:
    """Agent 工厂类，统一创建项目中的各类 Agent。

    这里复用同一个模型实例和 formatter，避免每个 Agent 重复初始化底层客户端。
    如果没有配置 API key，`has_model` 会返回 False，流水线将自动走本地兜底。
    """

    def __init__(self, config: RuntimeConfig | None = None):
        self.config = config or RuntimeConfig()
        self.formatter = OpenAIMultiAgentFormatter()
        self.model = None
        if self.config.api_key:
            client_kwargs: dict[str, Any] = {
                "timeout": self.config.timeout_seconds,
                "max_retries": self.config.max_retries,
            }
            if self.config.api_base:
                client_kwargs["base_url"] = self.config.api_base
            self.model = OpenAIChatModel(
                model_name=self.config.model_name,
                api_key=self.config.api_key,
                client_kwargs=client_kwargs,
            )

    @property
    def has_model(self) -> bool:
        """是否已经成功配置可用模型。"""
        return self.model is not None

    def _build(self, name: str, prompt_key: str, max_iters: int) -> ReActAgent:
        """创建指定角色的 ReActAgent。"""
        if self.model is None:
            raise RuntimeError("Please set OPENAI_API_KEY or KIMI_API_KEY before running AgentScope agents.")
        return ReActAgent(
            name=name,
            sys_prompt=SYSTEM_PROMPTS[prompt_key],
            model=self.model,
            formatter=self.formatter,
            max_iters=max_iters,
        )

    def planner(self) -> ReActAgent:
        return self._build("planner", "planner", 3)

    def character(self) -> ReActAgent:
        return self._build("character", "character", 3)

    def dialogue(self) -> ReActAgent:
        return self._build("dialogue", "dialogue", 4)

    def editor(self) -> ReActAgent:
        return self._build("editor", "editor", 2)

    def critic(self) -> ReActAgent:
        return self._build("critic", "critic", 2)


def request_to_prompt(request: ScriptRequest) -> str:
    """把用户请求转成模型容易理解的 JSON 文本。"""
    return json.dumps(asdict(request), ensure_ascii=False, indent=2)


def build_planner_prompt(request: ScriptRequest) -> str:
    """构造 Planner Agent 的提示词。"""
    return (
        "请根据以下需求生成剧本大纲，只输出 JSON，不要输出解释文字。\n"
        "JSON schema:\n"
        "{\n"
        '  "title": string,\n'
        '  "logline": string,\n'
        '  "outline": [\n'
        '    {"index": number, "location": string, "time_of_day": string, "mood": string, "purpose": string, "conflict": string}\n'
        "  ]\n"
        "}\n"
        f"需求:\n{request_to_prompt(request)}"
    )


def build_character_prompt(request: ScriptRequest, planner_output: dict[str, Any]) -> str:
    """构造 Character Agent 的提示词。"""
    return (
        "请根据需求和大纲生成角色卡，只输出 JSON，不要输出解释文字。\n"
        "JSON schema:\n"
        "{\n"
        '  "character_cards": [\n'
        '    {"name": string, "role": string, "personality": string, "motivation": string, "speaking_style": string, "relationship": string}\n'
        "  ]\n"
        "}\n"
        f"需求:\n{request_to_prompt(request)}\n"
        f"大纲:\n{json.dumps(planner_output, ensure_ascii=False, indent=2)}"
    )


def build_dialogue_prompt(request: ScriptRequest, planner_output: dict[str, Any], character_output: dict[str, Any]) -> str:
    """构造 Dialogue Agent 的提示词。"""
    return (
        "请根据需求、大纲和角色卡生成完整分场对白，只输出 JSON，不要输出解释文字。\n"
        "JSON schema:\n"
        "{\n"
        '  "scenes": [\n'
        '    {"scene": number, "beat": object, "dialogue": [{"character": string, "line": string}]}\n'
        "  ],\n"
        '  "conclusion": string\n'
        "}\n"
        f"需求:\n{request_to_prompt(request)}\n"
        f"大纲:\n{json.dumps(planner_output, ensure_ascii=False, indent=2)}\n"
        f"角色卡:\n{json.dumps(character_output, ensure_ascii=False, indent=2)}"
    )


def build_editor_prompt(
    request: ScriptRequest,
    planner_output: dict[str, Any],
    character_output: dict[str, Any],
    dialogue_output: dict[str, Any],
) -> str:
    """构造 Editor Agent 的提示词。"""
    return (
        "请对以下剧本内容进行润色与统一，修复冲突、强化戏剧性，只输出 JSON。\n"
        "JSON schema:\n"
        "{\n"
        '  "title": string,\n'
        '  "logline": string,\n'
        '  "outline": array,\n'
        '  "scenes": array,\n'
        '  "conclusion": string\n'
        "}\n"
        f"需求:\n{request_to_prompt(request)}\n"
        f"大纲:\n{json.dumps(planner_output, ensure_ascii=False, indent=2)}\n"
        f"角色卡:\n{json.dumps(character_output, ensure_ascii=False, indent=2)}\n"
        f"对白:\n{json.dumps(dialogue_output, ensure_ascii=False, indent=2)}"
    )


def build_critic_prompt(script_payload: dict[str, Any]) -> str:
    """构造 Critic Agent 的提示词。"""
    return (
        "请从结构、人物、连贯性、可控性四个维度评分，只输出 JSON。\n"
        "JSON schema:\n"
        "{\n"
        '  "score": number,\n'
        '  "notes": [string]\n'
        "}\n"
        f"剧本:\n{json.dumps(script_payload, ensure_ascii=False, indent=2)}"
    )


def extract_json(text: str) -> dict[str, Any]:
    """从模型文本中提取 JSON 对象。

    AgentScope 的控制台输出可能是 `planner: ```json ... ```，模型也可能输出
    裸 JSON。这里优先解析 fenced code block，再用括号配对方式截取第一个
    完整 JSON 对象，避免非贪婪正则只截到内部小对象。
    """
    cleaned = text.strip()
    candidates: list[str] = []
    candidates.extend(re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE))

    start = cleaned.find("{")
    if start >= 0:
        depth = 0
        in_string = False
        escaped = False
        for idx, char in enumerate(cleaned[start:], start=start):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(cleaned[start : idx + 1])
                    break
    candidates.append(cleaned)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(f"Failed to parse JSON from agent output: {text[:500]}") from last_error


def _block_to_text(block: Any) -> str:
    """把 AgentScope 的消息块转换为纯文本。"""
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        block_type = block.get("type")
        if block_type in {"text", "output_text"}:
            return str(block.get("text") or block.get("content") or "")
        if block_type == "thinking":
            return ""
        return str(block.get("text") or block.get("content") or "")
    block_type = getattr(block, "type", None)
    if block_type == "thinking":
        return ""
    return str(getattr(block, "text", None) or getattr(block, "content", None) or block)


def message_to_text(message: Any) -> str:
    """从 AgentScope Msg 中提取可解析文本。"""
    content = message.content if hasattr(message, "content") else message
    if isinstance(content, list):
        return "\n".join(part for part in (_block_to_text(item) for item in content) if part.strip())
    return _block_to_text(content)


async def agent_json_reply(agent: ReActAgent, prompt: str) -> dict[str, Any]:
    """调用 Agent，并将其回复解析为 JSON 字典。"""
    response = await agent.reply(Msg(name="user", content=prompt, role="user"))
    return extract_json(message_to_text(response))
