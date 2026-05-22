# TradingAgents-CN-wj 新增3个A股分析师角色 + 数据源替换方案（v2.3）

> **日期**: 2026-05-19（第四次修正版）  
> **原版**: 2026-05-18（v1.0）→ v2.0 → v2.1 → v2.2 → v2.3  
> **修正来源**: 六份评估报告综合修正  
> **原则**: 不修改，不实施，仅输出方案文档  

---

## 修正说明（v1.0 → v2.1）

v1.0 方案在架构分析层面基本正确，但在以下方面存在显著偏差，本版已逐一修正：

| # | 问题 | 严重度 | 修正方式 |
|---|------|:------:|---------|
| 1 | 分析师实现复杂度严重低估（~100行 vs 实际 ~400-500行） | **严重** | 重写第2节，按 CN-wj 完整模式描述 |
| 2 | `propagation.py` 遗漏 | **严重** | 新增第2.3.7节 |
| 3 | `agents/__init__.py` 的 `_EXPORTS` 懒加载模式未正确描述 | **严重** | 修正第2.3.3节 |
| 4 | tool_call_count 递增逻辑位置错误 | **严重** | 明确在分析师节点内递增，非 conditional_logic |
| 5 | `build_instrument_context()` 误标为"不存在" | **严重** | 已存在 `instrument_utils.py`，修正第1.1节 |
| 6 | `get_insider_transactions` 命名冲突 | **中等** | 统一为 `get_insider_transactions_astock` |
| 7 | `conditional_logic` 方法遗漏日志 | **中等** | 补充完整日志模式 |
| 8 | `_log_state()` 字段名差异 | **中等** | 使用 CN-wj 的字段名（risky/safe/neutral） |
| 9 | 下游适配遗漏 `risk_manager.py` | **中等** | 替换错误的 portfolio_manager 引用 |
| 10 | 反射层适配遗漏 | **中等** | 新增第4.8节 |
| 11 | SKILL.md 代码非生产级 | **高（风险）** | 重估工作量为 1200-1500 行 |
| 12 | Prompt 膨胀导致上下文溢出 | **中（风险）** | 新增风险项 + 预研 Phase |
| 13 | 非 A 股市场兼容性 | **中（风险）** | 新增风险项 + 工具层市场判断 |
| 14 | Web/前端未适配 | **中（风险）** | 新增风险项 |

### v2.0 → v2.1 补充修正（2026-05-19 二次评审）

| # | 问题 | 严重度 | 修正方式 |
|---|------|:------:|---------|
| 15 | `interface.py` 工具注册机制描述不清 | **中等** | 明确新增工具直接调用 AStockDirectProvider，不经 interface.py |
| 16 | `app/models/analysis.py` 默认分析师列表遗漏 | **中等** | 新增至文件变更清单 |
| 17 | `app/worker.py` 旧版英文分析师名硬编码 | **中等** | 新增至文件变更清单 + Phase 7 修复 |
| 18 | 非 A 股时图编排层未跳过3个分析师 | **中等** | 新增第2.4节：在 `setup_graph()` 中根据市场类型动态决定 |
| 19 | Prompt 膨胀缺少量化估算 | **低** | Phase 0 Step 0.1 补充 token 估算基线 |
| 20 | `propagation.py` 已有字段缺失说明不足 | **低** | 补充 LangGraph 自动默认值机制说明 |

### v2.1 → v2.2 补充修正（2026-05-19 第三次评审）

综合 `migration-plan-assessment-report.md`（8项新遗漏）+ `migration-plan-evaluation-report.md`（10项问题）的交叉验证结果：

| # | 问题 | 严重度 | 修正方式 |
|---|------|:------:|---------|
| 21 | 数据源边界不清晰（新增工具 vs 现有统一工具） | **严重** | 新增第3.4节明确数据源策略边界 |
| 22 | worker.py 分析师ID不兼容修复推迟到 Phase 7 | **严重** | 提升至 Phase 2，给出具体代码修复 |
| 23 | `web/utils/analysis_runner.py` 核心入口未分析 | **严重** | 新增第5.4节，确认传递机制 + 分析师ID兼容 |
| 24 | Streamlit 前端 `analysis_form.py` 适配遗漏 | **中等** | 新增第5.5节，纳入文件变更清单，提至 Phase 2 |
| 25 | `data_source_manager.py` ~2500行，降级链修改影响面大 | **中等** | 细化修改方案：优先 MongoDB 注册，硬编码仅 fallback |
| 26 | `_log_state()` JSON 日志遗漏3个新报告 | **中等** | 新增 JSON 字典字段 |
| 27 | `AStockDirectProvider` 生命周期设计未明确 | **中等** | 新增第3.2.1.A节：实例化时机、配置来源、单例模式 |
| 28 | `signal_processing.py` 适配从 v2.1 文件清单中遗漏 | **中等** | 纳入文件变更清单，A 股特色评级词提取 |
| 29 | GoogleToolCallHandler 集成细节不足 | **中等** | 新增第2.7节：3个角色的 `specific_requirements` 参数定义 |
| 30 | Quality Gate 图编排集成点不清晰 | **中等** | 补充具体的边定义、AgentState 字段、conditional 方法 |
| 31 | `a_stock.py`（1992行）可复用性未评估 | **低** | Phase 0 新增 Step 0.4：对比 a_stock.py vs SKILL.md |
| 32 | 测试文件更新策略缺失 | **低** | Phase 7 新增具体测试文件清单 |
| 33 | mootdx Windows TCP 端口兼容性 | **低** | Phase 0 Step 0.2 新增注意事项 |
| 34 | 非 A 股时性能统计空分类 | **低** | 已在 `_build_performance_data` 中自动处理（空字典不影响） |

### v2.2 → v2.3 补充修正（2026-05-19 第四次评审）

综合 `migration-plan-v22-assessment-report.md`（3严重+5中等）+ `migration-plan-evaluation-report-v2.2.md`（4处修正建议）的交叉验证结果：

| # | 问题 | 严重度 | 修正方式 |
|---|------|:------:|---------|
| 35 | `analysis_runner.py:811` valid_analysts 校验会拒绝新分析师ID | **严重** | 新增第4.9.4节，扩展列表，提至 Phase 2 Step 2.6 |
| 36 | `analysis_runner.py:710` analysis_keys 缺少3个新报告字段 | **严重** | 新增至第4.9.4节，用户将看不到新报告 |
| 37 | `analysis_runner.py:36` translate_analyst_labels 缺少3个映射 | **中等** | 新增至第4.9.4节 |
| 38 | `data_sources.py` 文件路径错误 | **中等** | 全文档 `dataflows/data_sources.py` → `constants/data_sources.py` |
| 39 | `data_source_manager.py:216` source_mapping 第二处副本遗漏 | **中等** | 第3.3.2节补充 |
| 40 | `ChinaDataSource` 枚举和 `DataSourceCode` 枚举缺 ASTOCK_DIRECT 成员 | **中等** | 第3.3.2节明确列出两处枚举新增 |
| 41 | Step 7.6 "Vue.js 前端" 与 Streamlit 项目技术栈不符 | **中等** | 改为 "Streamlit 前端（含 API 端点）" |
| 42 | ToolNode 位点在 `__init__` 中非独立 `_create_tool_nodes` 方法 | **低** | 修正描述为"在 TradingAgentsGraph.__init__ 中" |
| 43 | signal_processing.py 适配描述不够具体 | **低** | 细化：在 `process_signal()` system prompt 中加入 A 股评级词映射 |
| 44 | Quality Gate conditional 边缺少伪代码 | **低** | 补充实现策略 |
| 45 | `$218` total_result JSON int BUG 当前主流程不可复现 | **低** | 方案中不作声明（不存在的 bug 无需"修复"） |

---

## 目录

1. [架构差异概览（已修正）](#1-架构差异概览已修正)
2. [第一部分：新增3个分析师角色（已修正）](#2-第一部分新增3个分析师角色已修正)
3. [第二部分：数据源替换为a-stock-data-wj（已修正）](#3-第二部分数据源替换为a-stock-data-wj已修正)
4. [第三部分：下游Agent适配（已修正）](#4-第三部分下游agent适配已修正)
5. [第四部分：完整文件变更清单（已修正）](#5-第四部分完整文件变更清单已修正)
6. [第五部分：实施顺序与依赖（已修正）](#6-第五部分实施顺序与依赖已修正)
7. [第六部分：风险评估（已修正）](#7-第六部分风险评估已修正)

---

## 1. 架构差异概览（已修正）

### 1.1 两个TradingAgents项目的差异

| 维度 | TradingAgents-astock-wj | TradingAgents-CN-wj |
|------|------------------------|---------------------|
| **分析师签名** | `create_*_analyst(llm)` — 单参数 | `create_*_analyst(llm, toolkit)` — 双参数 |
| **工具组织** | 模块化: 独立 `*_tools.py` 文件，导入为独立函数 | 单体化: `Toolkit` 类中 `@tool` 装饰的方法 |
| **分析师节点执行模式** | 简单: `llm.bind_tools() → invoke → return`（~85行） | 复杂: 手动工具执行 + 二次LLM + 强制报告生成 + Google/DashScope兼容（~400-700行） |
| **工具执行方式** | 依赖 LangGraph ToolNode 多轮图迭代 | 分析师节点**内部手动执行工具** + 二次 LLM 调用 |
| **输出格式模板** | 无 | 有（详细的格式化 prompt，100+ 行） |
| **公司名称获取** | `build_instrument_context()` | `_get_company_name()` 含多级降级方案 |
| **语言支持** | `get_language_instruction()` 辅助函数 | 硬编码 "请使用中文撰写" |
| **股票上下文** | `build_instrument_context()` | **已存在**: `tradingagents/agents/utils/instrument_utils.py` |
| **工具调用计数** | 无防死循环机制 | 有 `*_tool_call_count` 状态字段（在分析师节点内递增） |
| **日志装饰器** | 无 | `@log_analyst_module` 统一装饰器 |
| **Google模型支持** | 无特殊处理 | 有 `GoogleToolCallHandler` 兼容（`google_tool_handler.py`，751行） |
| **DashScope/Qwen兼容** | 无 | 检测后创建全新 LLM 实例避免工具缓存 |
| **强制工具调用** | 无 | 当 LLM 未主动调用工具时，手动 invoke + 强制生成报告 |
| **ToolMessage 计数** | 无 | `sum(1 for msg in messages if isinstance(msg, ToolMessage))` |
| **分析师数量** | 7个（市场/情绪/新闻/基本面 + 政策/游资/解禁） | 4个（市场/情绪/新闻/基本面） |
| **市场覆盖** | A股专用 | A股 + 港股 + 美股（多市场） |
| **数据源** | 零第三方封装（mootdx TCP + 直连HTTP） | 多源+降级链（MongoDB→Tushare→AKShare→BaoStock） |
| **ChromaDB记忆** | 无 | 有 `FinancialSituationMemory` + `Reflector` 反思机制 |
| **最终决策者** | Portfolio Manager | **Risk Manager**（`risk_manager.py`，含3次重试机制） |

### 1.2 CN-wj 分析师节点的完整实现模式（关键修正）

基于对 `fundamentals_analyst.py`（698行）的源码分析，CN-wj 的分析师节点必须包含以下完整模式：

```
1. @log_analyst_module 装饰器
2. ToolMessage 计数统计 → tool_call_count 递增
3. 市场信息获取（StockUtils.get_market_info）
4. 多级公司名称降级方案（A股/港股/美股）
5. build_instrument_context() 上下文构建
6. 系统消息 + 格式化输出模板
7. Google 模型检测 → GoogleToolCallHandler 处理
8. DashScope/Qwen 检测 → 创建全新 LLM 实例
9. llm.bind_tools(tools) → invoke
10. 结果分析：
    ├── Google 模型 → handle_google_tool_calls()
    ├── 有 tool_calls + 已有 ToolMessage → 强制生成报告（不绑定工具的二次 LLM 调用）
    ├── 有 tool_calls + tool_call_count >= max → 降级报告
    ├── 有 tool_calls + 首次 → 返回 tool_calls（等待 ToolNode 执行）
    └── 无 tool_calls → 检查是否需要强制调用工具 → 手动 invoke 工具 → 二次 LLM
11. 返回 {report_field: str, tool_call_count: int}
```

每个新分析师预估 **400-500 行**（非 v1.0 的 100-130 行）。

---

## 2. 第一部分：新增3个分析师角色（已修正）

### 2.1 概述与核心适配规则

1. astock-wj 的简单模式（`llm.bind_tools() → invoke → return`，~85行）**不能直接移植**。
2. 必须完全按照 CN-wj 的完整分析师模式重写（参照 `fundamentals_analyst.py`）。
3. 添加 `*_tool_call_count` 防死循环机制（**在分析师节点内部递增**，非 conditional_logic）。
4. 添加 `GoogleToolCallHandler` 兼容 + `DashScope/Qwen` 兼容。
5. 保持 astock-wj 的中文提示词和 A 股分析框架不变。
6. `@log_analyst_module` 装饰器。
7. astock-wj 的独立工具函数 → CN-wj 的 `toolkit.*` @tool 方法。
8. `build_instrument_context()` **已存在**于 `instrument_utils.py`，直接导入即可。
9. `get_language_instruction()` **不存在**，需新增或保持硬编码。

### 2.4 非 A 股市场时3个分析师的处理策略（新增）

**问题**：仅靠 Toolkit @tool 方法中做市场判断（非 A 股返回"此工具仅适用于 A 股市场"），在**图编排层**3个新分析师节点仍会被创建和执行，导致 LLM 浪费调用、增加耗时、产生占位报告。

**正确的两阶段处理**：

| 阶段 | 位置 | 作用 |
|------|------|------|
| 阶段 1 — 图编排层（主要防线） | `trading_graph.py` 或 `setup.py` | 根据市场类型动态决定 `selected_analysts`，非 A 股时直接不创建3个节点 |
| 阶段 2 — 工具层（兜底防线） | Toolkit @tool 方法 | 非 A 股返回"此工具仅适用于 A 股" |

**实现方式**：

```python
def _resolve_selected_analysts(self, market_type: str) -> List[str]:
    base_analysts = ["market", "social", "news", "fundamentals"]
    a_stock_only = ["policy", "hot_money", "lockup"]

    is_a_stock = market_type in ("A股", "中国", "China", "a_stock")
    if is_a_stock:
        return base_analysts + a_stock_only
    return base_analysts
```

**注意事项**：
- 用户手动选择的 `selected_analysts` 应优先于市场类型自动决定
- 非 A 股时如果用户强行指定了 `policy`/`hot_money`/`lockup`，应给出 warning 日志
- 下游 Agent（Bull/Bear/Manager）的 `curr_situation` 拼接逻辑使用 `.get("xxx_report", "")` 模式，即使报告为空也能安全运行

### 2.5 需要新增的文件

#### 文件 2.5.1: `tradingagents/agents/analysts/policy_analyst.py`（预估 ~400 行）

**角色**: 政策分析师  
**工具**: `toolkit.get_stock_news_unified` + `toolkit.get_global_news_openai`  
**状态输出**: `policy_report`, `policy_tool_call_count`  
**max_tool_calls**: 3  
**提示词**: 从 astock-wj 移植（中文，5层政策分析框架）

#### 文件 2.5.2: `tradingagents/agents/analysts/hot_money_tracker.py`（预估 ~500 行）

**角色**: 游资追踪分析师（最复杂）  
**工具**: 9个（见下方工具映射表）  
**状态输出**: `hot_money_report`, `hot_money_tool_call_count`  
**max_tool_calls**: 3  

工具映射：
| astock-wj 工具 | → CN-wj Toolkit 方法 | 数据来源 |
|---------------|---------------------|---------|
| `get_stock_data` | `toolkit.get_stock_market_data_unified` | 已有 |
| `get_news` | `toolkit.get_stock_news_unified` | 已有 |
| `get_insider_transactions` | `toolkit.get_insider_transactions_astock` | **新增**（mootdx F10） |
| `get_hot_stocks` | `toolkit.get_hot_stocks` | **新增**（同花顺热点） |
| `get_northbound_flow` | `toolkit.get_northbound_flow` | **新增**（同花顺 hsgtApi） |
| `get_concept_blocks` | `toolkit.get_concept_blocks` | **新增**（百度股市通） |
| `get_fund_flow` | `toolkit.get_fund_flow` | **新增**（百度股市通） |
| `get_dragon_tiger_board` | `toolkit.get_dragon_tiger_board` | **新增**（东财 datacenter） |
| `get_industry_comparison` | `toolkit.get_industry_comparison` | **新增**（东财 push2） |

#### 文件 2.5.3: `tradingagents/agents/analysts/lockup_watcher.py`（预估 ~400 行）

**角色**: 解禁监控分析师  
**工具**: 4个  
**状态输出**: `lockup_report`, `lockup_tool_call_count`  
**max_tool_calls**: 3  

工具映射：
| astock-wj 工具 | → CN-wj Toolkit 方法 | 数据来源 |
|---------------|---------------------|---------|
| `get_insider_transactions` | `toolkit.get_insider_transactions_astock` | **新增** |
| `get_news` | `toolkit.get_stock_news_unified` | 已有 |
| `get_fundamentals` | `toolkit.get_stock_fundamentals_unified` | 已有 |
| `get_lockup_expiry` | `toolkit.get_lockup_expiry` | **新增**（东财 datacenter） |

### 2.6 需要修改的现有文件

#### 文件 2.6.1: `tradingagents/agents/utils/agent_states.py`

在 `AgentState` TypedDict 中新增6个字段（在 `fundamentals_tool_call_count` 之后）：

```python
# 新增：3个A股特化分析师报告
policy_report: Annotated[str, "Report from the Policy Analyst (A-stock specific)"]
hot_money_report: Annotated[str, "Report from the Hot Money Tracker (A-stock specific)"]
lockup_report: Annotated[str, "Report from the Lockup/Reduction Watcher (A-stock specific)"]

# 新增：防死循环工具调用计数器
policy_tool_call_count: Annotated[int, "Policy analyst tool call counter"]
hot_money_tool_call_count: Annotated[int, "Hot money tracker tool call counter"]
lockup_tool_call_count: Annotated[int, "Lockup watcher tool call counter"]
```

#### 文件 2.6.2: `tradingagents/agents/utils/agent_utils.py`

在 `Toolkit` 类中新增 **8个 `@tool` 方法**：

1. `get_insider_transactions_astock(self, ticker: str) -> str` — A股股东/内部人交易
2. `get_hot_stocks(self, curr_date: str) -> str` — 当日涨停股+题材归因
3. `get_northbound_flow(self, curr_date: str) -> str` — 北向资金分钟级流向
4. `get_concept_blocks(self, ticker: str) -> str` — 概念板块/行业/地域分类
5. `get_fund_flow(self, ticker: str, curr_date: str) -> str` — 主力/散户资金流向
6. `get_dragon_tiger_board(self, ticker: str, curr_date: str) -> str` — 龙虎榜席位明细
7. `get_lockup_expiry(self, ticker: str, curr_date: str) -> str` — 限售解禁日历
8. `get_industry_comparison(self, ticker: str, curr_date: str) -> str` — 行业横向对比

每个 @tool 方法必须包含：
- 非 A 股市场判断（非 A 股时返回"此工具仅适用于 A 股市场"）
- 调用 `astock_direct` adapter 或降级数据源
- 返回 LLM 可消费的 str 类型

是否新增 `get_language_instruction()` 辅助函数：**建议保持硬编码**（CN-wj 现有模式），不新增。

**命名统一确认**: `get_insider_transactions_astock` 与现有的 `get_finnhub_company_insider_transactions` 共存于 Toolkit，命名明确区分 A 股/美股。

#### 文件 2.6.3: `tradingagents/agents/__init__.py`

CN-wj 使用 `_EXPORTS: Dict[str, Tuple[str, str]]` + `__getattr__` 懒加载模式。必须同时修改 `_EXPORTS` 字典和 `__all__` 列表：

```python
_EXPORTS = {
    # ... 现有条目保持不变 ...
    "create_policy_analyst": ("tradingagents.agents.analysts.policy_analyst", "create_policy_analyst"),
    "create_hot_money_tracker": ("tradingagents.agents.analysts.hot_money_tracker", "create_hot_money_tracker"),
    "create_lockup_watcher": ("tradingagents.agents.analysts.lockup_watcher", "create_lockup_watcher"),
}

__all__ = [
    # ... 现有条目保持不变 ...
    "create_policy_analyst",
    "create_hot_money_tracker",
    "create_lockup_watcher",
]
```

#### 文件 2.6.4: `tradingagents/graph/trading_graph.py`

**A. `__init__` 默认参数**（第195行）：
```python
selected_analysts=["market", "social", "news", "fundamentals", "policy", "hot_money", "lockup"]
```

**B. 在 `TradingAgentsGraph.__init__` 中新增 3 个 ToolNode**（当前代码 ToolNode 创建逻辑在 `__init__` 内，非独立的 `_create_tool_nodes()` 方法；实施时需按实际代码结构插入）：
```python
"policy": ToolNode([
    self.toolkit.get_stock_news_unified,
    self.toolkit.get_global_news_openai,
]),
"hot_money": ToolNode([
    self.toolkit.get_stock_market_data_unified,
    self.toolkit.get_stock_news_unified,
    self.toolkit.get_insider_transactions_astock,
    self.toolkit.get_hot_stocks,
    self.toolkit.get_northbound_flow,
    self.toolkit.get_concept_blocks,
    self.toolkit.get_fund_flow,
    self.toolkit.get_dragon_tiger_board,
    self.toolkit.get_industry_comparison,
]),
"lockup": ToolNode([
    self.toolkit.get_insider_transactions_astock,
    self.toolkit.get_stock_news_unified,
    self.toolkit.get_stock_fundamentals_unified,
    self.toolkit.get_lockup_expiry,
]),
```

**C. `_log_state()` 新增3个报告字段**（第1112-1142行）— 同时修改**内存字典**和**JSON 文件写入**：

```python
# 新增到 log_states_dict（第1114-1142行的返回字典中）
"policy_report": final_state.get("policy_report", ""),
"hot_money_report": final_state.get("hot_money_report", ""),
"lockup_report": final_state.get("lockup_report", ""),
```

这3个字段会随 `json.dump()` 写入 `eval_results/{ticker}/TradingAgentsStrategy_logs/full_states_log.json`。使用 `.get()` 安全取值（非 A 股场景下可能不存在）。

**D. `_build_performance_data()` 和 `_print_timing_summary()` 的节点分类**（第921-1060行）：
- 3个新节点的名称（`"Policy Analyst"`、`"Hot_money Analyst"`、`"Lockup Analyst"`）自动匹配 `'Analyst' in node_name` 判断（第945行），归入 `analyst_nodes` 分类
- `Msg Clear` 和 `tools_` 前缀的节点也会自动匹配现有分类规则
- **非 A 股时如果节点被跳过**，`analyst_nodes` 字典中无对应条目——这不影响功能（`_build_performance_data` 第983-986行对空字典的 `sum()` 返回 0）
- **不需要修改分类逻辑**

**E. `_send_progress_update()` 的 `node_mapping` 字典**（第872-898行）新增：
```python
'Policy Analyst': "🏛️ 政策分析师",
'tools_policy': None,
'Msg Clear Policy': None,
'Hot_money Analyst': "💰 游资追踪师",
'tools_hot_money': None,
'Msg Clear Hot_money': None,
'Lockup Analyst': "🔓 解禁监控师",
'tools_lockup': None,
'Msg Clear Lockup': None,
```

#### 文件 2.6.5: `tradingagents/graph/setup.py`

**A. 头部 import 新增3个**：
```python
from tradingagents.agents import (
    # ... 现有导入 ...
    create_policy_analyst,
    create_hot_money_tracker,
    create_lockup_watcher,
)
```

**B. `setup_graph()` 方法中新增3个分析师节点创建块**（在 `if "fundamentals"` 块之后）：

```python
if "policy" in selected_analysts:
    analyst_nodes["policy"] = create_policy_analyst(self.quick_thinking_llm, self.toolkit)
    delete_nodes["policy"] = create_msg_delete()
    tool_nodes["policy"] = self.tool_nodes["policy"]

if "hot_money" in selected_analysts:
    analyst_nodes["hot_money"] = create_hot_money_tracker(self.quick_thinking_llm, self.toolkit)
    delete_nodes["hot_money"] = create_msg_delete()
    tool_nodes["hot_money"] = self.tool_nodes["hot_money"]

if "lockup" in selected_analysts:
    analyst_nodes["lockup"] = create_lockup_watcher(self.quick_thinking_llm, self.toolkit)
    delete_nodes["lockup"] = create_msg_delete()
    tool_nodes["lockup"] = self.tool_nodes["lockup"]
```

**C. 修改 `setup_graph` 默认参数**（第66行）：
```python
def setup_graph(
    self, selected_analysts=["market", "social", "news", "fundamentals", "policy", "hot_money", "lockup"]
):
```

**D. 注意**: `"hot_money".capitalize()` = `"Hot_money"`（含下划线），节点名称将为 `"Hot_money Analyst"`。这影响 `add_node()` 调用、进度映射键名、`getattr(conditional_logic, "should_continue_hot_money")` 动态方法查找。所有引用点必须使用统一名称。

#### 文件 2.6.6: `tradingagents/graph/conditional_logic.py`

新增3个条件判断方法（**含完整日志记录**，参照 `should_continue_market()` 模式）：

```python
def should_continue_policy(self, state: AgentState):
    """Determine if policy analysis should continue."""
    from tradingagents.utils.logging_init import get_logger
    logger = get_logger("agents")

    messages = state["messages"]
    last_message = messages[-1]
    tool_call_count = state.get("policy_tool_call_count", 0)
    max_tool_calls = 3
    policy_report = state.get("policy_report", "")

    logger.info(f"🔀 [条件判断] should_continue_policy")
    logger.info(f"🔀 [条件判断] - 消息数量: {len(messages)}")
    logger.info(f"🔀 [条件判断] - 报告长度: {len(policy_report)}")
    logger.info(f"🔧 [死循环修复] - 工具调用次数: {tool_call_count}/{max_tool_calls}")

    if tool_call_count >= max_tool_calls:
        logger.warning(f"🔧 [死循环修复] 达到最大工具调用次数，强制结束: Msg Clear Policy")
        return "Msg Clear Policy"
    if policy_report and len(policy_report) > 100:
        logger.info(f"🔀 [条件判断] ✅ 报告已完成，返回: Msg Clear Policy")
        return "Msg Clear Policy"
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"🔀 [条件判断] 🔧 检测到tool_calls，返回: tools_policy")
        return "tools_policy"
    logger.info(f"🔀 [条件判断] ✅ 无tool_calls，返回: Msg Clear Policy")
    return "Msg Clear Policy"

# should_continue_hot_money 和 should_continue_lockup 模式相同
# 注意: hot_money 的节点名是 "Hot_money"，所以返回值是 "Msg Clear Hot_money"
```

**重要**: 计数器递增逻辑在**分析师节点函数内部**（通过 `ToolMessage` 计数实现），**不在** conditional_logic 中。conditional_logic 只做读取和判断。

#### 文件 2.6.7: `tradingagents/graph/propagation.py`（v1.0 遗漏）

在 `create_initial_state()` 方法（第22-52行）中新增6个字段的初始化：

```python
# 在第48-51行之后添加
"policy_report": "",
"hot_money_report": "",
"lockup_report": "",
```

注意：
- `tool_call_count` 字段不需要在此初始化（它们通过 `state.get("xxx_tool_call_count", 0)` 的默认值机制处理）
- CN-wj 现有 `create_initial_state()` 也未初始化 `sender`、`market_tool_call_count` 等字段——这些字段依赖 LangGraph StateGraph 对 TypedDict 字段的**自动默认值填充**机制（int→0, str→"", list→[]）。只要 `AgentState` TypedDict 中定义了这些字段，LangGraph 会自动提供默认值。3个新报告字段同理，但**显式初始化更安全**（避免不同 LangGraph 版本行为差异）

### 2.7 新分析师 Google/DashScope 兼容集成细节（v2.2 新增）

3个新分析师必须包含 `GoogleToolCallHandler` 的完整处理流程（参照 `fundamentals_analyst.py:416-598`）。每个分析师需要定义 `create_analysis_prompt()` 的 `specific_requirements` 参数。

#### 2.7.1 政策分析师 `specific_requirements`

```python
specific_requirements = """
请从以下五个层面分析政策对股票的影响：
1. 宏观政策面：货币政策（利率、准备金率）、财政政策走向
2. 产业政策面：所属行业的政策扶持/限制力度
3. 监管环境：近期监管处罚、法规变化、行业整顿
4. 区域政策：自贸区、新区规划等区域性利好/利空
5. 政策预期：市场对政策走向的预期与可能变化

输出格式：每个层面单独成段，末尾给出政策面综合评级（利好/中性/利空，附带置信度）。
"""
```

#### 2.7.2 游资追踪分析师 `specific_requirements`

```python
specific_requirements = """
请从以下维度分析游资和资金流向：
1. 龙虎榜分析：近期上榜的营业部席位、买入/卖出金额、净买入排名
2. 北向资金：沪/深股通净流入流出、持仓变化趋势
3. 主力资金：超大单/大单净流入流出、主力持仓变化
4. 概念板块：所属概念板块的资金关注度、板块整体资金流向
5. 行业对比：同行业资金流入流出排名、相对强弱

输出格式：每个维度单独成段，末尾给出资金面综合评级（积极/中性/消极，附带置信度）。
"""
```

#### 2.7.3 解禁监控分析师 `specific_requirements`

```python
specific_requirements = """
请从以下维度分析限售解禁和减持风险：
1. 近期解禁：未来1-3个月的解禁数量、解禁市值、占总股本比例
2. 解禁类型：首发解禁/定增解禁/股权激励解禁（风险依次降低）
3. 股东减持：近期大股东/高管减持公告、减持理由、减持比例
4. 历史参考：同类股票解禁前后的股价表现
5. 减持预判：结合当前估值水平，判断解禁后减持意愿

输出格式：每个维度单独成段，末尾给出解禁风险评级（高风险/中风险/低风险，附带置信度）。
"""
```

---

## 3. 第二部分：数据源替换为a-stock-data-wj（已修正）

### 3.1 替换策略（不变）

推荐方案：**适配器层 + 渐进替换**

1. 创建 `AStockDirectProvider` 类封装 a-stock-data-wj 的全部28个端点
2. 注册为新的数据源选项，优先级最高
3. 现有降级链（MongoDB → Tushare → AKShare → BaoStock）保持不变
4. 仅 A 股数据走新通道，港股/美股数据保持原样

### 3.2 需要新增的文件

#### 文件 3.2.1: `tradingagents/dataflows/providers/china/astock_direct.py`（预估 1200-1500 行）

**修正**: v1.0 预估 800 行过于乐观。SKILL.md 中的代码是面向 Claude Code Skill 上下文注入设计的示例片段，不是可导入的 Python 模块。实际需要：

1. 从 Markdown 代码块中提取 28 个端点的代码
2. 重构为类方法，统一错误处理
3. 添加生产级特性：重试、超时、日志、类型注解
4. 适配 CN-wj Provider 接口
5. 方法名映射（SKILL.md 函数名 → Toolkit @tool 方法名）

**生命周期与依赖注入设计**（v2.2 新增）：

```
实例化时机：TradingAgentsGraph.__init__ 中创建（在 Toolkit 创建之前）
配置来源：   config 字典中的 astock_config 子配置（mootdx 端口、超时等）
单例模式：   整个分析会话中复用同一个 AStockDirectProvider 实例（mootdx TCP 连接池化）
注入方式：   通过 Toolkit.__init__ 的 astock_provider 参数注入
```

```python
# trading_graph.py 中的创建顺序
self.astock_provider = AStockDirectProvider(
    config=self.config.get("astock_config", {}),
    mongodb_cache=self.cache_manager,  # 北向资金用 MongoDB 替代 CSV
)
self.toolkit = Toolkit(config=self.config, astock_provider=self.astock_provider)
```

Toolkit 签名修改：
```python
class Toolkit:
    def __init__(self, config: dict = None, astock_provider=None):
        self.astock_provider = astock_provider  # 可能为 None（非 A 股场景）
```

**类结构**（与 v1.0 相同，行数调整）：

```python
class AStockDirectProvider:
    """A股直连HTTP/TCP数据供应商。零第三方封装依赖（仅 mootdx + requests）。"""
    
    def __init__(self, config: dict = None): ...
    
    # ===== 行情层 =====
    def get_realtime_quote(self, ticker: str) -> str: ...     # 腾讯财经 PE/PB/市值/换手率
    def get_kline_with_ma(self, ticker: str, start: str) -> str: ...  # 百度K线带MA
    
    # ===== 信号层 =====
    def get_hot_stocks(self, date: str) -> str: ...            # 同花顺热点
    def get_northbound_flow(self, date: str) -> str: ...       # 北向资金
    def get_concept_blocks(self, ticker: str) -> str: ...      # 概念板块
    def get_fund_flow(self, ticker: str, date: str) -> str: ... # 资金流向
    def get_dragon_tiger_board(self, ticker: str, date: str) -> str: ... # 龙虎榜
    def get_lockup_expiry(self, ticker: str, date: str) -> str: ...       # 解禁日历
    def get_industry_comparison(self, top_n: int) -> str: ...             # 行业对比
    
    # ===== 资金面/筹码层 =====
    def get_margin_trading(self, ticker: str) -> str: ...
    def get_block_trade(self, ticker: str) -> str: ...
    def get_holder_num_change(self, ticker: str) -> str: ...
    def get_dividend_history(self, ticker: str) -> str: ...
    def get_fund_flow_120d(self, ticker: str) -> str: ...
    
    # ===== 新闻层 =====
    def get_stock_news(self, ticker: str) -> str: ...          # 东财个股新闻
    def get_cls_telegraph(self) -> str: ...                    # 财联社快讯
    def get_global_news(self) -> str: ...                      # 东财全球资讯
    
    # ===== 基础数据层 =====
    def get_stock_info(self, ticker: str) -> str: ...          # 东财个股信息
    def get_financial_report(self, ticker: str, report_type: str) -> str: ... # 新浪财报
    def get_insider_transactions(self, ticker: str) -> str: ... # mootdx F10 股东研究
    
    # ===== 共享辅助 =====
    @staticmethod
    def _normalize_code(ticker: str) -> str: ...
    @staticmethod
    def _eastmoney_datacenter(report_name, columns, filter_str, ...) -> list: ...
```

**关键适配要点**:
- SKILL.md 返回 DataFrame/dict → AStockDirectProvider 方法返回 str（LLM 可消费）
- 每个方法的返回字符串要包含足够的上下文信息（股票代码、日期、数据来源标注）
- 北向资金历史数据改用 CN-wj 的 MongoDB 缓存（而非 SKILL.md 的 CSV 自缓存），以保证多实例部署时的数据一致性
- 所有方法需包含 try/except + 超时处理 + 明确的错误信息返回

### 3.3 需要修改的现有文件

#### 3.3.1 `tradingagents/dataflows/providers/china/__init__.py`

新增 `AStockDirectProvider` 导出。

#### 3.3.2 `tradingagents/dataflows/data_source_manager.py`

**修正**：CN-wj 没有 `CHINA_FALLBACK_CHAIN` 常量。实际降级链机制为：

1. **数据库配置**（优先）：从 MongoDB `system_configs.data_source_configs` 读取，按 `priority` 排序
2. **硬编码回退**（`_get_data_source_priority_order()` 第163-169行）：`[AKSHARE, TUSHARE, BAOSTOCK]`

需修改以下位置：

**前置条件**：先在两个枚举类中新增 `ASTOCK_DIRECT` 成员，否则所有引用会抛出 `AttributeError`：

1. `tradingagents/constants/data_sources.py` → `DataSourceCode` 枚举（第 17 行）：
   ```python
   ASTOCK_DIRECT = "astock_direct"
   ```
2. `tradingagents/dataflows/data_source_manager.py` → `ChinaDataSource` 枚举（第 28-38 行）：
   ```python
   ASTOCK_DIRECT = DataSourceCode.ASTOCK_DIRECT
   ```

**修改点**：

- **硬编码回退列表**（第 165-169 行）：在 `AKSHARE` 之前插入 `ASTOCK_DIRECT`
- **`source_mapping` 第一处**（第 138-142 行，`_get_data_source_priority_order()`）：新增 `DataSourceCode.ASTOCK_DIRECT: ChinaDataSource.ASTOCK_DIRECT`
- **`source_mapping` 第二处**（第 216-219 行，`_get_default_china_source()`）：**也必须同步新增** ASTOCK_DIRECT 条目。若只改第一处，当数据库无配置走环境变量回退路径时，`ASTOCK_DIRECT` 仍不可用
- **数据库配置注册**：在 MongoDB `system_configs` 集合中注册 `astock_direct` 数据源条目（type: "astock_direct", priority 最高, market_categories: ["A股"]）

#### 3.3.3 `tradingagents/dataflows/interface.py`

**修正**：CN-wj 的 `interface.py` **没有** `VENDOR_METHODS` 注册表（这是 astock-wj 的设计）。CN-wj 采用**独立函数导出**模式（如 `get_china_stock_data_unified()`、`get_stock_data_by_market()` 等顶层函数）。

新增的8个 Toolkit @tool 方法**不应**经过 `interface.py` 路由——它们应该：
1. 直接在 `agent_utils.py` Toolkit 的 @tool 方法内部调用 `AStockDirectProvider` 实例
2. `AStockDirectProvider` 作为 Toolkit 的依赖注入（`Toolkit.__init__` 新增参数 `astock_provider`）

**不需要修改 `interface.py`**。此处的修改仅限：如果政策分析师需要的 `get_global_news_openai` 要替换为 A 股专用新闻源，则新增可选函数；否则保持不变。

#### 3.3.4 其他文件

- `tradingagents/constants/data_sources.py`：注册 `astock_direct` 数据源代码（`DataSourceCode` 枚举新增 `ASTOCK_DIRECT = "astock_direct"`；`DATA_SOURCE_REGISTRY` 新增条目）
- `tradingagents/dataflows/providers_config.py`：配置 astock_direct 连接参数
- `requirements.txt`：新增 `mootdx`（建议 `--no-deps` 安装）

### 3.4 数据源策略边界明确化（v2.2 新增）

**核心原则**：**新增的8个 A 股专用工具** 和 **现有的4个统一工具** 使用不同的数据源策略，不得混淆。

| 工具类别 | 工具列表 | A 股数据源 | 港股/美股数据源 | 理由 |
|---------|---------|-----------|---------------|------|
| **新增8个 A 股专用工具** | `get_insider_transactions_astock`, `get_hot_stocks`, `get_northbound_flow`, `get_concept_blocks`, `get_fund_flow`, `get_dragon_tiger_board`, `get_lockup_expiry`, `get_industry_comparison` | **仅 astock_direct**（直连） | N/A（非 A 股市场判断兜底） | 这些工具的数据仅 A 股有，不存在于港股/美股数据源 |
| **现有4个统一工具** | `get_stock_market_data_unified`, `get_stock_fundamentals_unified`, `get_stock_news_unified`, `get_stock_sentiment_unified` | **保持不变**（MongoDB→Tushare→AKShare→BaoStock） | 保持不变 | 统一工具内含 A/H/US 三市场路由（`StockUtils.get_market_info`），直接替换会破坏非 A 股路径 |

**为什么不把 astock_direct 加入现有统一工具的降级链？**

1. 统一工具的 A/H/US 路由依赖 `StockUtils.identify_stock_market()` 返回 `StockMarket` 枚举
2. 如果在统一工具内部新增 `astock_direct` 为 A 股最高优先级分支，需要修改每个统一工具的实现（`get_china_stock_data_unified()` 等）
3. 这是**后续优化**（Phase 2 评估），非本次迁移必须

**Phase 1 实现策略**：
- `AStockDirectProvider` 只被**新增的8个 @tool 方法**调用
- 现有4个统一工具**完全不修改**
- 数据边界清晰，零耦合

---

## 4. 第三部分：下游Agent适配（已修正）

新增的3个报告（`policy_report`、`hot_money_report`、`lockup_report`）需要流向下游所有 Agent。

### 4.1 Bull Researcher

**文件**: `tradingagents/agents/researchers/bull_researcher.py`

当前 `curr_situation`（第87行）只含4个报告。需要：
1. 提取3个新报告：`policy_report = state.get("policy_report", "")` 等
2. 追加到 `curr_situation`：`f"{market_report}\n\n...\n\n{policy_report}\n\n{hot_money_report}\n\n{lockup_report}"`
3. 在 prompt 模板（第115-118行）中新增：
   ```
   政策分析报告：{policy_report}
   游资资金流分析报告：{hot_money_report}
   解禁减持风险评估报告：{lockup_report}
   ```

**重要**: `curr_situation` 也用于 ChromaDB 记忆检索（第91行 `memory.get_memories(curr_situation, n_matches=2)`），所以记忆检索会自动包含新报告内容。

### 4.2 Bear Researcher

**文件**: `tradingagents/agents/researchers/bear_researcher.py`

与 Bull Researcher 完全相同的修改模式（第76行 `curr_situation` + 第106-109行 prompt模板）。

### 4.3 风险辩论三方

**文件**: 
- `tradingagents/agents/risk_mgmt/aggresive_debator.py`（第45-48行 prompt）
- `tradingagents/agents/risk_mgmt/conservative_debator.py`（第46-49行 prompt）
- `tradingagents/agents/risk_mgmt/neutral_debator.py`（第49-52行 prompt）

每个文件需要：
1. 从 state 提取3个新报告
2. 在 prompt 模板中新增：
   ```
   政策分析报告：{policy_report}
   游资资金流分析报告：{hot_money_report}
   解禁减持风险评估报告：{lockup_report}
   ```

### 4.4 Trader

**文件**: `tradingagents/agents/trader/trader.py`

当前 `curr_situation`（第39行）只含4个报告。需要：
1. 提取3个新报告
2. 追加到 `curr_situation`
3. 在系统 prompt（第61-98行）中添加 A 股特定约束上下文（条件注入，仅 `is_china` 时生效）：
   - T+1 交易制度提醒
   - 涨跌停限制
   - 政策面/资金面/解禁面信号参考

### 4.5 Research Manager

**文件**: `tradingagents/agents/managers/research_manager.py`

当前 `curr_situation`（第22行）只含4个报告，用于 ChromaDB 记忆检索（第26行）。需要：
1. 提取3个新报告
2. 追加到 `curr_situation`
3. 在 prompt（第61-68行）中可选择性提及 A 股特定因子

### 4.6 Risk Manager（修正：非 Portfolio Manager）

**文件**: `tradingagents/agents/managers/risk_manager.py`

**修正**: CN-wj 的最终决策者是 Risk Manager（`risk_manager.py`），而非 astock-wj 的 Portfolio Manager。CN-wj 没有 `portfolio_manager.py` 文件。

当前 `curr_situation`（第24行）只含4个报告，用于记忆检索（第28行）。需要：
1. 提取3个新报告
2. 追加到 `curr_situation`
3. 可选择性地在 prompt 中提及 A 股特定风险因子

### 4.7 （推荐）质量门

**文件**: `tradingagents/agents/quality_gate.py`（新建，~200行）

从 astock-wj 移植，建议从"可选"提升为"推荐"：
- 7份报告硬检查（长度、失败标记、缺失数据计数）
- LLM 审查（A-F 评级），指导 Bull/Bear 降低对低质量报告的依赖
- 输出 `data_quality_summary` 到 state

**图编排集成细节**（v2.2 补充）：

1. `AgentState` 新增字段：`data_quality_summary: Annotated[str, "Quality audit report"]`
2. `setup.py` 节点创建（在最后一个分析师之后）：
   ```python
   if "quality_gate" in selected_analysts:
       analyst_nodes["quality_gate"] = create_quality_gate(self.quick_thinking_llm)
   ```
3. `setup.py` 边修改：最后一个分析师的 `Msg Clear` → `"Quality Gate"` → `"Bull Researcher"`
4. `conditional_logic.py` 不需新增方法（Quality Gate 无工具调用，直接输出）
5. `trading_graph.py` 不需新增 ToolNode（Quality Gate 不调用工具）

**注意**：如果 Quality Gate 被跳过，则图编排保持不变（最后一个分析师 → Bull Researcher），需要`setup.py`做 conditional 边连接。

**conditional 边实现策略**（v2.3 补充伪代码）：

`setup.py` 中使用 LangGraph 的 `add_conditional_edges` 实现动态路由：

```python
# 在 setup.py 的边连接循环之后（最后一个分析师 Msg Clear 之后）

def route_after_last_analyst(state):
    """决定是否经过 Quality Gate"""
    if "quality_gate" in state.get("selected_analysts", []):
        return "Quality Gate"
    return "Bull Researcher"

# 最后一个分析师的 Msg Clear → conditional 路由
last_clear_node = f"Msg Clear {last_analyst_type}"
workflow.add_conditional_edges(
    last_clear_node,
    route_after_last_analyst,
    {
        "Quality Gate": "Quality Gate",
        "Bull Researcher": "Bull Researcher"
    }
)

# Quality Gate → Bull Researcher（仅在启用时）
workflow.add_edge("Quality Gate", "Bull Researcher")
```

**关键点**：
- 使用 `add_conditional_edges` 而非硬编码边，避免图编译错误
- `last_analyst_type` 通过动态循环中的 `selected_analysts[-1]` 确定
- 当 `quality_gate` 不在 `selected_analysts` 中时，图结构等价于当前（最后一个分析师 → Bull Researcher）

### 4.8 Reflector / ChromaDB 记忆适配（v1.0 遗漏）

**文件**: `tradingagents/graph/reflection.py`

`_extract_current_situation()` 方法（第53-60行）当前只包含4个报告：

```python
def _extract_current_situation(self, current_state: Dict[str, Any]) -> str:
    curr_market_report = current_state["market_report"]
    curr_sentiment_report = current_state["sentiment_report"]
    curr_news_report = current_state["news_report"]
    curr_fundamentals_report = current_state["fundamentals_report"]
    return f"{curr_market_report}\n\n{curr_sentiment_report}\n\n{curr_news_report}\n\n{curr_fundamentals_report}"
```

必须新增3个报告，否则 ChromaDB 中的历史经验不包含 A 股政策/游资/解禁信息：

```python
def _extract_current_situation(self, current_state: Dict[str, Any]) -> str:
    curr_market_report = current_state["market_report"]
    curr_sentiment_report = current_state["sentiment_report"]
    curr_news_report = current_state["news_report"]
    curr_fundamentals_report = current_state["fundamentals_report"]
    curr_policy_report = current_state.get("policy_report", "")
    curr_hot_money_report = current_state.get("hot_money_report", "")
    curr_lockup_report = current_state.get("lockup_report", "")
    return f"{curr_market_report}\n\n{curr_sentiment_report}\n\n{curr_news_report}\n\n{curr_fundamentals_report}\n\n{curr_policy_report}\n\n{curr_hot_money_report}\n\n{curr_lockup_report}"
```

此修改确保所有5个反射方法（`reflect_bull_researcher`、`reflect_bear_researcher`、`reflect_trader`、`reflect_invest_judge`、`reflect_risk_manager`）都将新报告内容纳入情境记忆。

### 4.9 Web 层分析师 ID 兼容性适配（v2.2 新增 — 严重问题 #22/#23）

#### 4.9.1 `web/utils/analysis_runner.py` 核心入口分析

**文件**: `web/utils/analysis_runner.py`

此文件是 Web/CLI 调用分析流程的**核心入口**，`run_stock_analysis()` 函数（第100行）负责：
1. 接收 `analysts` 参数（第100行）
2. 传递给 `TradingAgentsGraph(analysts, config=config)`（第460行）

**关键发现**：`analysis_runner.py` **不会**硬编码分析师列表。它在调用链中充当被动传递者：
```
app/worker.py（旧版ID "Bull Analyst"）→ analysis_runner.py（透传）→ TradingAgentsGraph（新版ID "market"）
```

**问题不在** `analysis_runner.py` 本身，而在上游调用者 `app/worker.py:83` 的默认值格式不兼容。`analysis_runner.py` 不需要修改。

#### 4.9.2 `app/worker.py:83` 分析师 ID 兼容性修复

**严重性：高** —— 当前第83行代码与系统实际使用的分析师 ID 格式**完全不兼容**：

```python
# 当前（错误）：旧版英文分析师名称
analysts = params.get("analysts", ["Bull Analyst", "Bear Analyst", "Research Manager"])

# 修正后：新版 ID 格式
analysts = params.get("analysts", ["market", "fundamentals", "news", "social"])
```

**修复方案**（必须提前到 Phase 2，不可推迟到 Phase 7）：

```python
# worker.py 第83行修改为
analysts = params.get("analysts", ["market", "fundamentals", "news", "social"])
```

如果不修复此问题：
- 通过 Web API 发起的分析任务会使用不匹配的分析师名称
- `setup_graph()` 中 `if analyst_type in selected_analysts` 检查全部失败
- **所有分析师节点被静默跳过** — 分析结果为空

**配合修改**：`TradingAgentsGraph.__init__` 可增加分析师名称兼容性日志：

```python
valid_analysts = ["market", "social", "news", "fundamentals", "policy", "hot_money", "lockup"]
if any(a not in valid_analysts for a in selected_analysts):
    logger.warning(f"⚠️ 检测到非标准分析师名称: {selected_analysts}")
```

#### 4.9.3 Streamlit 前端分析表单适配

**文件**: `web/components/analysis_form.py`

当前代码（第184-192行）**硬编码**了4个分析师选项，必须新增3个：

```python
# 在第177-181行之后新增3个 A 股专用选项
# A 股专用：仅在 market_type == "A股" 时显示
if market_type == "A股":
    with st.columns(2)[0]:
        policy_analyst = st.checkbox(
            "🏛️ 政策分析师",
            value='policy' in cached_analysts,
            help="分析宏观政策、产业政策、监管环境对股票的影响"
        )
        hot_money_analyst = st.checkbox(
            "💰 游资追踪师",
            value='hot_money' in cached_analysts,
            help="追踪龙虎榜、北向资金、主力资金流向"
        )
    with st.columns(2)[1]:
        lockup_analyst = st.checkbox(
            "🔓 解禁监控师",
            value='lockup' in cached_analysts,
            help="监控限售解禁、大股东减持风险"
        )
else:
    policy_analyst = False
    hot_money_analyst = False
    lockup_analyst = False

# 在收集选中的分析师区域（第184-192行）追加：
if policy_analyst:
    selected_analysts.append(("policy", "政策分析师"))
if hot_money_analyst:
    selected_analysts.append(("hot_money", "游资追踪师"))
if lockup_analyst:
    selected_analysts.append(("lockup", "解禁监控师"))
```

同时修改默认缓存（第127行）：
```python
cached_analysts = cached_config.get('selected_analysts', ['market', 'fundamentals', 'news', 'social', 'policy', 'hot_money', 'lockup']) if cached_config else ['market', 'fundamentals', 'news', 'social', 'policy', 'hot_money', 'lockup']
```

#### 4.9.4 analysis_runner.py 三处关键修复（v2.3 新增）

**文件**: `web/utils/analysis_runner.py`

v2.2 方案将 `analysis_runner.py` 判定为"透传者，不需修改"，但遗漏了同文件中三处必须修复的位置。**不修复则 Web API 完全不可用、用户看不到新报告**。

##### 修复点 1（P0）：`valid_analysts` 校验列表（第 811-814 行）

```python
# 当前代码——会拒绝包含新分析师ID的请求
def validate_analysis_params(stock_symbol, analysis_date, analysts, research_depth, market_type="A股"):
    ...
    valid_analysts = ['market', 'social', 'news', 'fundamentals']  # ❌ 缺少3个新ID
    invalid_analysts = [a for a in analysts if a not in valid_analysts]
    if invalid_analysts:
        errors.append(f"无效的分析师类型: {', '.join(invalid_analysts)}")
```

**影响**：通过 Streamlit Web UI 发起的任何包含 `policy`/`hot_money`/`lockup` 的分析请求都会被 `validate_analysis_params()` 拒绝，返回 `无效的分析师类型: policy, hot_money, lockup`。**即使 worker.py 和 analysis_form.py 都已修复，此处仍会导致 Web API 完全不可用。**

**修复**：
```python
valid_analysts = ['market', 'social', 'news', 'fundamentals', 'policy', 'hot_money', 'lockup']
```

##### 修复点 2（P1）：`analysis_keys` 格式化列表（第 710-722 行）

```python
# 当前代码——缺少3个新报告字段
analysis_keys = [
    'market_report',
    'fundamentals_report',
    'sentiment_report',
    'news_report',
    'risk_assessment',
    'investment_plan',
    'investment_debate_state',
    'trader_investment_plan',
    'risk_debate_state',
    'final_trade_decision'
]
# ❌ 缺少: policy_report, hot_money_report, lockup_report
```

**影响**：3 个新分析师的报告**不会出现在用户看到的格式化结果中**。即使图执行成功生成了这 3 份报告，Web UI 展示时会静默忽略它们。

**修复**（建议在 `news_report` 之后插入）：
```python
analysis_keys = [
    'market_report',
    'fundamentals_report',
    'sentiment_report',
    'news_report',
    'policy_report',        # 新增
    'hot_money_report',     # 新增
    'lockup_report',        # 新增
    'risk_assessment',
    'investment_plan',
    'investment_debate_state',
    'trader_investment_plan',
    'risk_debate_state',
    'final_trade_decision'
]
```

##### 修复点 3（P2）：`translate_analyst_labels()` 翻译映射（第 36-58 行）

```python
# 当前代码——缺少3个新分析师的中文映射
def translate_analyst_labels(text):
    translations = {
        'Bull Analyst:': '看涨分析师:',
        'Bear Analyst:': '看跌分析师:',
        'Risky Analyst:': '激进风险分析师:',
        'Safe Analyst:': '保守风险分析师:',
        'Neutral Analyst:': '中性风险分析师:',
        'Research Manager:': '研究经理:',
        'Portfolio Manager:': '投资组合经理:',
        'Risk Judge:': '风险管理委员会:',
        'Trader:': '交易员:'
        # ❌ 缺少: Policy Analyst:, Hot_money Analyst:, Lockup Analyst:
    }
```

**影响**：如果下游 Agent 报告文本中引用了新分析师名称（如 `Policy Analyst:`），这些英文名称不会被翻译为中文。影响程度取决于 LLM 是否输出分析师名——如果 prompt 使用中文角色名（如"政策分析师"），可能不被触发。作为防御性编程，应当补全。

**修复**：
```python
'Policy Analyst:': '政策分析师:',
'Hot_money Analyst:': '游资追踪师:',
'Lockup Analyst:': '解禁监控师:',
```

##### 实施归属

| 修复点 | 归属 Phase | 所在 Step | 代码量 |
|--------|:----------:|----------|:------:|
| valid_analysts 列表 | Phase 2 | Step 2.6（新增） | ~1 行 |
| analysis_keys 列表 | Phase 2 | Step 2.6（新增） | ~3 行 |
| translate_analyst_labels | Phase 2 | Step 2.6（新增） | ~3 行 |
| **合计** | | | **~7 行** |

> **注意**：三处修复均在 `analysis_runner.py` 同一文件中，与 worker.py 修复（Step 2.3）同步执行。不修复则 Web API 不可用、用户看不到新报告。

---

## 5. 第四部分：完整文件变更清单（已修正）

### 5.1 新建文件（4个核心 + 1个推荐）

| 文件 | v1.0 预估 | v2.0 修正 | 说明 |
|------|:------:|:------:|------|
| `policy_analyst.py` | ~100 | **~400** | 完整 CN-wj 分析师模式 |
| `hot_money_tracker.py` | ~130 | **~500** | 9个工具，最复杂 |
| `lockup_watcher.py` | ~110 | **~400** | 4个工具 |
| `astock_direct.py` | ~800 | **~1200-1500** | SKILL.md 提取 + 生产级封装 |
| `quality_gate.py` | ~170 | ~200 | 提升为推荐 |
| **合计** | **~1,310** | **~2,700-3,000** | 约 2.3x |

### 5.2 修改现有文件（23个，新增7个遗漏文件）

| 文件 | v1.0 增量 | v2.2 修正 | 关键变更 |
|------|:------:|:------:|------|
| `agent_states.py` | +15 | +15 | 无变化 |
| `agent_utils.py` | +350 | **+500-700** | 8个 @tool（含 insider）+ 市场判断 + 错误处理 + astock_provider 注入 |
| `agents/__init__.py` | +6 | +6 | _EXPORTS 字典 + __all__ 列表 |
| `trading_graph.py` | +50 | **+75** | +ToolNode创建 + 进度映射键名 + _resolve_selected_analysts + _log_state JSON字段 + AStockDirectProvider初始化 |
| `setup.py` | +40 | +40 | 无变化 |
| `conditional_logic.py` | +60 | **+120** | +完整日志记录（参照现有模式） |
| **`propagation.py`** | **遗漏** | **+10** | `create_initial_state()` 新增3字段 + LangGraph 自动默认值说明 |
| **`reflection.py`** | **遗漏** | **+10** | `_extract_current_situation()` 新增3报告 |
| `bull_researcher.py` | +20 | +25 | +3报告提取+注入+日志 |
| `bear_researcher.py` | +20 | +25 | 同上 |
| `aggresive_debator.py` | +15 | +20 | +3报告提取+注入+长度统计 |
| `conservative_debator.py` | +15 | +20 | 同上 |
| `neutral_debator.py` | +15 | +20 | 同上 |
| `trader.py` | +15 | +25 | +3报告 + A 股约束条件注入 |
| `research_manager.py` | 未计 | **+25** | +3报告 + curr_situation 扩展 |
| `risk_manager.py` | 未计 | **+25** | 修正：替代 portfolio_manager |
| `constants/data_sources.py` | +5 | +5 | +ASTOCK_DIRECT 枚举值 + DATA_SOURCE_REGISTRY 注册 |
| `data_source_manager.py` | +10 | **+30** | +ASTOCK_DIRECT 枚举（ChinaDataSource）+ 两处 source_mapping + 硬编码回退（仅 fallback） |
| `providers_config.py` | +10 | +10 | astock_direct 连接参数配置 |
| `china/__init__.py` | +1 | +1 | 无变化 |
| `interface.py` | +20 | **0** | 确认**不需要修改**（Toolkit 直调 AStockDirectProvider） |
| **`app/models/analysis.py`** | **遗漏** | **+1** | `selected_analysts` 默认值新增3个 A 股 ID |
| **`app/worker.py`** | **遗漏** | **+10** | 修正旧版英文分析师名硬编码 **（提至 Phase 2）** + 分析师名称兼容性日志 |
| **`web/components/analysis_form.py`** | **遗漏** | **+30** | 新增3个A股专用分析师选项 + 市场类型动态显示/隐藏 |
| **`tradingagents/graph/signal_processing.py`** | **遗漏** | **+20** | `process_signal()` 的 system prompt 中加入 A 股特色评级词→标准 action 映射（游资介入→买入、政策利好→买入、解禁压力→卖出），不修改 `_extract_simple_decision()` |
| `requirements.txt` | 变化小 | 变化小 | +mootdx |
| **合计** | **~662** | **~1,120-1,340** | 约 1.8x（v2.3：+analysis_runner.py 3处修复 + data_source_manager 两处枚举 + signal_processing system prompt 细化） |

### 5.3 总计

| 维度 | v1.0 预估 | v2.3 修正 |
|------|:------:|:------:|
| 新建代码 | ~1,310 行 | ~2,700-3,000 行 |
| 修改代码 | ~662 行 | ~1,120-1,340 行 |
| **总计** | **~1,970 行** | **~3,820-4,340 行** |
| 涉及文件 | 20 个 | **29 个**（5 新建 + 24 修改） |
| 遗漏文件补充 | — | propagation.py, reflection.py, research_manager.py, risk_manager.py, analysis.py, worker.py, analysis_form.py, signal_processing.py, analysis_runner.py（3处修复）, constants/data_sources.py |

---

## 6. 第五部分：实施顺序与依赖（已修正）

```
Phase 0: 预研与验证（新增）──────────────────────────
│
├── Step 0.1: 测算 7 份报告的 token 消耗
│   └── 4份→7份，Bull/Bear prompt 约增大 56%（非 75%）
│   └── 估算基线（中文约 2 chars/token）：
│       ├── 当前4份报告 ~8000 字 → ~4000 tokens
│       ├── 新增3份报告 ~4500 字 → ~2250 tokens
│       ├── Bull/Bear 系统指令 + 辩论历史 ~3000 tokens
│       └── 总 prompt 约 ~9250 tokens → **最低要求 16K 上下文窗口**
│   └── 8K 窗口模型（如部分小模型）**不可用**；建议最低 DeepSeek-V3/Qwen-Max
│   └── 如果使用 128K+ 模型，prompt 膨胀不是问题
│
├── Step 0.2: 测试 mootdx 安装与 httpx 版本兼容性
│   └── pip install mootdx --no-deps（推荐）
│   └── 验证 langchain-google-genai 是否受影响
│   └── ⚠️ Windows 注意事项：mootdx 依赖 TCP 7709 端口（通达信服务器可达）
│   └── 企业内网/Docker 环境可能需要额外配置防火墙规则
│
├── Step 0.3: 验证 a-stock-data-wj 28个端点可用性
│   └── 逐个测试核心端点（重点：同花顺、百度股市通、东财 datacenter）
│   └── 确认无需 API Key 的端点确实可用
│
├── Step 0.4: 评估 a_stock.py 代码可复用性（新增）
│   └── astock-wj 已有 1992行生产级 `a_stock.py`（与 SKILL.md 对比）
│   └── a_stock.py 优势：已适配为可导入模块、返回 str、有 try/except + 降级
│   └── 决定以 a_stock.py 还是 SKILL.md 为 astock_direct.py 的代码基础
│
Phase 1: 基础设施 ─────────────────────────────────────
│
├── Step 1.1: 创建 astock_direct.py（最大阻塞项，1200-1500行）
│   └── 先实现信号层7个核心端点（3个角色直接依赖）
│   └── 再实现行情层、新闻层、基础数据层（供后续扩展）
│
├── Step 1.2: 注册数据源 + 配置
│   └── data_sources.py, data_source_manager.py, providers_config.py
│   └── **优先在 MongoDB 中注册** astock_direct 数据源条目（type: "astock_direct", priority 最高）
│   └── 硬编码回退列表仅作 fallback
│
├── Step 1.3: 安装依赖 + requirements.txt
│
Phase 2: 工具层 + Web 层兼容性修复 ─────────────────────
│
├── Step 2.1: Toolkit 新增 8个 @tool 方法
│   └── 每个方法含市场判断（非A股返回说明）
│   └── 调用 astock_direct adapter（通过 self.astock_provider）
│   └── 依赖: Phase 1（astock_direct.py 可用）
│
├── Step 2.2: AgentState 新增 6个字段
│
├── Step 2.3: ⚠️ 修复 app/worker.py:83 分析师 ID 硬编码（严重！）
│   └── `["Bull Analyst", "Bear Analyst", "Research Manager"]` → `["market", "fundamentals", "news", "social"]`
│   └── 此修复必须在新增分析师前完成，否则 Web API 任务静默失败
│
├── Step 2.4: app/models/analysis.py:46 selected_analysts 默认值新增3个 ID
│
├── Step 2.5: web/components/analysis_form.py 新增3个A股专用分析师选项
│   └── 根据 market_type 动态显示/隐藏（仅 A 股显示 policy/hot_money/lockup）
│
├── Step 2.6: ⚠️ 修复 analysis_runner.py 三处（严重！见第 4.9.4 节）
│   └── valid_analysts 列表扩展（第811行）—— 否则 Web API 请求被拒绝
│   └── analysis_keys 列表扩展（第710行）—— 否则新报告不出现在结果中
│   └── translate_analyst_labels 映射扩展（第36行）—— 防御性补全
│
Phase 3: Agent 层（分步验证，新增策略）───────────────
│
├── Step 3.1: 先创建 policy_analyst.py（工具最少，~400行）
│   └── 工具: get_stock_news_unified + get_global_news_openai
│   └── 不依赖任何新增 @tool
│
├── Step 3.2: 注册 + 图编排 + 条件逻辑 → 集成验证
│   └── 验证 1 个新角色在图中正常运行
│   └── 确认 tool_call_count、Google/DashScope 兼容工作正常
│
├── Step 3.3: 验证通过后创建 hot_money_tracker.py（~500行）
│   └── 依赖 6 个新增 @tool（需 Phase 2 完成）
│
├── Step 3.4: 创建 lockup_watcher.py（~400行）
│   └── 依赖 2 个新增 @tool（get_insider_transactions_astock + get_lockup_expiry）
│
├── Step 3.5: 注册导出（agents/__init__.py）
│
Phase 4: 图编排 ─────────────────────────────────────
│
├── Step 4.1: conditional_logic.py（3个方法 + 日志）
├── Step 4.2: trading_graph.py（ToolNode + 默认列表 + 进度映射 + 日志状态）
├── Step 4.3: setup.py（节点创建）
├── Step 4.4: propagation.py（初始状态字段）
│
Phase 5: 下游适配 ─────────────────────────────────────
│
├── Step 5.1: Bull/Bear Researcher（+3报告提取 + prompt注入 + curr_situation）
├── Step 5.2: 风险辩论三方（aggresive/conservative/neutral_debator）
├── Step 5.3: Trader（+3报告 + A股约束条件注入）
├── Step 5.4: Research Manager（+3报告 + curr_situation）
├── Step 5.5: Risk Manager（+3报告 + curr_situation）
├── Step 5.6: reflection.py（_extract_current_situation 纳入3报告）
│
Phase 6: 质量门（推荐） ─────────────────────────────
│
├── Step 6.1: 创建 quality_gate.py
├── Step 6.2: 在 setup.py 中插入节点和边（最后一个分析师 → Quality Gate → Bull Researcher）
│
Phase 7: 测试与清理 ─────────────────────────────────
│
├── Step 7.1: 端到端测试（A 股 + 港股 + 美股）
├── Step 7.2: 上下文截断测试（确认 7 份报告不超 token 限制）
├── Step 7.3: 非 A 股市场自动跳过测试（验证 _resolve_selected_analysts + 图编排层跳过）
├── Step 7.4: 数据源降级测试（astock_direct 失败→回退到明确错误信息）
├── Step 7.5: 信号处理测试（signal_processing.py A 股特色评级词识别）
│   └── 验证"游资介入"/"政策利好"/"解禁压力"等评级词被正确提取
├── Step 7.6: Streamlit 前端适配（含 API 端点，分析师选择组件支持新角色）
│   └── `frontend/src/api/analysis.ts` 分析师类型定义扩展
│   └── `frontend/src/types/analysis.ts` selected_analysts 类型扩展
├── Step 7.7: 测试文件更新（30+ 测试文件中的 selected_analysts 引用）
│   └── 搜索 `selected_analysts` 关键字定位所有测试文件
│   └── 新增 A 股场景测试（启用 policy/hot_money/lockup）
│   └── 新增非 A 股场景测试（确认3个角色被跳过）
├── Step 7.8: 评估是否可移除旧依赖（akshare, baostock）
│   └── ⚠️ 不要直接移除！akshare 仍被港股数据路径使用
│   └── 逐一确认旧依赖的引用点后再决定
├── Step 7.9: _log_state JSON 完整性验证（确认7份报告均写入日志文件）
```

---

## 7. 第六部分：风险评估（已修正）

| 风险 | v1.0 评级 | v2.0 评级 | 修正说明 | 缓解措施 |
|------|:------:|:------:|------|------|
| **分析师实现复杂度被低估** | 未提及 | **高** | v1.0 完全未识别此风险 | 按 CN-wj 完整模式重写（400-500行/个），Phase 3 分步验证 |
| **SKILL.md 代码非生产级** | 未提及 | **高** | v1.0 假设直接提取即用 | 大量适配工作（错误处理、重试、日志、类型注解），astock_direct.py 实际 1200-1500 行 |
| **Prompt 膨胀 → 上下文溢出** | 未提及 | **中** | 4→7份报告，curr_situation 约增大 ~56% | Phase 0 Step 0.1 量化估算；最低 16K 上下文窗口；若超限考虑摘要/截断 |
| **非 A 股市场3个分析师行为** | 未提及 | **中** | 港股/美股分析时 A 股工具返回空数据 | 图编排层动态决定 selected_analysts（主防线）+ 工具层兜底返回"仅适用A股" |
| **信号层工具无降级链** | 未提及 | **中** | 7个信号工具仅有 astock_direct 供应商 | astock_direct 失败时返回明确错误信息而非崩溃 |
| **ChromaDB 记忆与 A 股报告不匹配** | 未提及 | **中** | Reflector 不感知新报告 | 修改 reflection.py 的 _extract_current_situation() |
| **默认分析师列表分散在3处** | 未提及 | **中** | analysis.py / setup.py / trading_graph.py 默认值需同步修改 | 实施时统一修改3处；Phase 7 Web 适配一并处理 |
| **`app/worker.py` 旧版英文分析师名硬编码** | 未提及 | **中** | `["Bull Analyst", "Bear Analyst", "Research Manager"]` 与新 ID 系统不兼容 | Phase 7 统一修正为 `selected_analysts` ID 格式 |
| **Web/前端层未适配** | 未提及 | **中** | 分析师选择 UI、进度显示、报告展示 | Phase 7 增加 Web 适配任务 |
| **mootdx httpx 版本冲突** | 低 | **中** | CN-wj 使用 langchain-google-genai 依赖 httpx | `pip install mootdx --no-deps`；Phase 0 预验兼容性 |
| 数据源 API 变动/被封 | 中 | 中 | 评级合理 | 保留降级链 |
| astock-wj 同步 vs CN-wj 异步 | 低 | 低 | 评级合理 | asyncio.to_thread() 包装或保持同步 |
| 分析师命名惯例 | 低 | 低 | 评级合理 | Hot_money 下划线不影响功能 |
| 新报告为空时下游行为 | 低 | 低 | 评级合理 | .get(key, "") 模式 |
| 工具数量膨胀 | 低 | 低 | 评级合理 | tool_call_count 限制 |

---

## 附录A：分析师节点名称对照表（不变）

| 内部key | 图节点名 | 工具节点名 | 消息清除节点 | 中文显示名 |
|---------|---------|-----------|-------------|-----------|
| `market` | `Market Analyst` | `tools_market` | `Msg Clear Market` | 市场分析师 |
| `social` | `Social Analyst` | `tools_social` | `Msg Clear Social` | 社交媒体分析师 |
| `news` | `News Analyst` | `tools_news` | `Msg Clear News` | 新闻分析师 |
| `fundamentals` | `Fundamentals Analyst` | `tools_fundamentals` | `Msg Clear Fundamentals` | 基本面分析师 |
| `policy` | `Policy Analyst` | `tools_policy` | `Msg Clear Policy` | 政策分析师 |
| `hot_money` | `Hot_money Analyst` | `tools_hot_money` | `Msg Clear Hot_money` | 游资追踪师 |
| `lockup` | `Lockup Analyst` | `tools_lockup` | `Msg Clear Lockup` | 解禁监控师 |

## 附录B：3个新角色工具需求矩阵（不变）

| 工具方法 | 政策分析师 | 游资追踪 | 解禁监控 | 数据源 |
|---------|:--------:|:------:|:------:|--------|
| `get_stock_news_unified` | ✅ | ✅ | ✅ | 已有 |
| `get_global_news_openai` | ✅ | | | 已有 |
| `get_stock_market_data_unified` | | ✅ | | 已有 |
| `get_stock_fundamentals_unified` | | | ✅ | 已有 |
| `get_insider_transactions_astock` | | ✅ | ✅ | **新增** |
| `get_hot_stocks` | | ✅ | | **新增** |
| `get_northbound_flow` | | ✅ | | **新增** |
| `get_concept_blocks` | | ✅ | | **新增** |
| `get_fund_flow` | | ✅ | | **新增** |
| `get_dragon_tiger_board` | | ✅ | | **新增** |
| `get_industry_comparison` | | ✅ | | **新增** |
| `get_lockup_expiry` | | | ✅ | **新增** |

## 附录C：v1.0 已知错误汇总

| # | v1.0 错误描述 | 严重度 | 修正 |
|---|-------------|:------:|------|
| 1 | `build_instrument_context()` 标为"需新增" | 严重 | 已存在于 `instrument_utils.py`，直接导入 |
| 2 | 分析师预估 100-130 行/个 | 严重 | 修正为 400-500 行/个 |
| 3 | `propagation.py` 遗漏 | 严重 | 新增 create_initial_state() 修改 |
| 4 | `__init__.py` 只提 `__all__` | 严重 | 需同时修改 `_EXPORTS` 字典 |
| 5 | tool_call_count 递增位置不明确 | 严重 | 明确在分析师节点内部递增 |
| 6 | 下游适配提到 portfolio_manager.py | 中等 | 修正为 risk_manager.py |
| 7 | conditional_logic 无日志 | 中等 | 补充完整日志模式 |
| 8 | `reflection.py` 适配遗漏 | 中等 | 新增 _extract_current_situation() 修改 |
| 9 | SKILL.md 代码量低估 | 高（风险） | 1200-1500 行 |
| 10 | 未评估 prompt token 膨胀风险 | 中（风险） | Phase 0 预研测算 |
| 11 | 非 A 股市场兼容性未提及 | 中（风险） | 工具层市场判断 |
| 12 | `get_insider_transactions` 命名不一致 | 中等 | 统一为 `get_insider_transactions_astock` |
| 13 | `_log_state` 风险字段名差异 | 低 | 使用 CN-wj 的 risky/safe/neutral 字段名 |
| 14 | `get_global_news_openai` 对政策分析不够 | 中等 | 建议后续替换为 CLS + 东财全球资讯 |

---

> **文档版本**: v2.3（第四次修正版）  
> **修正基于**: 六份评估报告的综合修正  
>  - spec.md（9严重+7中等）  
>  - migration-plan-review.md（8问题+5风险补充）  
>  - migration-plan-assessment-report.md（8项新遗漏）  
>  - migration-plan-evaluation-report.md（10项问题）  
>  - migration-plan-evaluation-report-v2.2.md（12处核验，4处建议修正）  
>  - migration-plan-v22-assessment-report.md（3严重+5中等遗漏）  
> **验证方式**: 逐条对照 CN-wj 真实代码（30+ 文件）  
> **状态**: v2.3 已修正，待评审确认后进入 Phase 0 实施