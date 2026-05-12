# Multi-Agent Scripting & Collaboration; AgentScope 多智能体剧本生成系统

本项目是一个基于 `AgentScope` 的多智能体剧本生成实验系统。系统面向“可控剧本生成”任务，将一次完整的剧本创作拆分为多个专业 Agent 协作完成，包括剧情规划、角色设计、对白生成、编辑润色和质量评估。

相比直接让一个大模型一次性输出完整剧本，本项目采用分阶段、多角色、结构化输出的方式，提高生成过程的可控性、可解释性和可扩展性。

---

## 1. 当前任务需求定义

### 1.1 任务目标

当前任务是构建一个能够根据用户输入自动生成剧本的多智能体系统。用户只需要提供基础创作约束，例如：

- 剧本类型：如悬疑、科幻、爱情、犯罪等
- 角色设定：如角色姓名、身份、性格关键词
- 场景设定：如雨夜、废弃医院、未来城市等
- 生成约束：如反转结局、800 字左右、台词克制、电影感等

系统需要自动生成：

- 剧本标题
- 一句话梗概
- 角色卡
- 分场大纲
- 分场对白
- 最终润色版剧本文本
- 质量评分与修改建议

### 1.2 示例输入

```bash
script-lab --genre 悬疑 \
  --characters "林然:冷静的记者;苏晚:神秘的法医" \
  --setting "雨夜, 废弃医院" \
  --constraints "反转结局, 800字左右, 台词克制"
```

### 1.3 期望输出

系统最终应输出结构化 JSON，例如：

```json
{
  "title": "雨夜无声",
  "logline": "记者林然雨夜深入废弃医院调查旧案，偶遇神秘法医苏晚，随着线索深入，两人逐渐发现彼此与这栋建筑之间超越生死的隐秘联系。",
  "characters": [],
  "outline": [],
  "scenes": [],
  "conclusion": "...",
  "quality_score": 8.5,
  "critic_notes": []
}
```

### 1.4 关键约束

本任务不仅要求“能生成文本”，还强调以下几点：

1. **可控性**：生成内容必须遵循用户输入的类型、角色、场景和约束。
2. **结构化**：每个阶段尽量输出 JSON，方便后续解析、编辑和评估。
3. **多智能体协作**：不同 Agent 负责不同创作环节，而不是单模型一次性完成。
4. **容错能力**：当某个 Agent 调用失败时，系统应尽可能保留前面已经成功生成的结果。
5. **可解释性**：能够观察到每个 Agent 的中间输出，便于调试和优化。

---

## 2. 方案设计

### 2.1 总体思路

系统采用“流水线式多 Agent 协作”架构。每个 Agent 只负责一个相对明确的子任务，后一个 Agent 基于前一个 Agent 的输出继续创作。

整体流程如下：

```text
用户输入
  -> Planner Agent：生成标题、梗概、分场大纲
  -> Character Agent：生成角色卡与人物关系
  -> Dialogue Agent：生成分场对白
  -> Editor Agent：统一润色、修复矛盾、形成最终剧本
  -> Critic Agent：评分并给出修改建议
  -> 最终结构化输出
```

### 2.2 Agent 职责划分

#### 2.2.1 Planner Agent

Planner Agent 负责剧本的宏观结构设计。

输入：

- 用户原始需求
- 类型、角色、场景、约束

输出：

- `title`：标题
- `logline`：一句话梗概
- `outline`：分场大纲

示例职责：

- 确定故事开端、冲突、升级、高潮、收束
- 设计反转结局
- 控制整体风格与节奏
- 保证故事符合用户约束

#### 2.2.2 Character Agent

Character Agent 负责人物设计。

输入：

- 用户角色设定
- Planner 生成的大纲

输出：

- `character_cards`：角色卡列表

每个角色卡包含：

- 姓名
- 身份
- 性格
- 动机
- 说话方式
- 人物关系

该 Agent 的作用是解决剧本生成中常见的“人物扁平”和“角色串台”问题。

#### 2.2.3 Dialogue Agent

Dialogue Agent 负责根据大纲和角色卡生成具体对白。

输入：

- 用户需求
- 分场大纲
- 角色卡

输出：

- `scenes`：分场内容
- `conclusion`：结局说明

该 Agent 需要做到：

- 不同角色有不同说话方式
- 对白符合“台词克制”等约束
- 对白服务于剧情推进
- 场景之间有连续性

#### 2.2.4 Editor Agent

Editor Agent 负责对前面结果进行统一编辑。

输入：

- Planner 输出
- Character 输出
- Dialogue 输出

输出：

- 最终标题
- 最终梗概
- 最终大纲
- 最终场景内容
- 最终结局

Editor Agent 是最终成稿阶段，负责：

- 修复逻辑矛盾
- 去除重复内容
- 增强戏剧性
- 统一格式
- 强化用户约束

在最终组装时，系统优先采用 `Editor Agent` 的输出，其次才使用 `Dialogue Agent` 或 `Planner Agent` 的输出。

#### 2.2.5 Critic Agent

Critic Agent 负责质量评估。

输入：

- 最终剧本结构化内容

输出：

- `score`：评分
- `notes`：修改建议

评估维度包括：

- 结构完整性
- 人物深度
- 叙事连贯性
- 约束遵循程度

---

## 3. 技术选型

### 3.1 Python

项目使用 Python 实现，原因包括：

- 生态适合 AI Agent 和 LLM 应用开发
- 数据结构、JSON 解析、异步调用实现简单
- 与 AgentScope、OpenAI SDK 等工具兼容性好

### 3.2 AgentScope

本项目使用 `AgentScope` 作为多智能体框架。

选择 AgentScope 的原因：

- 支持 Agent 抽象
- 支持多 Agent 协作
- 支持模型、消息、格式化器等组件化封装
- 适合构建复杂 Agent pipeline

在本项目中，AgentScope 主要用于：

- 构建 `ReActAgent`
- 管理 Agent 的系统提示词
- 调用底层 LLM
- 统一消息格式

### 3.3 OpenAI-Compatible API

系统通过 `OpenAIChatModel` 调用兼容 OpenAI 接口的大语言模型。

当前支持通过环境变量配置：

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="your_base_url"
export AGENTSCOPE_MODEL_NAME="kimi-k2.5"
```

如果使用 Kimi / Moonshot 等兼容接口，通常需要额外配置：

```bash
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
```

### 3.4 异步调用

AgentScope 的 `ReActAgent.reply()` 是异步协程，因此系统使用 `asyncio` 管理执行流程。

CLI 入口采用同步包装异步逻辑的方式：

```text
main()
  -> asyncio.run(main_async())
  -> await pipeline.run_async(request)
```

这样既能在命令行中直接运行，也能在异步环境中复用 `run_async()`。

### 3.5 JSON 结构化输出

各 Agent 均被要求输出 JSON。这样做的原因是：

- 方便程序解析
- 方便后续 Agent 消费上一步结果
- 方便最终统一渲染
- 方便调试和评估

系统还实现了 JSON 提取逻辑，用于处理模型输出中包含 Markdown 代码块或 AgentScope block 的情况。

---

## 4. 具体技术解释

### 4.1 项目结构

```text
src/script_lab/
  __init__.py
  agents.py
  cli.py
  config.py
  graph.py
  models.py
  rl.py
```

各文件职责如下：

#### `config.py`

负责运行时配置和系统提示词。

主要内容包括：

- 模型名称
- API Key
- Base URL
- 请求超时时间
- 最大重试次数
- 不同 Agent 的系统提示词

支持环境变量：

```bash
AGENTSCOPE_MODEL_NAME
OPENAI_API_KEY
KIMI_API_KEY
OPENAI_BASE_URL
KIMI_BASE_URL
SCRIPT_LAB_TIMEOUT
SCRIPT_LAB_MAX_RETRIES
```

#### `models.py`

定义结构化数据模型。

包括：

- `CharacterCard`
- `SceneBeat`
- `ScriptRequest`
- `ScriptDraft`

这些 dataclass 用于统一系统内部数据结构，避免不同 Agent 输出格式不一致导致程序混乱。

#### `agents.py`

负责 Agent 构建、Prompt 构造和模型输出解析。

主要功能：

- 创建 `Planner / Character / Dialogue / Editor / Critic` Agent
- 构造每个 Agent 的任务 prompt
- 调用 Agent 并解析 JSON
- 从 AgentScope 返回的 `thinking` / `text` block 中提取有效文本

重点逻辑包括：

1. **AgentFactory**

用于统一创建 Agent。

1. **Prompt Builder**

例如：

- `build_planner_prompt()`
- `build_character_prompt()`
- `build_dialogue_prompt()`
- `build_editor_prompt()`
- `build_critic_prompt()`

每个 builder 都会明确要求模型输出 JSON schema。

1. **JSON 提取逻辑**

模型有时会输出：

```text
```json
{
  "title": "雨夜无声"
}
```

```

或者 AgentScope 返回：

```text
thinking block + text block
```

因此系统实现了：

- 忽略 `thinking` block
- 提取 `text` block
- 识别 Markdown fenced JSON
- 尝试从文本中截取 JSON 对象

#### `graph.py`

负责主流程编排，是系统核心。

主要职责：

- 调用各个 Agent
- 保存各阶段输出
- 解析角色卡、大纲、场景
- 按优先级组装最终结果
- 调用 Critic 评分
- 在失败时进行 fallback

最终结果组装优先级如下：

```text
标题 / 梗概：Editor > Planner > 用户输入 / fallback
角色卡：Character > 用户输入 / fallback
大纲：Editor > Planner > fallback
场景：Editor > Dialogue > fallback
结局：Editor > Dialogue > fallback
评分：Critic > 本地评分器
```

#### `rl.py`

实现轻量本地评分器。

它不是完整强化学习训练，而是一个 RL-style feedback loop 的雏形，用于：

- 给草稿评分
- 记录 revision history
- 在 Critic Agent 不可用时提供本地兜底评分

#### `cli.py`

负责命令行入口。

支持参数：

```bash
--genre
--title-hint
--characters
--setting
--constraints
--length-hint
--style-hint
```

---

## 5. 使用方法

### 5.1 安装

```bash
pip install -e .
```

### 5.2 配置模型 API

如果使用 OpenAI-compatible API：

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="your_base_url"
export AGENTSCOPE_MODEL_NAME="kimi-k2.5"
```

可选配置：

```bash
export SCRIPT_LAB_TIMEOUT=180
export SCRIPT_LAB_MAX_RETRIES=3
```

### 5.3 运行示例

```bash
script-lab --genre 悬疑 \
  --characters "林然:冷静的记者;苏晚:神秘的法医" \
  --setting "雨夜, 废弃医院" \
  --constraints "反转结局, 800字左右, 台词克制"
```

---

## 6. 开发过程中遇到的问题与解决方案

### 6.1 问题一：Agent 被调用但结果没有进入最终输出

#### 现象

最初系统虽然调用了 Agent，但最终输出仍然是模板内容，例如：

```text
林然 围绕悬念建立展开对白。
```

#### 原因

代码中调用了 Agent：

```text
planner.reply(...)
character.reply(...)
```

但没有读取 Agent 返回值，也没有将其解析后接入最终 `ScriptDraft`。

#### 解决方案

增加了：

- `agent_json_reply()`
- 各阶段输出变量：`planner_output`、`character_output`、`dialogue_output`、`editor_output`
- 最终组装逻辑

现在模型生成结果会真正进入最终输出。

---

### 6.2 问题二：`coroutine was never awaited`

#### 现象

运行 CLI 时出现：

```text
RuntimeWarning: coroutine 'ReActAgent.reply' was never awaited
```

#### 原因

AgentScope 的 `ReActAgent.reply()` 是异步协程，不能直接同步调用。

#### 解决方案

将流水线改为异步：

```text
run_async()
```

CLI 入口改成：

```text
main() -> asyncio.run(main_async())
```

从而保证所有 Agent 调用都通过 `await` 执行。

---

### 6.3 问题三：CLI 入口直接返回 coroutine 对象

#### 现象

运行 `script-lab` 时输出：

```text
<coroutine object main at ...>
RuntimeWarning: coroutine 'main' was never awaited
```

#### 原因

`pyproject.toml` 中入口为：

```toml
script-lab = "script_lab.cli:main"
```

但 `main()` 被定义成了 `async def main()`。

命令行入口调用它时不会自动执行事件循环。

#### 解决方案

拆分为：

```text
main_async()：异步主逻辑
main()：同步包装器，内部 asyncio.run(main_async())
```

---

### 6.4 问题四：模型输出 JSON 解析失败

#### 现象

模型明明输出了 JSON，但程序仍然 fallback。

#### 原因

AgentScope 返回内容可能包含：

- `thinking` block
- `text` block
- Markdown fenced JSON

例如：

```text
planner(thinking): ...
planner: ```json
{
  "title": "雨夜证词"
}
```

```

旧代码直接把整个返回对象转成字符串，导致 JSON 解析失败。

#### 解决方案

新增文本提取和 JSON 解析逻辑：

- 忽略 `thinking` block
- 提取 `text` block
- 识别 ```json 代码块
- 从文本中提取 JSON 对象

---

### 6.5 问题五：最终输出仍然使用 fallback 模板

#### 现象

中间 Agent 输出正常，例如 `editor` 已生成 `积水证言`，但最终 JSON 仍然显示：

```text
"title": "悬疑剧本"
```

#### 原因

最终组装优先级错误，且格式兼容不足。

旧逻辑对 `outline` 和 `scenes` 的格式要求过窄，而模型输出可能是：

```json
"outline": [
  "雨夜废弃医院，林然与苏晚在积水的走廊中搜寻线索..."
]
```

而不是对象数组。

#### 解决方案

改进解析兼容：

- `outline` 支持字符串数组和对象数组
- `scenes` 支持 `heading`、`content`、`dialogue`、`description`、`action`
- 最终优先使用 `Editor Agent` 的结果

---

### 6.6 问题六：模型服务过载，返回 429

#### 现象

运行时出现：

```text
Error code: 429
engine_overloaded_error
The engine is currently overloaded, please try again later
```

#### 原因

一次完整生成包含多个 LLM 请求：

```text
Planner -> Character -> Dialogue -> Editor -> Critic
```

即一次 CLI 命令可能调用 5 次模型。如果模型服务繁忙、账号限流或 prompt 较长，就可能触发 429。

#### 解决方案

已做优化：

1. 增加超时时间配置：

```bash
export SCRIPT_LAB_TIMEOUT=180
```

1. 增加最大重试次数配置：

```bash
export SCRIPT_LAB_MAX_RETRIES=3
```

1. 增加 fallback 机制。
2. 将整体失败改进为分阶段容错：

```text
Planner 失败，只 fallback 大纲
Character 失败，只 fallback 角色卡
Dialogue 失败，只 fallback 对白
Editor 失败，只 fallback 润色
Critic 失败，只使用本地评分器
```

这样可以避免某一步失败导致前面已经成功生成的结果全部丢失。

---

## 7. 当前系统能力与限制

### 7.1 当前能力

目前系统已经具备：

- 命令行输入剧本需求
- 多 Agent 串行协作
- 模型驱动的结构化生成
- JSON 解析与最终组装
- Agent 调用失败时的 fallback
- 基础质量评分

### 7.2 当前限制

当前系统仍有一些限制：

1. **依赖外部模型服务稳定性**
  - 如果 API 超时或 429，生成质量会下降。
2. **多 Agent 串行调用耗时较长**
  - 一次完整生成可能需要较长时间。
3. **Critic 还不是严格的 RLHF / RLAIF**
  - 当前只是评分与建议，还没有真正训练策略模型。
4. **JSON 输出依赖模型遵循指令**
  - 虽然已有解析兜底，但模型仍可能输出不完整 JSON。
5. **没有持久化中间结果**
  - 当前终端能看到中间过程，但没有自动保存每个 Agent 的输出文件。

---

## 8. 未来改进方向

### 8.1 增加 Debug 模式

增加参数：

```bash
--debug
```

开启后将每个 Agent 的输出保存到：

```text
output/planner.json
output/character.json
output/dialogue.json
output/editor.json
output/critic.json
```

这样可以方便定位是哪一步失败或生成质量不足。

### 8.2 增加断点续跑

如果 `planner` 和 `character` 已经成功，但 `dialogue` 因 429 失败，下次运行可以从 `dialogue` 继续，而不必重新调用前面的 Agent。

### 8.3 增加重试退避策略

针对 429 和 timeout，可实现指数退避：

```text
第 1 次失败：等待 5 秒
第 2 次失败：等待 15 秒
第 3 次失败：等待 30 秒
```

降低模型服务过载时的失败率。

### 8.4 增加生成模式

可增加不同模式：

```bash
--mode fast
--mode balanced
--mode full
```

含义：

- `fast`：只调用一个 Agent，快速生成
- `balanced`：调用 Planner + Dialogue + Editor
- `full`：调用全部 Agent，包括 Critic

### 8.5 引入 Agentic RL 反馈闭环

当前 `rl.py` 只是轻量评分器，后续可以逐步演化为真正的 `agentic RL` 系统。建议按下面四个阶段推进：

#### Phase 1：先把 Critic 做强

目标是把当前“单一总分”升级为更稳定、更可解释的评审器。

可做改进包括：

- 多维评分，而不是只给一个总分
- 输出结构化问题清单
- 输出可执行的修改建议
- 支持题材感知评分，例如悬疑、爱情、科幻、犯罪使用不同标准
- 支持场景级、角色级、对白级评审
- 支持 pairwise preference，比较两个版本哪个更好

这一阶段的核心作用是为后续训练提供高质量反馈信号。

#### Phase 2：构建 Reward Model

当 Critic 能稳定产出偏好和评分后，可以把这些数据沉淀为训练样本，训练一个 reward model。

reward model 的作用是：

- 学习 Critic / 人类的偏好
- 为后续优化提供更稳定的 reward 来源
- 降低每次都依赖大模型在线评审的成本

建议收集的数据包括：

- `prompt`
- `candidate_a`
- `candidate_b`
- `critic_preference`
- `human_preference`（如有）
- `final_accepted_output`
- `revision_history`

#### Phase 3：用 GRPO 优化生成策略

有了稳定 reward 之后，再用 GRPO 去优化生成侧的 policy。

推荐优先优化的对象是：

- `Editor Agent`
- 或一个统一的 `Writer / Orchestrator Agent`

GRPO 的优势在于：

- 适合“同一输入下生成多个候选，再做相对比较”的任务
- 不一定依赖显式价值函数
- 更适合文本生成这种高方差任务
- 可以直接利用 group-relative 的相对优势进行更新

#### Phase 4：扩展到完整的 Agentic RL

当单个生成 agent 已经收敛后，可以进一步把整个 pipeline 纳入优化范围：

- Planner 决定大纲结构
- Character 决定人物设定
- Dialogue 决定对白策略
- Editor 决定重写与整合方式
- Critic 继续作为评估器和 reward 来源

这一阶段的目标不是只优化“文本”，而是优化“整个创作决策过程”。

### 为什么优先选择 GRPO，而不是 PPO 或 DPO

#### 1. 相比 PPO，GRPO 更适合文本候选组比较

PPO 通常更依赖 value model / advantage estimation，训练链路更复杂，对文本生成任务来说，稳定 reward 和价值估计都比较难。

GRPO 更适合以下场景：

- 一次采样多个候选
- 按组内相对优势更新
- 直接利用 reward model 或 Critic 的排序结果

对于剧本生成这种“多版本比较”天然存在的任务，GRPO 的工程匹配度更高。

#### 2. 相比 DPO，GRPO 更适合真正的在线优化

DPO 更偏向利用离线偏好数据做直接优化，优点是简单稳定，但它更像“静态偏好学习”。

而 `agentic RL` 更强调：

- 多轮生成
- 多轮评审
- 多轮重写
- 多阶段决策

GRPO 更容易嵌入这种在线闭环，因为它可以直接利用当前策略采样出来的多个候选进行更新。

#### 3. GRPO 更适合做逐步扩展

对于本项目来说，可以先从：

- Critic 评分
- Reward Model
- GRPO 优化 Editor

开始，后面再扩展到更多 agent。这样路径清晰、风险较低，也更利于调试。

### 推荐的落地顺序

1. 先增强 Critic 的多维评分和偏好输出
2. 再积累偏好数据并训练 Reward Model
3. 再用 GRPO 优化生成侧策略
4. 最后把整个多 Agent 流水线纳入 agentic RL 闭环

### 8.6 增加 Web UI

未来可以开发一个 Web 界面，支持：

- 表单输入剧本需求
- 实时显示各 Agent 生成过程
- 可视化编辑角色卡和大纲
- 一键重新生成某一场
- 导出 Markdown / PDF / Final Draft 格式

### 8.7 增加剧本格式导出

目前输出 JSON，未来可增加：

- Markdown 剧本文档
- 标准影视剧本格式
- 分镜脚本格式
- 小说化文本格式

### 8.8 加强内容一致性检查

未来可以增加专门的 Consistency Agent，检查：

- 人物动机是否前后一致
- 场景时间是否冲突
- 伏笔是否回收
- 反转是否合理
- 对白是否符合人物设定

---

## 9. 总结

本项目完成了一个基于 AgentScope 的多智能体剧本生成系统原型。系统将复杂创作任务拆解为多个专业 Agent 的协作流程，通过结构化 JSON 输出实现可解析、可组合、可评估的剧本生成。

在开发过程中，我们解决了异步调用、CLI 协程入口、AgentScope block 解析、模型输出接入、fallback 优先级、API 超时和 429 过载等问题，使系统从最初的模板输出逐步演进为真正可调用 LLM 的多 Agent 创作流水线。

当前系统已经可以运行并生成结构化剧本结果，后续可继续向 Debug 持久化、断点续跑、Web UI、强化学习反馈和专业剧本格式导出方向扩展。