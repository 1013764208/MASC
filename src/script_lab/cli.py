from __future__ import annotations

import argparse
import asyncio

from .graph import ScriptPipeline
from .models import ScriptRequest


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(description="AgentScope multi-agent script generation demo")
    parser.add_argument("--genre", required=True, help="剧本类型，例如：悬疑、科幻、爱情")
    parser.add_argument("--title-hint", default="", help="可选标题提示")
    parser.add_argument("--characters", required=True, help="格式: 姓名:描述;姓名:描述")
    parser.add_argument("--setting", required=True, help="故事发生的主要场景")
    parser.add_argument("--constraints", default="", help="逗号分隔的生成约束，例如：反转结局, 800字左右")
    parser.add_argument("--length-hint", default="中短篇", help="长度提示")
    parser.add_argument("--style-hint", default="自然、电影感", help="风格提示")
    return parser


def parse_characters(raw: str) -> list[dict[str, str]]:
    """解析命令行中的角色字符串。

    输入示例："林然:冷静的记者;苏晚:神秘的法医"
    输出示例：[{"name": "林然", "role": "冷静的记者"}, ...]
    """
    chars: list[dict[str, str]] = []
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        name, _, desc = item.partition(":")
        chars.append({"name": name.strip(), "role": desc.strip() or "待定义"})
    return chars


async def main_async() -> None:
    """异步 CLI 主逻辑。"""
    parser = build_parser()
    args = parser.parse_args()
    request = ScriptRequest(
        genre=args.genre,
        title_hint=args.title_hint,
        characters=parse_characters(args.characters),
        setting=args.setting,
        constraints=[c.strip() for c in args.constraints.split(",") if c.strip()],
        length_hint=args.length_hint,
        style_hint=args.style_hint,
    )
    pipeline = ScriptPipeline()
    draft = await pipeline.run_async(request)
    print(pipeline.render(draft))


def main() -> None:
    """同步命令行入口。

    pyproject.toml 中的 script-lab 会调用这个函数，因此这里不能定义为 async。
    """
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
