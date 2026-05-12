from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import ScriptDraft


class ScriptCritic:
    """本地轻量评分器。

    当 Critic Agent 不可用时，用简单规则评估剧本结构完整度。
    这不是严格意义上的强化学习模型，而是一个可替换的本地反馈组件。
    """

    def score(self, draft: ScriptDraft) -> dict[str, Any]:
        structure = min(1.0, len(draft.outline) / 5)
        consistency = 1.0 if draft.character_cards else 0.4
        coherence = 0.8 if draft.scenes else 0.3
        controllability = 0.7 if draft.logline else 0.3
        score = round((structure + consistency + coherence + controllability) / 4, 3)

        notes = []
        if len(draft.outline) < 3:
            notes.append("大纲分幕偏少，建议增加推进层次。")
        if not draft.character_cards:
            notes.append("角色卡缺失。")
        if not draft.scenes:
            notes.append("场景对白缺失。")
        return {"score": score, "notes": notes}


class RLRefiner:
    """轻量反馈循环。

    当前版本只记录评分和修订历史，后续可以替换为真正的多版本采样、
    偏好排序或 RLAIF/RLHF 风格优化流程。
    """

    def __init__(self, critic: ScriptCritic | None = None):
        self.critic = critic or ScriptCritic()

    def refine(self, draft: ScriptDraft) -> ScriptDraft:
        result = self.critic.score(draft)
        draft.quality_score = result["score"]
        draft.critic_notes = result["notes"]
        draft.revision_history.append({"score": result["score"], "notes": result["notes"], "snapshot": asdict(draft)})
        return draft
