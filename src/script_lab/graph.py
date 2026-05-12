from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from .agents import (
    AgentFactory,
    agent_json_reply,
    build_character_prompt,
    build_critic_prompt,
    build_dialogue_prompt,
    build_editor_prompt,
    build_planner_prompt,
)
from .models import CharacterCard, SceneBeat, ScriptDraft, ScriptRequest
from .rl import RLRefiner


class ScriptPipeline:
    """多智能体剧本生成主流水线。

    该类负责按顺序调用 Planner、Character、Dialogue、Editor、Critic 等 Agent，
    并把各阶段输出组装成最终的 ScriptDraft。为了保证项目可演示，即使没有
    API key 或某些阶段失败，流水线也会使用本地模板进行兜底。
    """

    def __init__(self, factory: AgentFactory | None = None, refiner: RLRefiner | None = None):
        self.factory = factory or AgentFactory()
        self.refiner = refiner or RLRefiner()

    def _parse_character_cards(self, request: ScriptRequest, payload: dict[str, Any]) -> list[CharacterCard]:
        """将模型返回的角色卡转换为内部 CharacterCard 对象。

        如果 Character Agent 没有返回有效结果，则使用用户输入的角色信息兜底。
        """
        cards = payload.get("character_cards") or request.characters
        return [
            CharacterCard(
                name=item.get("name", "未命名角色"),
                role=item.get("role", "待补充"),
                personality=item.get("personality", "复杂但稳定"),
                motivation=item.get("motivation", "推动剧情"),
                speaking_style=item.get("speaking_style", "克制自然"),
                relationship=item.get("relationship", "待定义"),
            )
            for item in cards
        ]

    def _fallback_outline(self, request: ScriptRequest) -> list[dict[str, Any]]:
        """在模型不可用时生成最小可用三幕式大纲。"""
        return [
            {
                "index": 1,
                "location": request.setting,
                "time_of_day": "夜晚",
                "mood": "悬念建立",
                "purpose": "引入核心问题",
                "conflict": "角色之间的秘密首次露出",
            },
            {
                "index": 2,
                "location": request.setting,
                "time_of_day": "深夜",
                "mood": "冲突升级",
                "purpose": "推进误解与对抗",
                "conflict": "角色目标发生正面碰撞",
            },
            {
                "index": 3,
                "location": request.setting,
                "time_of_day": "凌晨",
                "mood": "真相揭示",
                "purpose": "完成反转与收束",
                "conflict": "隐藏动机被揭开",
            },
        ]

    def _normalize_outline_item(self, request: ScriptRequest, item: Any, idx: int) -> SceneBeat:
        """兼容模型可能返回的不同大纲格式。

        模型有时返回对象数组，有时返回字符串数组。这里统一转换为 SceneBeat，
        便于后续评分和渲染。
        """
        if isinstance(item, str):
            return SceneBeat(
                index=idx + 1,
                location=request.setting,
                time_of_day="未指定",
                mood="推进剧情",
                purpose=item,
                conflict="由场景推进自然产生",
            )
        if not isinstance(item, dict):
            item = {}
        return SceneBeat(
            index=int(item.get("index", idx + 1)),
            location=item.get("location") or item.get("heading") or request.setting,
            time_of_day=item.get("time_of_day", "未指定"),
            mood=item.get("mood", "推进剧情"),
            purpose=item.get("purpose") or item.get("summary") or item.get("content") or "推进故事",
            conflict=item.get("conflict", "制造对抗"),
        )

    def _parse_outline(self, request: ScriptRequest, *payloads: dict[str, Any]) -> list[SceneBeat]:
        """按优先级选择大纲：Editor 输出 > Planner 输出 > 本地兜底。"""
        beats: list[Any] = []
        for payload in payloads:
            candidate = payload.get("outline") if isinstance(payload, dict) else None
            if candidate:
                beats = candidate
                break
        if not beats:
            beats = self._fallback_outline(request)
        return [self._normalize_outline_item(request, item, idx) for idx, item in enumerate(beats)]

    def _parse_scenes(
        self,
        outline: list[SceneBeat],
        character_cards: list[CharacterCard],
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """按优先级选择场景：Editor 输出 > Dialogue 输出 > 本地兜底。

        这里保留 heading/content/dialogue/beat 等字段，避免把 Editor 生成的
        剧本化内容压缩成只有对白的简单结构。
        """
        for payload in payloads:
            scenes_payload = payload.get("scenes") if isinstance(payload, dict) else None
            if not scenes_payload:
                continue
            scenes: list[dict[str, Any]] = []
            for idx, item in enumerate(scenes_payload):
                if isinstance(item, str):
                    scenes.append({"scene": idx + 1, "content": item, "dialogue": [], "beat": {}})
                    continue
                if not isinstance(item, dict):
                    continue
                scene_number = item.get("scene") or item.get("index") or idx + 1
                scene = {
                    "scene": int(scene_number),
                    "dialogue": item.get("dialogue", []),
                    "beat": item.get("beat", {}),
                }
                if item.get("heading") or item.get("title"):
                    scene["heading"] = item.get("heading") or item.get("title")
                if item.get("content") or item.get("description") or item.get("action"):
                    scene["content"] = item.get("content") or item.get("description") or item.get("action")
                scenes.append(scene)
            if scenes:
                return scenes

        # 当模型没有返回场景时，生成最小可用占位对白，保证程序仍可运行。
        return [
            {
                "scene": beat.index,
                "dialogue": [
                    {
                        "character": card.name,
                        "line": f"{card.name} 围绕{beat.mood}展开对白。",
                    }
                    for card in character_cards[: min(3, len(character_cards))]
                ],
                "beat": asdict(beat),
            }
            for beat in outline
        ]

    async def _safe_agent_json(self, agent_name: str, prompt: str) -> dict[str, Any]:
        """安全调用单个 Agent。

        模型服务可能出现超时、429 过载或 JSON 格式异常。这里按阶段捕获异常，
        防止某一步失败导致前面已经成功的输出全部丢失。
        """
        if not self.factory.has_model:
            return {}
        try:
            agent = getattr(self.factory, agent_name)()
            return await agent_json_reply(agent, prompt)
        except Exception as exc:  # noqa: BLE001
            print(f"[script-lab] {agent_name} agent failed, using best available fallback: {exc}")
            return {}

    async def run_async(self, request: ScriptRequest) -> ScriptDraft:
        """异步执行完整剧本生成流程。"""
        if not self.factory.has_model:
            print("[script-lab] No API key found; using local fallback template.")

        planner_output = await self._safe_agent_json("planner", build_planner_prompt(request))
        character_output = await self._safe_agent_json("character", build_character_prompt(request, planner_output))
        dialogue_output = await self._safe_agent_json(
            "dialogue",
            build_dialogue_prompt(request, planner_output, character_output),
        )
        editor_output = await self._safe_agent_json(
            "editor",
            build_editor_prompt(request, planner_output, character_output, dialogue_output),
        )

        character_cards = self._parse_character_cards(request, character_output)
        outline = self._parse_outline(request, editor_output, planner_output)
        scenes = self._parse_scenes(outline, character_cards, editor_output, dialogue_output)

        draft = ScriptDraft(
            title=editor_output.get("title") or planner_output.get("title") or request.title_hint or f"{request.genre}剧本",
            logline=editor_output.get("logline")
            or planner_output.get("logline")
            or f"围绕{request.setting}展开的一段{request.genre}故事，强调{', '.join(request.constraints) or '情节推进'}。",
            character_cards=character_cards,
            outline=outline,
            scenes=scenes,
            conclusion=editor_output.get("conclusion") or dialogue_output.get("conclusion") or "所有线索在结尾回收，人物关系得到重新定义。",
            quality_score=0.0,
            critic_notes=[],
        )

        script_payload = {
            "title": draft.title,
            "logline": draft.logline,
            "characters": [asdict(c) for c in draft.character_cards],
            "outline": [asdict(o) for o in draft.outline],
            "scenes": draft.scenes,
            "conclusion": draft.conclusion,
        }
        critic_output = await self._safe_agent_json("critic", build_critic_prompt(script_payload))
        if critic_output:
            if isinstance(critic_output.get("score"), (int, float)):
                draft.quality_score = round(float(critic_output["score"]), 3)
            draft.critic_notes = [str(note) for note in critic_output.get("notes", [])]
            draft.revision_history.append({"score": draft.quality_score, "notes": draft.critic_notes, "source": "critic"})
        else:
            draft = self.refiner.refine(draft)
        return draft

    def run(self, request: ScriptRequest) -> ScriptDraft:
        """同步运行入口。

        普通脚本可以直接调用该方法；如果当前已经处于事件循环中，需改用
        `await run_async(request)`。
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run_async(request))
        raise RuntimeError("ScriptPipeline.run() cannot be called inside an active event loop; use await run_async().")

    def render(self, draft: ScriptDraft) -> str:
        """将 ScriptDraft 渲染为中文友好的 JSON 字符串。"""
        payload = {
            "title": draft.title,
            "logline": draft.logline,
            "characters": [asdict(c) for c in draft.character_cards],
            "outline": [asdict(o) for o in draft.outline],
            "scenes": draft.scenes,
            "conclusion": draft.conclusion,
            "quality_score": draft.quality_score,
            "critic_notes": draft.critic_notes,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
