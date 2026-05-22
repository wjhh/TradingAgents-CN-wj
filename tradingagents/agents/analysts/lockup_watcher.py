"""
解禁监控分析师 - A股专用
追踪限售股解禁计划、大股东减持动态和股权结构变化
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage

from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.llm_clients import create_llm_client


def _get_company_name_for_lockup(ticker: str, market_info: dict) -> str:
    """为解禁监控师获取公司名称"""
    try:
        if market_info['is_china']:
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)
            if stock_info and "股票名称:" in stock_info:
                return stock_info.split("股票名称:")[1].split("\n")[0].strip()
            else:
                try:
                    from tradingagents.dataflows.data_source_manager import get_china_stock_info_unified as get_info_dict
                    info_dict = get_info_dict(ticker)
                    if info_dict and info_dict.get('name'):
                        return info_dict['name']
                except Exception:
                    pass
                return f"股票代码{ticker}"
        elif market_info['is_hk']:
            try:
                from tradingagents.dataflows.providers.hk.improved_hk import get_hk_company_name_improved
                return get_hk_company_name_improved(ticker)
            except Exception:
                return f"港股{ticker.replace('.HK', '').replace('.hk', '')}"
        elif market_info['is_us']:
            names = {'AAPL': '苹果公司', 'TSLA': '特斯拉', 'NVDA': '英伟达',
                     'MSFT': '微软', 'GOOGL': '谷歌', 'AMZN': '亚马逊',
                     'META': 'Meta', 'NFLX': '奈飞'}
            return names.get(ticker.upper(), f"美股{ticker}")
        return f"股票{ticker}"
    except Exception as e:
        logger.error(f"❌ [解禁监控] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_lockup_watcher(llm, toolkit):
    @log_analyst_module("lockup")
    def lockup_watcher_node(state):
        logger.debug(f"🔓 [DEBUG] ===== 解禁监控师节点开始 =====")

        messages = state.get("messages", [])
        tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))
        tool_call_count = state.get("lockup_tool_call_count", 0)
        max_tool_calls = 3

        if tool_message_count > tool_call_count:
            tool_call_count = tool_message_count
            logger.info(f"🔧 [工具调用计数] 更新计数器: {tool_call_count}")

        logger.info(f"🔧 [工具调用计数] 当前: {tool_call_count}/{max_tool_calls}")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name_for_lockup(ticker, market_info)

        tools = [
            toolkit.get_insider_transactions_astock,
            toolkit.get_stock_news_unified,
            toolkit.get_stock_fundamentals_unified,
            toolkit.get_lockup_expiry,
        ]

        tool_names = [tool.name for tool in tools]

        system_message = (
            "你是一位专注于 A 股市场的解禁与减持监控分析师。你的核心任务是追踪目标公司的限售股解禁计划、大股东减持动态和股权结构变化，评估供给端压力对股价的影响。"
            "\n\n⚠️ A 股解禁/减持分析框架："
            "\n- **限售股类型**：首发原股东限售(IPO 后 1-3 年)、定增限售(6-18 个月)、股权激励限售、战略配售限售。不同类型的减持意愿和节奏差异很大。"
            "\n- **解禁规模评估**：解禁市值占流通市值比例 >20% 为重大解禁压力；<5% 影响有限。结合当前股价和解禁成本(原始获取价)判断减持动力。"
            "\n- **减持新规约束**：大股东(持股 5%+)每 90 天通过集中竞价减持不超过总股本 1%、大宗交易不超过 2%；董监高每年减持不超过持股 25%。"
            "\n- **减持预披露**：大股东/董监高减持需提前 15 个交易日披露减持计划(时间窗口、数量、方式)。已披露的减持计划是确定性利空。"
            "\n- **减持动力评估**：当前股价 vs 解禁成本的溢价倍数越高，减持动力越强。若股价低于解禁成本，减持概率大幅降低。"
            "\n- **历史减持行为**：大股东过往减持频率和规模反映其套现意愿。频繁减持的大股东在新一轮解禁时减持概率更高。"
            "\n\n分析方法："
            "\n1. 调用 get_insider_transactions_astock 获取股东/内部人交易记录和持股变化"
            "\n2. 调用 get_stock_fundamentals_unified 获取公司股本结构和大股东持股比例"
            "\n3. 调用 get_stock_news_unified 搜索解禁、减持计划、股东变动相关公告和新闻"
            "\n4. 综合评估未来 1-3 个月的减持压力等级"
            "\n\n撰写详细的解禁/减持风险评估报告，给出减持压力总体评级（重大压力/中等压力/轻微压力/无明显压力），并估算潜在减持规模和时间窗口。报告末尾附 Markdown 表格列出关键解禁/减持事件、规模和影响评估。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近 6 个月内部人/大股东交易记录（增持/减持/无变动）"
            "\n2. 前十大股东持股变化趋势"
            "\n3. 解禁/减持相关新闻及公告"
            "\n4. 减持压力评级（重大压力/中等压力/轻微压力/无明显压力）"
            "\n5. 未来 3 个月潜在减持风险评估"
            "\n\n请使用中文撰写报告。"
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a helpful AI assistant, collaborating with other assistants."
                " Use the provided tools to progress towards answering the question."
                " If you are unable to fully answer, that's OK; another assistant with different tools"
                " will help where you left off. Execute what you can to make progress."
                " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                " You have access to the following tools: {tool_names}.\n{system_message}"
                "For your reference, the current date is {current_date}. {instrument_context}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        # Handle DashScope/Qwen compatibility
        fresh_llm = llm
        try:
            if hasattr(llm, 'model_name'):
                model_lower = str(llm.model_name).lower()
                if any(kw in model_lower for kw in ('qwen', 'dashscope')):
                    fresh_llm = create_llm_client(
                        provider="dashscope", model=llm.model_name, temperature=0.3
                    )
                    logger.info(f"🔄 [解禁监控] DashScope/Qwen检测，创建全新LLM实例")
        except Exception as e:
            logger.warning(f"⚠️ [解禁监控] LLM检测失败: {e}")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.info(f"📊 [解禁监控] ✅ 工具绑定成功，绑定了 {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"📊 [解禁监控] ❌ 工具绑定失败: {e}")
            raise e

        logger.info(f"📊 [解禁监控] 开始调用LLM...")
        result = chain.invoke({"messages": state["messages"]})
        logger.info(f"📊 [解禁监控] LLM调用完成")

        if hasattr(result, 'content') and result.content:
            logger.info(f"🤖 [解禁监控] - 内容长度: {len(result.content)}")
        if hasattr(result, 'tool_calls'):
            logger.info(f"📊 [解禁监控] - tool_calls数量: {len(result.tool_calls)}")

        # Google model handling
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            logger.info(f"📊 [解禁监控] 检测到Google模型")

            specific_requirements = (
                "请从以下维度分析限售解禁和减持风险：\n"
                "1. 近期解禁：未来1-3个月的解禁数量、解禁市值、占总股本比例\n"
                "2. 解禁类型：首发解禁/定增解禁/股权激励解禁（风险依次降低）\n"
                "3. 股东减持：近期大股东/高管减持公告、减持理由、减持比例\n"
                "4. 历史参考：同类股票解禁前后的股价表现\n"
                "5. 减持预判：结合当前估值水平，判断解禁后减持意愿\n\n"
                "输出格式：每个维度单独成段，末尾给出解禁风险评级（高风险/中风险/低风险，附带置信度）。"
            )

            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="解禁减持风险分析",
                specific_requirements=specific_requirements,
            )

            report, messages_out = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=fresh_llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="解禁监控师"
            )

            return {"lockup_report": report}
        else:
            current_tool_calls = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0

            if current_tool_calls > 0:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)

                if has_tool_result:
                    logger.warning(f"⚠️ [强制生成报告] 工具已返回数据，强制生成报告")
                    force_system_prompt = (
                        f"你是专业的A股解禁/减持监控分析师。"
                        f"你已经收到了股票 {company_name}（代码：{ticker}）的解禁和股东数据。"
                        f"🚨 现在你必须基于这些数据生成完整的解禁/减持风险评估报告！🚨\n\n"
                        f"报告必须包含：\n"
                        f"1. 解禁日历分析\n2. 解禁类型分类\n3. 股东减持动态\n"
                        f"4. 历史解禁参考\n5. 减持压力评级（重大压力/中等压力/轻微压力/无明显压力）\n\n"
                        f"使用中文撰写报告。"
                    )
                    force_prompt = ChatPromptTemplate.from_messages([
                        ("system", force_system_prompt),
                        MessagesPlaceholder(variable_name="messages"),
                    ])
                    force_chain = force_prompt | fresh_llm
                    force_result = force_chain.invoke({"messages": messages})
                    report = str(force_result.content) if hasattr(force_result, 'content') else "解禁分析完成"
                    logger.info(f"✅ [强制生成报告] 报告长度: {len(report)}字符")
                    return {
                        "lockup_report": report,
                        "messages": [force_result],
                        "lockup_tool_call_count": tool_call_count
                    }
                elif tool_call_count >= max_tool_calls:
                    fallback_report = f"解禁减持分析（{ticker}）\n\n达到最大工具调用次数限制，使用简化模式。"
                    return {
                        "messages": [result],
                        "lockup_report": fallback_report,
                        "lockup_tool_call_count": tool_call_count
                    }
                else:
                    logger.info(f"✅ [正常流程] LLM调用工具，等待执行")
                    return {"messages": [result]}
            else:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)
                has_analysis_content = (
                    hasattr(result, 'content') and result.content
                    and len(str(result.content)) > 300
                )

                if has_tool_result or has_analysis_content:
                    report = str(result.content) if hasattr(result, 'content') else "解禁分析完成"
                    return {
                        "lockup_report": report,
                        "messages": [result],
                        "lockup_tool_call_count": tool_call_count
                    }

                # Force tool call
                logger.info(f"🔧 [决策] 执行强制工具调用")
                try:
                    for tool in tools:
                        tname = getattr(tool, 'name', None) or getattr(tool, '__name__', '')
                        if tname == 'get_lockup_expiry':
                            combined_data = tool.invoke({
                                'ticker': ticker, 'curr_date': current_date
                            })
                            logger.info(f"✅ 强制获取解禁数据成功，长度: {len(combined_data)}")
                            break
                    else:
                        combined_data = "解禁数据工具不可用"
                except Exception as e:
                    combined_data = f"解禁数据获取失败: {e}"

                analysis_prompt = (
                    f"基于以下数据，对{company_name}（{ticker}）进行解禁/减持风险分析：\n\n{combined_data}\n\n"
                    f"请分析解禁日历、减持压力并给出风险评级（重大压力/中等压力/轻微压力/无明显压力）。使用中文。"
                )

                try:
                    ap = ChatPromptTemplate.from_messages([
                        ("system", "你是专业的A股解禁监控分析师。"),
                        ("human", "{analysis_request}")
                    ])
                    ac = ap | fresh_llm
                    ar = ac.invoke({"analysis_request": analysis_prompt})
                    report = ar.content if hasattr(ar, 'content') else str(ar)
                except Exception as e:
                    report = f"解禁分析失败：{str(e)}"

                return {
                    "lockup_report": report,
                    "lockup_tool_call_count": tool_call_count
                }

        return {
            "messages": [result],
            "lockup_report": result.content if hasattr(result, 'content') else str(result),
            "lockup_tool_call_count": tool_call_count
        }

    return lockup_watcher_node