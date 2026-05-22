"""
游资追踪分析师 - A股专用
分析资金流向、成交量异动、主力动向和龙虎榜信号
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage

from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.llm_clients import create_llm_client


def _get_company_name_for_hot_money(ticker: str, market_info: dict) -> str:
    """为游资追踪师获取公司名称"""
    try:
        if market_info['is_china']:
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)
            if stock_info and "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                return company_name
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
        logger.error(f"❌ [游资追踪] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_hot_money_tracker(llm, toolkit):
    @log_analyst_module("hot_money")
    def hot_money_tracker_node(state):
        logger.debug(f"💰 [DEBUG] ===== 游资追踪师节点开始 =====")

        messages = state.get("messages", [])
        tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))
        tool_call_count = state.get("hot_money_tool_call_count", 0)
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
        company_name = _get_company_name_for_hot_money(ticker, market_info)

        tools = [
            toolkit.get_stock_market_data_unified,
            toolkit.get_stock_news_unified,
            toolkit.get_stock_fundamentals_unified,
            toolkit.get_insider_transactions_astock,
            toolkit.get_hot_stocks,
            toolkit.get_northbound_flow,
            toolkit.get_concept_blocks,
            toolkit.get_fund_flow,
            toolkit.get_dragon_tiger_board,
            toolkit.get_industry_comparison,
        ]

        tool_names = [tool.name for tool in tools]

        system_message = (
            "你是一位专注于 A 股市场的游资与资金流向追踪分析师。你的核心任务是通过分析成交量异动、股东变化和市场新闻，追踪主力资金和游资的动向，判断短期资金博弈格局。"
            "\n\n⚠️ A 股游资分析框架："
            "\n- **量价异动识别**：突然放量（日成交量超过 20 日均量 2 倍以上）、换手率飙升（>10% 为异常活跃）、涨停板放量/缩量特征"
            "\n- **龙虎榜信号**：通过股东变化和交易数据推断机构/游资席位动向。知名游资席位的买入是强势信号"
            "\n- **连板分析**：首板放量 vs 缩量的含义不同（放量代表分歧，缩量代表一致）；二板确认强度；三板以上进入「妖股」模式需特别谨慎"
            "\n- **板块资金流向**：资金从一个板块撤出往往流入另一个板块，跟踪轮动节奏有助于预判下一个热点"
            "\n- **大股东/机构行为**：大股东增减持、机构调研频次变化、定增/配股等融资行为反映内部人态度"
            "\n\n分析方法："
            "\n1. 先调用 get_stock_market_data_unified 获取近期 K 线和成交量数据，识别量价异动"
            "\n2. 调用 get_insider_transactions_astock 获取股东/内部人交易记录，判断主力动向"
            "\n3. 调用 get_stock_news_unified 搜索游资、龙虎榜、主力资金相关新闻"
            "\n4. 调用 get_hot_stocks 获取当日强势股及题材归因（同花顺编辑部人工标注），识别热点板块轮动"
            "\n5. 调用 get_northbound_flow 获取北向资金（沪深股通）实时分钟级流向，判断外资态度"
            "\n6. 综合判断当前资金博弈格局：主力吸筹 / 主力出货 / 游资接力 / 散户主导"
            "\n\n撰写详细的资金面分析报告，给出资金面总体判断（主力流入/主力流出/资金博弈/无明显信号）和短期操作建议。报告末尾附 Markdown 表格汇总量价信号、资金动向和结论。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近 5 日成交量变化趋势（放量/缩量/平稳）"
            "\n2. 当日北向资金净流入金额（沪股通 + 深股通）"
            "\n3. 个股主力资金净流入（超大单 + 大单）"
            "\n4. 所属概念板块及当日板块涨幅"
            "\n5. 当日是否上榜热门股及题材归因"
            "\n6. 资金面总体判断"
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
                    logger.info(f"🔄 [游资追踪] DashScope/Qwen检测，创建全新LLM实例")
        except Exception as e:
            logger.warning(f"⚠️ [游资追踪] LLM检测失败: {e}")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.info(f"📊 [游资追踪] ✅ 工具绑定成功，绑定了 {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"📊 [游资追踪] ❌ 工具绑定失败: {e}")
            raise e

        logger.info(f"📊 [游资追踪] 开始调用LLM...")
        result = chain.invoke({"messages": state["messages"]})
        logger.info(f"📊 [游资追踪] LLM调用完成")

        if hasattr(result, 'content') and result.content:
            logger.info(f"🤖 [游资追踪] - 内容长度: {len(result.content)}")
        if hasattr(result, 'tool_calls'):
            logger.info(f"📊 [游资追踪] - tool_calls数量: {len(result.tool_calls)}")

        # Google model handling
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            logger.info(f"📊 [游资追踪] 检测到Google模型")

            specific_requirements = (
                "请从以下维度分析游资和资金流向：\n"
                "1. 龙虎榜分析：近期上榜的营业部席位、买入/卖出金额、净买入排名\n"
                "2. 北向资金：沪/深股通净流入流出、持仓变化趋势\n"
                "3. 主力资金：超大单/大单净流入流出、主力持仓变化\n"
                "4. 概念板块：所属概念板块的资金关注度、板块整体资金流向\n"
                "5. 行业对比：同行业资金流入流出排名、相对强弱\n\n"
                "输出格式：每个维度单独成段，末尾给出资金面综合评级（积极/中性/消极，附带置信度）。"
            )

            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="游资资金流分析",
                specific_requirements=specific_requirements,
            )

            report, messages_out = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=fresh_llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="游资追踪师"
            )

            return {"hot_money_report": report}
        else:
            current_tool_calls = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0

            if current_tool_calls > 0:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)

                if has_tool_result:
                    logger.warning(f"⚠️ [强制生成报告] 工具已返回数据，强制生成报告")
                    force_system_prompt = (
                        f"你是专业的A股游资追踪分析师。"
                        f"你已经收到了股票 {company_name}（代码：{ticker}）的资金流和数据。"
                        f"🚨 现在你必须基于这些数据生成完整的资金面分析报告！🚨\n\n"
                        f"报告必须包含：\n"
                        f"1. 量价异动分析\n2. 龙虎榜信号分析\n3. 北向资金分析\n"
                        f"4. 主力资金分析\n5. 概念板块分析\n6. 资金面综合评级（积极/中性/消极）\n\n"
                        f"使用中文撰写报告。"
                    )
                    force_prompt = ChatPromptTemplate.from_messages([
                        ("system", force_system_prompt),
                        MessagesPlaceholder(variable_name="messages"),
                    ])
                    force_chain = force_prompt | fresh_llm
                    force_result = force_chain.invoke({"messages": messages})
                    report = str(force_result.content) if hasattr(force_result, 'content') else "资金面分析完成"
                    logger.info(f"✅ [强制生成报告] 报告长度: {len(report)}字符")
                    return {
                        "hot_money_report": report,
                        "messages": [force_result],
                        "hot_money_tool_call_count": tool_call_count
                    }
                elif tool_call_count >= max_tool_calls:
                    fallback_report = f"资金面分析（{ticker}）\n\n达到最大工具调用次数限制，使用简化模式。"
                    return {
                        "messages": [result],
                        "hot_money_report": fallback_report,
                        "hot_money_tool_call_count": tool_call_count
                    }
                else:
                    logger.info(f"✅ [正常流程] LLM调用工具，等待执行")
                    return {"messages": [result]}
            else:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)
                has_analysis_content = (
                    hasattr(result, 'content') and result.content
                    and len(str(result.content)) > 500
                )

                if has_tool_result or has_analysis_content:
                    report = str(result.content) if hasattr(result, 'content') else "资金面分析完成"
                    return {
                        "hot_money_report": report,
                        "messages": [result],
                        "hot_money_tool_call_count": tool_call_count
                    }

                # Force tool call — call market data as minimum
                logger.info(f"🔧 [决策] 执行强制工具调用")
                try:
                    for tool in tools:
                        tname = getattr(tool, 'name', None) or getattr(tool, '__name__', '')
                        if tname == 'get_stock_market_data_unified':
                            combined_data = tool.invoke({
                                'ticker': ticker, 'curr_date': current_date
                            })
                            logger.info(f"✅ 强制获取市场数据成功，长度: {len(combined_data)}")
                            break
                    else:
                        combined_data = "市场数据工具不可用"
                except Exception as e:
                    combined_data = f"市场数据获取失败: {e}"

                analysis_prompt = (
                    f"基于以下数据，对{company_name}（{ticker}）进行资金面分析：\n\n{combined_data}\n\n"
                    f"请分析成交量异动、资金流向、概念板块归属，给出资金面综合评级（积极/中性/消极）。使用中文。"
                )

                try:
                    ap = ChatPromptTemplate.from_messages([
                        ("system", "你是专业的A股游资追踪分析师。"),
                        ("human", "{analysis_request}")
                    ])
                    ac = ap | fresh_llm
                    ar = ac.invoke({"analysis_request": analysis_prompt})
                    report = ar.content if hasattr(ar, 'content') else str(ar)
                except Exception as e:
                    report = f"资金面分析失败：{str(e)}"

                return {
                    "hot_money_report": report,
                    "hot_money_tool_call_count": tool_call_count
                }

        return {
            "messages": [result],
            "hot_money_report": result.content if hasattr(result, 'content') else str(result),
            "hot_money_tool_call_count": tool_call_count
        }

    return hot_money_tracker_node