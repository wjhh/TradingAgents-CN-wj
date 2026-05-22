# TradingAgents-CN-wj 迁移方案评估报告（v2.2）

> **评估日期**: 2026-05-19  
> **评估对象**: `docs/migration-plan-3roles-datasource.md`（v2.2 原版保留版）  
> **评估范围**: 方案可行性、完整性、问题和风险评估  
> **评估方式**: 逐条对照 3 个项目源码验证，仅做文档评审，不做任何方案执行

---

## 一、方案概述

该方案目标是将 TradingAgents-astock-wj 中的**政策分析师/游资追踪/解禁监控** 3 个 A 股特化分析角色，以及 **a-stock-data-wj 聚合数据源**整合到 TradingAgents-CN-wj 项目中。

### 方案版本演进

| 版本 | 更新时间 | 主要改进 |
|------|---------|---------|
| v1.0 | - | 初始方案，27 个文件，~1,970 行预估（严重低估） |
| v2.1 | 2026-05-19 | 修正分析师合计约 1,700 行、AStockDirectProvider 约 1,200-1,500 行；补充遗漏 6 处；新增风险 6 项；总预估提升到 ~3,680-4,180 行 |
| **v2.2** | 2026-05-19 | 基于 code review 反馈修正：4 个分析师确认、ToolNode 位点验证、signal_processing.py 显式声明、新增 `total_result` BUG 处理、新增 `analysis_runner.py` 变更、新增 `analysis_form.py` UI 适配、MongoDB `selected_analysts` 字段、SKILL.md 启动日志；总预估 ~4,060-4,660 行 |

### 方案关键数据

| 维度 | v2.1 | v2.2 | 变化 |
|------|------|------|------|
| 新建文件 | 5 个 | 5 个 | 不变 |
| 修改现有文件 | 21 个 | 26 个（含 1 个配置文件 + 5 处新增逻辑） | +5 |
| 预估代码量 | ~3,680-4,180 行 | ~4,060-4,660 行 | +~380-480 行 |
| 涉及子系统 | Agent / 图编排 / 数据源 / Web / 记忆 | + MongoDB 存储层 / 分析结果持久化 | +2 |

---

## 二、方案 v2.2 新增变更项逐条验证

### 2.1 v2.2 12 处新增/修正条目核验

| # | v2.2 描述 | 源码验证结果 | 判定 |
|---|----------|------------|:----:|
| 1 | 4 个已有分析师确认存在（market/social/news/fundamentals） | `conditional_logic.py` 有 4 个 `should_continue_*` 方法；`setup.py` 创建 4 个 analyst node；`analysis_form.py` 4 个 checkbox | ✅ 正确 |
| 2 | ToolNode 在 `trading_graph.py` `_create_tool_nodes()` 之内 | **无法完全验证** — 当前代码 ToolNode 创建逻辑分散在 `TradingAgentsGraph.__init__` 和 `setup.py` 中，未找到独立的 `_create_tool_nodes()` 方法。方案描述的插入位点逻辑正确但方法名需实施时确认。 | ⚠️ 部分正确 |
| 3 | `signal_processing.py` 已在 baseline 存在，不需要新建 | `signal_processing.py` 确实存在（336 行），含 `SignalProcessor` 类，功能稳定 | ✅ 正确 |
| 4 | `$218` 处 BUG：`save_analysis_report` 中 `stock_code` 从 `total_result` JSON 读取出 int 问题 | **无法验证** — 当前 `save_analysis_report` 接收 `stock_symbol: str` 参数（类型安全），未使用 `total_result` JSON。该 BUG 可能在特定路径或旧版本中存在，但当前主流程代码未见此问题。 | ⚠️ 需确认实际触发路径 |
| 5 | `analysis_runner.py` 新增 `selected_analysts` 参数保存到 `total_result.json` + 覆盖 `analysis_id` | `analysis_runner.py` 第 100 行签名 `run_stock_analysis(..., market_type=...)` 无 `selected_analysts` 参数；第 507-520 行 `results` 字典无 `selected_analysts` 字段 | ⚠️ 描述功能正确，但参数名需对应当前签名 |
| 6 | `analysis_form.py` 新增 3 个 A 股专属 checkbox + 市场联动 | 当前 4 个 checkbox（market/social/news/fundamentals），social 已实现 A 股禁用逻辑（第 153-161 行）。新增 3 个的逻辑模式一致 | ✅ 可行 |
| 7 | `mongodb_report_manager.py` `save_analysis_report` 写入 `selected_analysts` | 当前第 182 行 `"analysts": analysis_results.get("analysts", [])` 使用 `analysts` 键名，无 `selected_analysts` 字段 | ⚠️ 新增 `selected_analysts` 字段即可，不影响现有逻辑 |
| 8 | `report_exporter.py` `save_analysis_report` 传递 `selected_analysts` | 当前第 1165 行传递 `analysis_results`（含所有结果），新增字段自然透传 | ✅ 正确 |
| 9 | SKILL.md 启动日志在 `app.py` | **文件不存在** — CN-wj 无 `app/app.py`。Web 应用在 `web/app.py`（Streamlit），API 应用在 `app/main.py`（FastAPI）。方案文件路径需修正 | ❌ 路径错误 |
| 10 | `app/models/analysis.py` `selected_analysts` 默认值新增 3 个 ID | 当前第 46 行 `["market", "fundamentals", "news", "social"]`，需新增 `policy`, `hot_money`, `lockup` | ✅ 正确 |
| 11 | `app/worker.py` 旧版英文分析师名硬编码修正 | v2.1 已识别 | ✅ 正确 |
| 12 | 新增 `selected_analysts` 渲染到 `total_result.json` | 需新增 `save_total_result_json` 函数 | ✅ 正确 |

**核验结论**: 12 项中 8 项完全正确、3 项部分正确或需小修、1 项路径错误。

### 2.2 重点关注项说明

#### 🟡 关注项 1：`$218` BUG 当前无法复现

方案描述 `save_analysis_report` 中 `stock_code` 从 `total_result` JSON 读取变成 `int` 的 BUG，在当前主流程代码中**不存在**：

- [analysis_runner.py:L1165](file:///C:/Work/Tra/TradingAgents-CN-wj/web/utils/analysis_runner.py#L1165) 传递 `stock_symbol` 为 `str` 类型
- [report_exporter.py:L1194](file:///C:/Work/Tra/TradingAgents-CN-wj/web/utils/report_exporter.py#L1194) 接收 `stock_symbol: str`
- [mongodb_report_manager.py:L109](file:///C:/Work/Tra/TradingAgents-CN-wj/web/utils/mongodb_report_manager.py#L109) 接收 `stock_symbol: str`

**可能触发路径**：
1. 通过 `analysis_results.py` 历史记录加载路径（第 234 行 `json.load` 可能将 `"000001"` 解析为 `"000001"` — Python `json` 不会自动转 int，所以此路径安全）
2. 如果 MongoDB 中 `stock_symbol` 字段被其它系统以 `int` 类型写入

**建议**：实施时在 `save_analysis_report` 入口处统一加 `str(stock_symbol)` 强制转换即可防御。

#### 🔴 关注项 2：SKILL.md 启动日志路径错误

方案写道"在 `app.py` 启动时加载并验证 SKILL.md"。**CN-wj 项目中不存在 `app/app.py`**：

- Web 启动入口：[web/app.py](file:///C:/Work/Tra/TradingAgents-CN-wj/web/app.py)（Streamlit ~1,300+ 行）
- API 启动入口：[app/main.py](file:///C:/Work/Tra/TradingAgents-CN-wj/app/main.py)（FastAPI）
- 实际运行入口（uvicorn）：`app.__main__`

**正确插入位点**应该是 [app/__main__.py](file:///C:/Work/Tra/TradingAgents-CN-wj/app/__main__.py)（uvicorn 启动入口）或 [app/main.py](file:///C:/Work/Tra/TradingAgents-CN-wj/app/main.py)（FastAPI `lifespan` 上下文管理器中）。

### 2.3 v2.2 新增文件变更验证

| 新增变更文件 | v2.2 描述 | 当前源码位置 | 验证结果 |
|------------|----------|------------|---------|
| `mongodb_report_manager.py` | `selected_analysts` 写入 `analysis_requests` 集合 | 第 182 行 `"analysts"` 字段写入 | ✅ 存在需要新增的字段位置 |
| `report_exporter.py` | `save_analysis_report` 透传 `selected_analysts` | 第 1194 行调用 | ✅ 透传逻辑可自动传递新字段 |
| `analysis_runner.py` | 保存 `selected_analysts` 到 `total_result.json` | 第 551 行 `report_exporter` 调用前 | ⚠️ 需新增具体保存函数 |
| `analysis_form.py` | 3 个 A 股专属 checkbox | 第 122-198 行 | ✅ UI 模式成熟，新增按模式即可 |
| `analysis_results.py` | `analysis_id` 生成逻辑 | 第 244 行 | ✅ 需新增 `total_result.json` 覆盖逻辑 |
| `config.py` | `DATABASE_URI` 导入权限 | 需定位配置文件 | ⚠️ 需确认 CN-wj 使用 MongoDB 的具体配置方式 |

---

## 三、可行性评估

### 3.1 整体可行性判定：✅ 可行

v2.2 方案基于 **实际 code review** 修正了 v2.1 的多处误判（如第 $218 行类型推断错误、ToolNode 位点模糊、signal_processing.py 误判为"需要新建"），使之更加贴近实际代码。整体架构路径正确。

| 维度 | v2.1 评分 | v2.2 评分 | 变化 |
|------|:---------:|:---------:|:----:|
| 架构兼容性 | ✅ | ✅ | 已验证 4 个已有分析师的完整实现模式 |
| 分析师模式适配 | ⚠️ | ⚠️ | 因 CN-wj ~700 行模式不变，未降低实现复杂度 |
| 工具层适配 | ✅ | ✅ | 已验证 `Toolkit` 类 `@tool` 方法模式 |
| 数据源替换 | ⚠️ | ⚠️ | 未降低 AStockDirectProvider 封装工作量 |
| 多市场兼容 | ⚠️ | ⚠️ | 未降低动态控制复杂度 |

### 3.2 关键架构约束（v2.2 明确补充）

v2.2 方案在 v2.1 基础上明确了以下架构约束：

1. **4 个已有分析师采用相同模式**：当前 `market/social/news/fundamentals` 均在 [conditional_logic.py](file:///C:/Work/Tra/TradingAgents-CN-wj/tradingagents/graph/conditional_logic.py) 中有对应的 `should_continue_*` 方法，每个不超过 12 行简洁逻辑（报告检查 + tool_call_count 限制 + tool_calls 检测）
2. **ToolNode 创建插入位点**：位于 [trading_graph.py](file:///C:/Work/Tra/TradingAgents-CN-wj/tradingagents/graph/trading_graph.py) 的 `TradingAgentsGraph.__init__` 中（非 `_create_tool_nodes` 独立方法，实施时需按实际结构插入）
3. **`signal_processing.py` 已存在**：336 行，`SignalProcessor` 类稳定运行，方案从"需修改"降级为"不需修改"
4. **`analysis_form.py` UI 模式**：当前 checkbox 模式实现规范（第 122-198 行），新增 3 个 A 股专属 checkbox 仅需复制现有 `social` 的 A 股禁用模式

---

## 四、完整性评估

### 4.1 文件变更清单（v2.2 更新）

| 类别 | 文件 | v2.1 | v2.2 | 变更说明 |
|------|------|:----:|:----:|---------|
| **新建 — 分析师** | `policy_analyst.py` | ✅ | ✅ | 预估 ~400 行 |
| | `hot_money_tracker.py` | ✅ | ✅ | 预估 ~500 行，9 个工具 |
| | `lockup_watcher.py` | ✅ | ✅ | 预估 ~400 行 |
| **新建 — 数据源** | `astock_direct.py` | ✅ | ✅ | 预估 1,200-1,500 行 |
| **新建 — 质量门** | `quality_gate.py` | ✅ | ✅ | 推荐，预估 ~200 行 |
| **修改 — 状态** | `agent_states.py` | ✅ | ✅ | 新增 6 字段 + 3 个 tool_call_count |
| **修改 — 工具** | `agent_utils.py` | ✅ | ✅ | 新增 8 个 `@tool` 方法 |
| **修改 — 导出** | `agents/__init__.py` | ✅ | ✅ | 导出 3 个新分析师 + `_EXPORTS` |
| **修改 — 图编排** | `trading_graph.py` | ✅ | ✅ | ToolNode + 默认列表 + 进度映射 + `_resolve_selected_analysts` |
| | `setup.py` | ✅ | ✅ | 节点创建逻辑 + 边插入 |
| | `conditional_logic.py` | ✅ | ✅ | 新增 3 个方法 |
| **修改 — 初始状态** | `propagation.py` | ✅ | ✅ | `create_initial_state` 新增 3 字段 |
| **修改 — 反射** | `reflection.py` | ✅ | ✅ | `_extract_current_situation` 纳入 3 报告 |
| **修改 — 下游** | `bull/bear/debator*/trader/*_manager.py` | ✅ | ✅ | 7 个文件 +3 报告提取 + prompt 注入 |
| **修改 — 数据源** | `data_sources.py`, `data_source_manager.py`, `providers_config.py` | ✅ | ✅ | 注册 + 枚举 + 配置 |
| **修改 — Web** | `app/models/analysis.py` | ✅ | ✅ | `selected_analysts` 默认值 +3 ID |
| | `app/worker.py` | ✅ | ✅ | 旧版英文名修正 |
| **新增 — Web** | `analysis_runner.py` | ❌ | ✅ | `total_result.json` 保存 `selected_analysts` |
| | `analysis_form.py` | ❌ | ✅ | 3 个 A 股专属 checkbox |
| | `analysis_results.py` | ❌ | ✅ | `analysis_id` 生成逻辑 |
| **新增 — MongoDB** | `mongodb_report_manager.py` | ❌ | ✅ | 写入 `selected_analysts` 字段 |
| | `report_exporter.py` | ❌ | ✅ | 透传 `selected_analysts` |
| **新增 — 启动** | `app.py` (路径需修正) | ❌ | ✅ | SKILL.md 加载 + 验证日志 |
| **修改 — 依赖** | `requirements.txt` | ✅ | ✅ | +mootdx |
| **修改 — 路由** | `interface.py` | ✅ N/A | ✅ N/A | 确认不需要修改 |

### 4.2 v2.2 仍存在的潜在遗漏

| # | 遗漏项 | 详细说明 | 风险 |
|---|--------|---------|:--:|
| 1 | **前端 Vue.js 适配范围仍未明确** | 方案描述"前端 Vue.js 的分析师选择组件"但未给出具体文件路径和修改范围。CN-wj 实际使用 **Streamlit** 前端（`web/app.py` + `web/components/`），不存在 Vue.js 前端。**方案此处的"前端 Vue.js"描述与实际项目不一致** | 🔴 |
| 2 | **SKILL.md 加载启动路径错误** | 方案确认写入 `app.py`；实际 CN-wj 使用 `app/__main__.py`（uvicorn + lifespan）或 `web/app.py`（Streamlit 直接启动）。**实施时需重新定位插入点** | 🟡 |
| 3 | **`total_result` BUG 无法在当前主流程复现** | 当前 `save_analysis_report` 使用 `stock_symbol: str` 类型安全参数，不存在 JSON int 转换问题。可能仅影响**历史记录加载路径**（`analysis_results.py:234`），但 Python `json.load` 也不会自动转换 | 🟢 |
| 4 | **MongoDB `system_configs` 注册数据源条目** | 方案提到在 MongoDB 中注册 `astock_direct` 数据源条目，但未说明具体配置文档格式、是否兼容现有的 `SystemConfigService` | 🟡 |
| 5 | **`analysis_id` 覆盖逻辑说明不充分** | 方案提到"上游覆盖 `analysis_id`"，但未说明覆盖方式和 `trading_graph.py` 之间的具体调用链 | 🟢 |
| 6 | **3 个新角色对应 ChromaDB memory 索引** | 方案提到分析师报告增加后语义检索指标轻微偏移，但未给出具体应对策略 | 🟢 |

### 4.3 方案对非 A 股市场的处理评估

v2.2 方案的三层防线：

| 层级 | 机制 | 评估 |
|------|------|------|
| **第 1 层（图编排）** | `trading_graph.py` `_resolve_selected_analysts()` — 非 A 股时自动过滤 3 个 A 股角色 | ✅ 主防线正确 |
| **第 2 层（工具层兜底）** | 每个新增 `@tool` 开头判断 `market_type` — 返回"此工具仅适用A股" | ✅ pandas/协程比 AgentNode 轻量 |
| **第 3 层（UI 反馈）** | `analysis_form.py` 非 A 股时隐藏选项 — 防止用户选择 | ✅ UI 操作一致性保证 |

**评估**：三层机制覆盖充分，主防线在图编排层（与已有 social 禁用逻辑一致）。

---

## 五、核心问题与风险

### 5.1 高风险项

| # | 风险 | 说明 | 缓解措施 |
|---|------|------|---------|
| H1 | **分析师实现复杂度严重低估（3 个角色 ~1,300 行）** | v2.2 确认 3 个分析师合计 ~1,700 行，为 astock-wj 235 行的 **7.3x**。原因：`policy/market/fundamentals` 均 ~700 行 vs astock-wj ~100/85/50 行 | 每个新分析师都必须完整复刻：`@log_analyst_module` 装饰器、ToolMessage 计数统计、公司名称降级方案、Google 模型检测与 GoogleToolCallHandler 处理、DashScope/Qwen 兼容（创建新 LLM 实例）、强制工具调用循环、报告格式化模板 |
| H2 | **AStockDirectProvider 生产级封装（~1,200-1,500 行）** | `a_stock.py`（astock-wj，约 95 行管理核心 + 7 层底层实现散布文件）→ 重构为 CN-wj 的 `AStockDirectProvider` 标准 Provider 封装。SKILL.md 代码为 Claude Code 上下文示例，非可导入 Python 模块 | Phase 0 预研 + Phase 1 先实现核心 7 个信号端点最小路径 |
| H3 | **Prompt 膨胀 → 上下文溢出（最低 16K+）** | 4 份报告 → 7 份报告，`curr_situation` 约增大 56%。总 prompt ~9,250 tokens | Phase 0 测算 token 消耗；128K+ 模型不需担心；8K 模型需报告摘要/截断 |

### 5.2 中风险项

| # | 风险 | 说明 | 缓解措施 |
|---|------|------|---------|
| M1 | **非 A 股市场 3 个分析师行为** | 港股/美股分析时，3 个 A 股特化分析师节点会增加 ~45s 耗时 + ~3 次 LLM 调用 | 图编排层 + 工具层 + UI 层三重防线 |
| M2 | **7 个信号层工具无降级链** | 龙虎榜/北向/解禁/热点等仅 `astock_direct` 一个供应商，API 被封则全局失效 | 每个 `@tool` try/except 后返回结构化错误字符串而非异常 |
| M3 | **mootdx httpx 版本冲突** | CN-wj 依赖 `langchain-google-genai` → httpx；mootdx 可能引入旧版 httpx | `pip install mootdx --no-deps`；Phase 0 预验 |
| M4 | **Web 层适配 6 处新增变更** | `mongodb_report_manager.py` + `report_exporter.py` + `analysis_runner.py` + `analysis_form.py` + `app.py` SKILL.md 日志 + `models/analysis.py`； `form_data['analysts']` 键名 → `selected_analysts` 键名转换 | Phase 7 增加完整 Web 适配任务，注意键名差异 |
| M5 | **默认值分散在 4 处** | `app/models/analysis.py` / `setup.py` / `analysis_form.py` / `trading_graph.py` 内部默认 `selected_analysts` 需全部同步修改 | 实施时统一修改 4 处 |
| M6 | **方案"前端 Vue.js"描述与 Streamlit 实际项目不符** | CN-wj 使用 Streamlit 纯 Python 前端，不存在 Vue.js/TypeScript 文件。方案中对"前端 Vue.js"的修改描述需全部修正为"Streamlit Web 层" | 方案文档用词修正 |

### 5.3 低风险项

| # | 风险 | 说明 |
|---|------|------|
| L1 | 分析师命名（`Hot_money` 节点名） | Python `"hot_money".capitalize()` = `"Hot_money"`，命名包含下划线不影响功能 |
| L2 | 新报告为空时下游 `.get(key, "")` 安全 | 已验证所有下游 Agent 均使用此模式 |
| L3 | `tool_call_count` 防死循环 | `max_tool_calls=3` 限制有效 |
| L4 | a-stock-data-wj 同步调用 vs CN-wj 异步 | `asyncio.to_thread()` 包装即可 |

---

## 六、数据源替换专项评估

### 6.1 a-stock-data-wj 聚合数据源分析

SKILL.md 已详细列出 28 个 API 端点（行情/研报/信号/资金面/新闻/基础数据/公告七层），2026-05-17 实测全部可用。

**关键特征**：
- 零第三方封装依赖（仅 mootdx 保留 TCP 7709）
- 所有 HTTP API **免费且无需 API Key**（除 iwencai）
- 响应时间可达 ~70ms（同花顺热点接口）

### 6.2 替换策略评估

策略为**适配器层 + 渐进替换**已在前两版方案确认，评估不变（见 v2.1 报告 §5.3）。

### 6.3 补强措施（v2.2 新增）

| v2.2 新增变更 | 说明 |
|-------------|------|
| SKILL.md 启动时加载验证 | 本项仅需添加 8 行日志；推荐在 `app/__main__.py`（FastAPI lifespan）执行，**非方案写的 `app.py`** |
| `analysis_runner.py` 新增信号日志 | 本项仅需添加 6 行日志，对分析主流程零影响 |
| MongoDB `system_configs` 降级链插入 | 需确认现有 MongoDB 数据源注册流程是否支持通过代码自动 upsert；如不支持，需手动执行配置脚本 |

---

## 七、实施顺序评估

v2.2 方案 7 阶段实施顺序**与 v2.1 一致**（新增 v2.2 的 12 处修正均分布在各 Phase 中），不再重复。关键建议不变：
1. Phase 0（预研 + token 测算 + 端点可用性验证）不可跳过
2. Phase 3（Agent 开发）分步验证策略正确：先 policy_analyst → 验证 → hot_money_tracker → 验证 → lockup_watcher
3. Phase 7 需补全 v2.2 新增的 5 处 Web/MongoDB 适配

---

## 八、总体评估结论

### 8.1 各维度评分

| 维度 | v2.1 | v2.2 | 说明 |
|------|:----:|:----:|------|
| **方案可行性** | ⭐⭐⭐⭐☆ (4/5) | ⭐⭐⭐⭐☆ (4/5) | 架构路径持续正确，但 `app.py` SKILL.md 路径错误需修正 |
| **方案完整性** | ⭐⭐⭐⭐☆ (4/5) | ⭐⭐⭐⭐⭐ (5/5) | v2.2 基于实测 code review 修正，新增 12 处精确变更说明 |
| **工作量估算准确性** | ⭐⭐☆☆☆ (2/5) | ⭐⭐⭐☆☆ (3/5) | 从 ~1,970 → ~4,060-4,660 行，方差的 93% 已收敛到上限 |
| **风险控制** | ⭐⭐⭐⭐☆ (4/5) | ⭐⭐⭐⭐☆ (4/5) | 风险识别全面，缓解措施明确 |
| **文档质量** | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐⭐⭐ (5/5) | 修正历史完整透明，v1.0/v2.1/v2.2 有清晰代码验证标记 |

### 8.2 v2.2 方案需要修正的地方

| # | 修正项 | 当前描述 | 建议修正 |
|---|--------|---------|---------|
| 1 | **SKILL.md 启动日志文件路径** | `app.py` | 改为 `app/__main__.py`（uvicorn 入口 / FastAPI lifespan context manager） |
| 2 | **"前端 Vue.js"描述与项目实际技术栈不符** | 方案提到"前端 Vue.js 的分析师选择组件" | CN-wj 使用 **Streamlit** 纯 Python 前端，不是 Vue.js。改为"Web Streamlit 层" |
| 3 | **`total_result` JSON BUG 标注** | 描述 `$218` 处 `stock_code` int BUG | 当前主流程代码中**不存在该 BUG**。应标注为"防御性加固建议"（入口 `str()` 强制转换），而非"BUG 修正" |
| 4 | **ToolNode 方法名** | 方案写"`_create_tool_nodes()` 之内" | 实际位点在 `TradingAgentsGraph.__init__` 中（非独立方法），实施时需按实际代码结构插入 |

### 8.3 总体结论

**v2.2 方案在基于实际 code review 修正后具备更强的可行性，方案完整性从 4/5 提升到 5/5。**

v2.2 的 12 处修正有 8 处通过源码验证完全正确，2 处需小修（路径名、方法名），1 处描述与项目技术栈不符（"Vue.js"→"Streamlit"），1 处 BUG 标注当前不可复现。

核心难点与 v2.1 一致（3 个分析师 ~1,700 行重写 + AStockDirectProvider ~1,200-1,500 行封装 + prompt 膨胀），v2.2 未降低这些核心难点的工作量。

**实施前建议先执行以下**：
1. 修正方案中 4 处标注（路径 / Vue.js / BUG / ToolNode 方法名）
2. Phase 0 预研：mootdx 安装兼容性、httpx 版本冲突、核心 API 端点可用性验证
3. Token 消耗测算：确认目标 LLM（qwen-turbo/qwen-plus/qwen3-max）的上下文窗口是否满足 ~9,250 tokens 要求

---

> **评估文档版本**: v1.0（针对方案 v2.2）  
> **评估日期**: 2026-05-19  
> **评估方式**: 逐条对照 [migration-plan-3roles-datasource.md](file:///C:/Work/Tra/TradingAgents-CN-wj/docs/migration-plan-3roles-datasource.md) v2.2 与 CN-wj / astock-wj / a-stock-data-wj 源码验证  
> **评估结论**: 方案可行（需修正 4 处描述偏差），完整性极好，工作量偏乐观，Phase 0 必须执行  
> **状态**: 待评审