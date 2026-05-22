"""
政策分析师 - A股专用
追踪宏观政策、产业政策、监管环境对股票的影响
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage

from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
from tradingagents.agents.utils.instrument_utils import build_instrument_context
from tradingagents.llm_clients import create_llm_client


def _get_company_name_for_policy(ticker: str, market_info: dict) -> str:
    """为政策分析师获取公司名称"""
    try:
        if market_info['is_china']:
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)
            if stock_info and "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.info(f"✅ [政策分析师] 成功获取中国股票名称: {ticker} -> {company_name}")
                return company_name
            else:
                try:
                    from tradingagents.dataflows.data_source_manager import get_china_stock_info_unified as get_info_dict
                    info_dict = get_info_dict(ticker)
                    if info_dict and info_dict.get('name'):
                        company_name = info_dict['name']
                        logger.info(f"✅ [政策分析师] 降级方案成功获取股票名称: {ticker} -> {company_name}")
                        return company_name
                except Exception as e:
                    logger.error(f"❌ [政策分析师] 降级方案也失败: {e}")
                return f"股票代码{ticker}"
        elif market_info['is_hk']:
            try:
                from tradingagents.dataflows.providers.hk.improved_hk import get_hk_company_name_improved
                return get_hk_company_name_improved(ticker)
            except Exception:
                clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                return f"港股{clean_ticker}"
        elif market_info['is_us']:
            us_stock_names = {
                'AAPL': '苹果公司', 'TSLA': '特斯拉', 'NVDA': '英伟达',
                'MSFT': '微软', 'GOOGL': '谷歌', 'AMZN': '亚马逊',
                'META': 'Meta', 'NFLX': '奈飞'
            }
            return us_stock_names.get(ticker.upper(), f"美股{ticker}")
        else:
            return f"股票{ticker}"
    except Exception as e:
        logger.error(f"❌ [政策分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_policy_analyst(llm, toolkit):
    @log_analyst_module("policy")
    def policy_analyst_node(state):
        logger.debug(f"🏛️ [DEBUG] ===== 政策分析师节点开始 =====")

        messages = state.get("messages", [])
        tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))
        tool_call_count = state.get("policy_tool_call_count", 0)
        max_tool_calls = 3

        if tool_message_count > tool_call_count:
            tool_call_count = tool_message_count
            logger.info(f"🔧 [工具调用计数] 检测到新的工具结果，更新计数器: {tool_call_count}")

        logger.info(f"🔧 [工具调用计数] 当前工具调用次数: {tool_call_count}/{max_tool_calls}")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(ticker)
        company_name = _get_company_name_for_policy(ticker, market_info)

        tools = [
            toolkit.get_stock_news_unified,
            toolkit.get_global_news_openai,
        ]

        tool_names = [tool.name for tool in tools]

        system_message = (
            "你是一位专注于 A 股市场的政策分析师。你的核心任务是追踪和解读影响目标公司及所在行业的政策动态，评估政策对股价的潜在影响方向和力度。"
            "\n\nA 股是全球最典型的「政策市」，政策分析是投资决策中权重最高的因子之一。"
            "\n\n⚠️ 政策分析框架："
            "\n- **宏观政策层**：货币政策（降准/降息/MLF/LPR 调整）、财政政策（专项债/减税）、汇率政策（人民币升贬值对出口/进口行业的影响）"
            "\n- **监管政策层**：证监会（IPO 节奏/再融资/减持新规/退市制度）、银保监会（信贷政策）、发改委（产业审批）"
            "\n- **产业政策层**：国务院/部委发布的行业扶持或限制政策（如「新质生产力」、半导体自主可控、新能源补贴、房地产调控、平台经济监管）"
            "\n- **地方政策层**：地方政府出台的区域性扶持政策（如自贸区、特区优惠、地方产业基金）"
            "\n- **国际政策层**：中美关系、出口管制、关税变动、国际制裁等对特定行业的传导效应"
            "\n\n分析方法："
            "\n1. 识别近期发布的与目标公司直接或间接相关的政策"
            "\n2. 评估政策的力度级别：指导意见（弱）< 部委通知（中）< 国务院文件（强）< 法律法规（最强）"
            "\n3. 判断政策的影响时间窗口：短期脉冲（1-2 周）vs 中期趋势（1-3 月）vs 长期结构性（半年以上）"
            "\n4. 分析政策的受益/受损逻辑链：政策 → 行业影响 → 公司业务映射 → 财务影响估算"
            "\n\n撰写详细的政策分析报告，明确给出政策面对该公司的总体评级（重大利好/利好/中性/利空/重大利空），并量化影响程度。报告末尾附 Markdown 表格列出关键政策事件、影响方向和持续时间。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近期相关政策事件清单（含发布日期和发布机构）"
            "\n2. 行业政策方向判断（扶持/限制/中性）"
            "\n3. 政策影响力度评级（强/中/弱）"
            "\n4. 政策影响时间窗口估算"
            "\n5. 政策面总体评级"
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
        from tradingagents.llm_clients import create_llm_client
        fresh_llm = llm
        try:
            if hasattr(llm, 'model_name'):
                model_lower = str(llm.model_name).lower()
                if any(kw in model_lower for kw in ('qwen', 'dashscope')):
                    fresh_llm = create_llm_client(
                        provider="dashscope", model=llm.model_name, temperature=0.3
                    )
                    logger.info(f"🔄 [政策分析师] DashScope/Qwen检测，创建全新LLM实例")
        except Exception as e:
            logger.warning(f"⚠️ [政策分析师] LLM检测失败: {e}")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.info(f"📊 [政策分析师] ✅ 工具绑定成功，绑定了 {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"📊 [政策分析师] ❌ 工具绑定失败: {e}")
            raise e

        logger.info(f"📊 [政策分析师] 开始调用LLM...")
        result = chain.invoke({"messages": state["messages"]})
        logger.info(f"📊 [政策分析师] LLM调用完成")

        if hasattr(result, 'content') and result.content:
            logger.info(f"🤖 [政策分析师] - 内容长度: {len(result.content)}")

        if hasattr(result, 'tool_calls'):
            logger.info(f"📊 [政策分析师] - tool_calls数量: {len(result.tool_calls)}")

        # Google model handling
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            logger.info(f"📊 [政策分析师] 检测到Google模型，使用统一工具调用处理器")

            specific_requirements = (
                "请从以下五个层面分析政策对股票的影响：\n"
                "1. 宏观政策面：货币政策（利率、准备金率）、财政政策走向\n"
                "2. 产业政策面：所属行业的政策扶持/限制力度\n"
                "3. 监管环境：近期监管处罚、法规变化、行业整顿\n"
                "4. 区域政策：自贸区、新区规划等区域性利好/利空\n"
                "5. 政策预期：市场对政策走向的预期与可能变化\n\n"
                "输出格式：每个层面单独成段，末尾给出政策面综合评级（利好/中性/利空，附带置信度）。"
            )

            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="政策分析",
                specific_requirements=specific_requirements,
            )

            report, messages_out = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=fresh_llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="政策分析师"
            )

            return {"policy_report": report}
        else:
            current_tool_calls = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0

            if current_tool_calls > 0:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)

                if has_tool_result:
                    logger.warning(f"⚠️ [强制生成报告] 工具已返回数据，但LLM仍尝试调用工具，强制基于现有数据生成报告")
                    force_system_prompt = (
                        f"你是专业的股票政策分析师。"
                        f"你已经收到了股票 {company_name}（代码：{ticker}）的政策和新闻数据。"
                        f"🚨 现在你必须基于这些数据生成完整的政策分析报告！🚨\n\n"
                        f"报告必须包含：\n"
                        f"1. 宏观政策面分析\n2. 产业政策面分析\n3. 监管环境分析\n"
                        f"4. 区域政策分析\n5. 政策预期\n6. 政策面综合评级（利好/中性/利空）\n\n"
                        f"要求：使用中文撰写报告，基于消息历史中的真实数据进行分析。"
                    )
                    force_prompt = ChatPromptTemplate.from_messages([
                        ("system", force_system_prompt),
                        MessagesPlaceholder(variable_name="messages"),
                    ])
                    force_chain = force_prompt | fresh_llm
                    logger.info(f"🔧 [强制生成报告] 使用专门的提示词重新调用LLM...")
                    force_result = force_chain.invoke({"messages": messages})
                    report = str(force_result.content) if hasattr(force_result, 'content') else "政策分析完成"
                    logger.info(f"✅ [强制生成报告] 成功生成报告，长度: {len(report)}字符")
                    return {
                        "policy_report": report,
                        "messages": [force_result],
                        "policy_tool_call_count": tool_call_count
                    }

                elif tool_call_count >= max_tool_calls:
                    logger.warning(f"🔧 [异常情况] 达到最大工具调用次数 {max_tool_calls}")
                    fallback_report = f"政策分析（股票代码：{ticker}）\n\n由于达到最大工具调用次数限制，使用简化分析模式。"
                    return {
                        "messages": [result],
                        "policy_report": fallback_report,
                        "policy_tool_call_count": tool_call_count
                    }
                else:
                    logger.info(f"✅ [正常流程] LLM调用工具，等待工具执行")
                    return {"messages": [result]}
            else:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)
                has_analysis_content = (
                    hasattr(result, 'content') and result.content
                    and len(str(result.content)) > 500
                )

                if has_tool_result or has_analysis_content:
                    report = str(result.content) if hasattr(result, 'content') else "政策分析完成"
                    logger.info(f"📊 [返回结果] 报告长度: {len(report)}字符")
                    return {
                        "policy_report": report,
                        "messages": [result],
                        "policy_tool_call_count": tool_call_count
                    }

                # Force tool call
                logger.info(f"🔧 [决策] 执行强制工具调用")
                try:
                    unified_tool = None
                    for tool in tools:
                        tool_name = getattr(tool, 'name', None) or getattr(tool, '__name__', '')
                        if tool_name == 'get_stock_news_unified':
                            unified_tool = tool
                            break
                    if unified_tool:
                        combined_data = unified_tool.invoke({
                            'ticker': ticker,
                            'curr_date': current_date
                        })
                        logger.info(f"✅ [工具调用] 统一工具调用成功，数据长度: {len(combined_data)}字符")
                    else:
                        combined_data = "统一新闻工具不可用"
                except Exception as e:
                    combined_data = f"统一新闻工具调用失败: {e}"

                analysis_prompt = (
                    f"基于以下真实数据，对{company_name}（股票代码：{ticker}）进行详细的政策面分析：\n\n"
                    f"{combined_data}\n\n"
                    f"请提供五层政策分析并给出政策面综合评级（利好/中性/利空，附带置信度）。使用中文。"
                )

                try:
                    analysis_prompt_template = ChatPromptTemplate.from_messages([
                        ("system", "你是专业的A股政策分析师，基于提供的真实数据进行分析。"),
                        ("human", "{analysis_request}")
                    ])
                    analysis_chain = analysis_prompt_template | fresh_llm
                    analysis_result = analysis_chain.invoke({"analysis_request": analysis_prompt})
                    report = analysis_result.content if hasattr(analysis_result, 'content') else str(analysis_result)
                    logger.info(f"📊 [政策分析师] 强制工具调用完成，报告长度: {len(report)}")
                except Exception as e:
                    logger.error(f"❌ [政策分析师] 强制工具调用分析失败: {e}")
                    report = f"政策分析失败：{str(e)}"

                return {
                    "policy_report": report,
                    "policy_tool_call_count": tool_call_count
                }

        # Fallback
        return {
            "messages": [result],
            "policy_report": result.content if hasattr(result, 'content') else str(result),
            "policy_tool_call_count": tool_call_count
        }

    return policy_analyst_node