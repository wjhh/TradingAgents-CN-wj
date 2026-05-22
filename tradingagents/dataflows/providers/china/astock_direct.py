"""A-stock direct data provider for TradingAgents-CN-wj.

Wraps a-stock-data-wj signal/data functions in a clean provider class suitable
for dependency injection into Toolkit.

All methods return str (LLM-consumable), not DataFrame/dict.
Each method includes try/except + timeout + error message return.

Data sources (zero akshare):
- mootdx (TCP 7709): K-lines, financial snapshots, F10 shareholder data
- Tencent Finance (qt.gtimg.cn): PE/PB/market cap/turnover
- 东方财富 (datacenter-web + push2): stock info, dragon-tiger, lockup calendar, industry
- 新浪财经 (direct HTTP): K-line fallback, financial statements
- 同花顺 (direct HTTP): EPS forecasts, hot stocks, northbound capital flow
- 百度股市通 (finance.pae.baidu.com): concept blocks, fund flow
- 财联社 (cls.cn): global news wire
"""

from __future__ import annotations

import csv
import json as _json
import logging
import math
import os
import re as _re
import urllib.request
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests as _requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

_BAIDU_PAE_HEADERS = {
    "Host": "finance.pae.baidu.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
        "Gecko/20100101 Firefox/110.0"
    ),
    "Accept": "application/vnd.finance-web.v1+json",
    "Origin": "https://gushitong.baidu.com",
    "Referer": "https://gushitong.baidu.com/",
}


# ---------------------------------------------------------------------------
# Ticker helpers
# ---------------------------------------------------------------------------

def _get_prefix(code: str) -> str:
    """6-digit A-stock code -> market prefix for Tencent API."""
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    return "sz"


def _normalize_ticker(symbol: str) -> str:
    """Strip exchange prefix/suffix, return pure 6-digit code.

    Handles: '688017', 'SH688017', '688017.SH', 'sh688017'
    """
    s = symbol.strip().upper()
    for suffix in (".SH", ".SZ", ".BJ"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    for prefix in ("SH", "SZ", "BJ"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


# ---------------------------------------------------------------------------
# Eastmoney Datacenter helper
# ---------------------------------------------------------------------------

def _eastmoney_datacenter(
    report_name: str,
    columns: str = "ALL",
    filter_str: str = "",
    page_size: int = 50,
    sort_columns: str = "",
    sort_types: str = "-1",
) -> list[dict]:
    """Eastmoney datacenter unified query — dragon-tiger/lockup/etc."""
    params = {
        "reportName": report_name,
        "columns": columns,
        "filter": filter_str,
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortColumns": sort_columns,
        "sortTypes": sort_types,
        "source": "WEB",
        "client": "WEB",
    }
    r = _requests.get(
        _DATACENTER_URL, params=params, headers={"User-Agent": _UA}, timeout=15
    )
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


# ===========================================================================
# AStockDirectProvider
# ===========================================================================


class AStockDirectProvider:
    """A-stock direct HTTP/TCP data provider. Zero third-party DB dependency.

    Usage:
        provider = AStockDirectProvider(config={"mootdx_port": 7709})
        result = provider.get_hot_stocks("2026-05-20")
    """

    def __init__(self, config: dict = None, mongodb_cache=None):
        self.config = config or {}
        self.mongodb_cache = mongodb_cache
        self._mootdx_client = None
        self._name_to_code: dict | None = None
        self._code_to_name: dict | None = None

    # ---- mootdx client (lazy singleton) ----

    def _get_mootdx_client(self):
        if self._mootdx_client is None:
            from mootdx.quotes import Quotes
            self._mootdx_client = Quotes.factory(market="std")
        return self._mootdx_client

    # ---- Name/code mapping ----

    def _build_name_code_map(self):
        if self._name_to_code is not None:
            return self._name_to_code, self._code_to_name

        try:
            client = self._get_mootdx_client()
            n2c: dict[str, str] = {}
            c2n: dict[str, str] = {}

            for market in (0, 1):  # 0=SZ, 1=SH
                stocks = client.stocks(market=market)
                if stocks is None or stocks.empty:
                    continue
                for _, row in stocks.iterrows():
                    code = str(row["code"]).strip()
                    name = str(row["name"]).strip()
                    if not _re.match(r"^[036]\d{5}$", code):
                        continue
                    clean_name = name.replace(" ", "").replace("　", "")
                    n2c[clean_name] = code
                    c2n[code] = clean_name

            self._name_to_code = n2c
            self._code_to_name = c2n
            logger.info("Built stock name-code map: %d entries", len(n2c))
        except Exception as e:
            logger.warning("Failed to build name-code map: %s", e)
            self._name_to_code = {}
            self._code_to_name = {}

        return self._name_to_code, self._code_to_name

    def resolve_ticker(self, user_input: str) -> str:
        """Resolve user input (code or Chinese name) to a 6-digit A-stock code."""
        s = user_input.strip()
        if not s:
            raise ValueError("Input cannot be empty")

        has_chinese = any("一" <= ch <= "鿿" for ch in s)
        if not has_chinese:
            return _normalize_ticker(s)

        clean = s.replace(" ", "").replace("　", "")
        n2c, _ = self._build_name_code_map()

        if clean in n2c:
            return n2c[clean]

        matches = {name: code for name, code in n2c.items() if clean in name}
        if len(matches) == 1:
            return next(iter(matches.values()))
        if len(matches) > 1:
            examples = ", ".join(f"{n}({c})" for n, c in list(matches.items())[:5])
            raise ValueError(f"'{s}' matched multiple: {examples}")

        raise ValueError(f"Cannot find stock '{s}'")

    # ---- Tencent quote helper ----

    def _tencent_quote(self, codes: list[str]) -> dict:
        """Batch real-time quotes from Tencent Finance."""
        prefixed = [f"{_get_prefix(c)}{c}" for c in codes]
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            raw = resp.read().decode("gbk")
        except Exception as e:
            logger.warning("Tencent quote failed: %s", e)
            return {}

        result = {}
        for line in raw.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name": vals[1],
                "price": float(vals[3]) if vals[3] else 0,
                "last_close": float(vals[4]) if vals[4] else 0,
                "open": float(vals[5]) if vals[5] else 0,
                "change_pct": float(vals[32]) if vals[32] else 0,
                "high": float(vals[33]) if vals[33] else 0,
                "low": float(vals[34]) if vals[34] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "pe_ttm": float(vals[39]) if vals[39] else 0,
                "mcap_yi": float(vals[44]) if vals[44] else 0,
                "float_mcap_yi": float(vals[45]) if vals[45] else 0,
                "pb": float(vals[46]) if vals[46] else 0,
                "limit_up": float(vals[47]) if vals[47] else 0,
                "limit_down": float(vals[48]) if vals[48] else 0,
                "pe_static": float(vals[52]) if vals[52] else 0,
            }
        return result

    # =======================================================================
    # Signal Layer (7 endpoints — directly needed by 3 new analysts)
    # =======================================================================

    # ---- 1. get_insider_transactions ----

    def get_insider_transactions(self, ticker: str) -> str:
        """Get shareholder/insider activity via mootdx F10 shareholder research."""
        code = _normalize_ticker(ticker)
        try:
            client = self._get_mootdx_client()
            text = client.F10(symbol=code, name="股东研究")

            if not text or not text.strip():
                return f"No insider/shareholder data found for A-stock '{code}'"

            header = f"# Shareholder Research for {code} (A-stock)\n"
            header += "# Data source: mootdx F10\n"
            header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            # Trim to focus on section 4 (shareholder changes)
            sec4_hits = list(_re.finditer(r"\r?\n【4\.股东变化】\r?\n", text))
            if sec4_hits:
                sec4_pos = sec4_hits[-1].start()
                before_sec4 = text[:sec4_pos]
                sec4_text = text[sec4_pos:]
                cut_at = 2000
                if len(sec4_text) > cut_at:
                    sec4_text = (
                        sec4_text[:cut_at]
                        + "\n\n(... older shareholder history omitted, "
                        f"{len(text) - sec4_pos - cut_at} chars truncated ...)"
                    )
                text = before_sec4 + sec4_text

            return header + text
        except Exception as e:
            return f"Error retrieving insider/shareholder data for {code}: {str(e)}"

    # ---- 2. get_hot_stocks ----

    def get_hot_stocks(self, curr_date: str = "") -> str:
        """Get limit-up stocks with human-curated reason tags from 同花顺."""
        if not curr_date or curr_date.strip() == "":
            curr_date = datetime.now().strftime("%Y-%m-%d")

        try:
            url = (
                f"http://zx.10jqka.com.cn/event/api/getharden/"
                f"date/{curr_date}/orderby/date/orderway/desc/charset/GBK/"
            )
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "Chrome/117.0.0.0 Safari/537.36"
                )
            }
            r = _requests.get(url, headers=headers, timeout=10)
            data = r.json()

            if data.get("errocode", 0) != 0:
                return f"同花顺 API error: {data.get('errormsg', 'unknown')}"

            rows = data.get("data") or []
            if not rows:
                return (
                    f"No hot stocks data for {curr_date} "
                    f"(may be non-trading day or data not yet available)"
                )

            lines = [
                f"# Hot Stocks with Topic Attribution ({curr_date})",
                f"# Source: 同花顺 editorial (human-curated reason tags)",
                f"# Total: {len(rows)} stocks",
                "",
            ]

            all_tags: list[str] = []
            for row in rows:
                code = row.get("code", "")
                name = row.get("name", "")
                reason = row.get("reason", "")
                zhangfu = row.get("zhangfu", "")
                huanshou = row.get("huanshou", "")
                chengjiaoe = row.get("chengjiaoe", "")
                dde = row.get("ddejingliang", "")

                lines.append(
                    f"{code} {name}: +{zhangfu}% "
                    f"换手{huanshou}% 成交额{chengjiaoe} "
                    f"大单净量{dde} | {reason}"
                )

                if reason:
                    tags = [t.strip() for t in str(reason).split("+") if t.strip()]
                    all_tags.extend(tags)

            if all_tags:
                cnt = Counter(all_tags)
                lines.append(f"\n## Theme Frequency (top 15)")
                for tag, n in cnt.most_common(15):
                    lines.append(f"  {tag}: {n} stocks")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching hot stocks for {curr_date}: {str(e)}"

    # ---- 3. get_northbound_flow ----

    def get_northbound_flow(self, curr_date: str, include_history: bool = True) -> str:
        """Get northbound capital flow (沪深股通) from 同花顺 hsgtApi.

        Realtime: minute-level cumulative net buying for HGT + SGT.
        History: MongoDB-cached daily close snapshots (replaces CSV self-cache).
        """
        hsgt_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "Chrome/117.0.0.0 Safari/537.36"
            ),
            "Host": "data.hexin.cn",
            "Referer": "https://data.hexin.cn/",
        }

        lines = [
            f"# Northbound Capital Flow ({curr_date})",
            "# Source: 同花顺 hsgtApi (沪深股通)",
            "",
        ]

        hgt_close = 0.0
        sgt_close = 0.0
        got_realtime = False

        try:
            url_rt = "https://data.hexin.cn/market/hsgtApi/method/dayChart/"
            r = _requests.get(url_rt, headers=hsgt_headers, timeout=10)
            d = r.json()

            times = d.get("time", [])
            hgt = d.get("hgt", [])
            sgt = d.get("sgt", [])

            if times:
                lines.append("## Realtime (cumulative net buying, 亿元)")
                n = len(times)
                start_idx = max(0, n - 10)
                for i in range(start_idx, n):
                    t = times[i]
                    h = hgt[i] if i < len(hgt) else "N/A"
                    s = sgt[i] if i < len(sgt) else "N/A"
                    lines.append(f"  {t}: HGT={h} SGT={s}")

                hgt_close = float(hgt[-1]) if hgt else 0
                sgt_close = float(sgt[-1]) if sgt else 0
                total = hgt_close + sgt_close
                lines.append(
                    f"\nClose: HGT(沪股通)={hgt_close:.2f}亿 "
                    f"SGT(深股通)={sgt_close:.2f}亿 "
                    f"Total={total:.2f}亿"
                )
                if total > 0:
                    lines.append("Signal: Net northbound INFLOW (bullish)")
                elif total < 0:
                    lines.append("Signal: Net northbound OUTFLOW (bearish)")
                got_realtime = True
            else:
                lines.append("No realtime data (non-trading hours or holiday)")

            # Save snapshot to MongoDB (preferred) or local CSV fallback
            if got_realtime:
                today_str = datetime.now().strftime("%Y-%m-%d")
                self._save_northbound_snapshot(today_str, hgt_close, sgt_close)

            if include_history:
                history = self._load_northbound_history(20)
                if history:
                    lines.append("\n## Historical Daily Close (亿元)")
                    lines.append("Date       | HGT(沪股通) | SGT(深股通) | Total")
                    for date, h, s in history:
                        lines.append(f"  {date}: HGT={h:.2f} SGT={s:.2f} Total={h + s:.2f}")
                    avg_total = sum(h + s for _, h, s in history) / len(history)
                    lines.append(f"\n{len(history)}-day avg net flow: {avg_total:.2f}亿")
                    if got_realtime:
                        today_total = hgt_close + sgt_close
                        diff = today_total - avg_total
                        lines.append(
                            f"Today vs avg: {'+' if diff >= 0 else ''}{diff:.2f}亿 "
                            f"({'above' if diff >= 0 else 'below'} average)"
                        )
                else:
                    lines.append("\n## Historical Daily: No cached data yet.")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching northbound flow: {str(e)}"

    def _northbound_cache_path(self) -> str:
        cache_dir = self.config.get(
            "data_cache_dir", os.path.expanduser("~/.tradingagents/cache")
        )
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "northbound_daily.csv")

    def _save_northbound_snapshot(self, date_str: str, hgt: float, sgt: float) -> None:
        """Save northbound daily close to local CSV cache (dedup by date)."""
        path = self._northbound_cache_path()
        existing: dict[str, tuple[str, str]] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        existing[row[0]] = (row[1], row[2])
        existing[date_str] = (f"{hgt:.2f}", f"{sgt:.2f}")
        sorted_dates = sorted(existing.keys())
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "hgt", "sgt"])
            for d in sorted_dates:
                writer.writerow([d, existing[d][0], existing[d][1]])

    def _load_northbound_history(self, n: int = 20) -> list[tuple[str, float, float]]:
        """Load last N days of northbound close data from local cache."""
        path = self._northbound_cache_path()
        if not os.path.exists(path):
            return []
        rows: list[tuple[str, float, float]] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3:
                    try:
                        rows.append((row[0], float(row[1]), float(row[2])))
                    except ValueError:
                        continue
        return rows[-n:]

    # ---- 4. get_concept_blocks ----

    def get_concept_blocks(self, ticker: str) -> str:
        """Get concept/sector/region blocks from 百度股市通."""
        code = _normalize_ticker(ticker)
        try:
            url = (
                "https://finance.pae.baidu.com/api/getrelatedblock"
                f'?stock=[{{"code":"{code}","market":"ab","type":"stock"}}]'
                "&finClientType=pc"
            )
            r = _requests.get(url, headers=_BAIDU_PAE_HEADERS, timeout=10)
            d = r.json()

            if str(d.get("ResultCode", -1)) != "0":
                return (
                    f"Baidu PAE error: ResultCode={d.get('ResultCode')} "
                    f"{d.get('ResultMsg', '')}"
                )

            result = d.get("Result", {})
            categories = result.get(code, [])
            if not categories:
                return f"No concept/block data for {code}"

            lines = [
                f"# Concept & Sector Blocks for {code} (A-stock)",
                f"# Source: 百度股市通 (Baidu PAE)",
                f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]

            concept_names: list[str] = []
            for cat in categories:
                cat_name = cat.get("name", "")
                items = cat.get("list", [])
                if not items:
                    continue
                lines.append(f"## {cat_name}")
                for item in items:
                    name = item.get("name", "")
                    ratio = item.get("ratio", "")
                    desc = item.get("describe", "")
                    suffix = f" ({desc})" if desc else ""
                    lines.append(f"  {name}{suffix}: {ratio}")
                    if cat_name == "概念":
                        concept_names.append(name)

            if concept_names:
                lines.append(f"\nConcept tags: {' / '.join(concept_names)}")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching concept blocks for {code}: {str(e)}"

    # ---- 5. get_fund_flow ----

    def get_fund_flow(self, ticker: str, curr_date: str, include_history: bool = True) -> str:
        """Get individual stock fund flow from 百度股市通.

        Realtime: minute-level main force vs retail investor flow.
        History: daily super/large/medium/small order net inflow for 20 days.
        """
        code = _normalize_ticker(ticker)
        lines = [
            f"# Fund Flow for {code} (A-stock)",
            f"# Source: 百度股市通 (Baidu PAE)",
            f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        try:
            # Realtime minute-level fund flow
            url_rt = (
                "https://finance.pae.baidu.com/vapi/v1/fundflow"
                f"?finance_type=stock&fund_flow_type=&type=stock"
                f"&market=ab&code={code}&belongs=stocklevelone"
                "&finClientType=pc"
            )
            r = _requests.get(url_rt, headers=_BAIDU_PAE_HEADERS, timeout=10)
            d = r.json()

            if str(d.get("ResultCode", -1)) == "0":
                content = d.get("Result", {}).get("content", {})
                ff = content.get("fundFlowMinute", {})
                data_str = ff.get("data", "")
                rows = data_str.split(";") if data_str else []

                if rows:
                    lines.append("## Realtime Minute Flow (mainForce vs retailInvestor, 万元)")
                    for row in rows[-10:]:
                        parts = row.split(",")
                        if len(parts) >= 8:
                            lines.append(
                                f"  {parts[0]}: "
                                f"主力={parts[2]} 散户={parts[3]} "
                                f"超大单={parts[4]} 大单={parts[5]} "
                                f"price={parts[8] if len(parts) > 8 else ''}"
                            )

                    last_row = rows[-1].split(",")
                    if len(last_row) >= 4:
                        main_force = float(last_row[2])
                        lines.append(f"\nClose: mainForce={last_row[2]}万 retail={last_row[3]}万")
                        if main_force > 0:
                            lines.append("Signal: Net main force INFLOW (bullish)")
                        elif main_force < 0:
                            lines.append("Signal: Net main force OUTFLOW (bearish)")
                else:
                    lines.append("No realtime fund flow (non-trading hours or holiday)")

            # Historical daily fund flow
            if include_history:
                date_compact = curr_date.replace("-", "")
                url_hist = (
                    "https://finance.pae.baidu.com/vapi/v1/fundsortlist"
                    f"?code={code}&market=ab&finance_type=stock"
                    f"&tab=day&from=history&date={date_compact}"
                    "&pn=0&rn=20&finClientType=pc"
                )
                rh = _requests.get(url_hist, headers=_BAIDU_PAE_HEADERS, timeout=10)
                dh = rh.json()

                if dh.get("ResultCode", -1) == 0:
                    hist = dh.get("Result", {}).get("content", [])
                    if hist:
                        lines.append(f"\n## Historical Daily Fund Flow (last {len(hist)} trading days)")
                        lines.append("Date | Close | Change | SuperBig | Large | Medium | Small | MainForce")
                        for row in hist:
                            lines.append(
                                f"  {row.get('showtime', '')} "
                                f"| {row.get('closepx', '')} "
                                f"| {row.get('ratio', '')} "
                                f"| super={row.get('superNetIn', '')} "
                                f"| large={row.get('largeNetIn', '')} "
                                f"| med={row.get('mediumNetIn', '')} "
                                f"| small={row.get('littleNetIn', '')} "
                                f"| main={row.get('extMainIn', '')}"
                            )

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching fund flow for {code}: {str(e)}"

    # ---- 6. get_dragon_tiger_board ----

    def get_dragon_tiger_board(
        self, ticker: str, trade_date: str, look_back_days: int = 30
    ) -> str:
        """Get dragon-tiger board (龙虎榜) appearances and seat details."""
        code = _normalize_ticker(ticker)
        end_dt = datetime.strptime(trade_date, "%Y-%m-%d")
        start_dt = end_dt - pd.Timedelta(days=look_back_days)
        start_date_str = start_dt.strftime("%Y-%m-%d")
        lines = [f"# 龙虎榜数据 | {code} | {trade_date} (近{look_back_days}日)"]

        data = []
        # 1. Appearances
        try:
            data = _eastmoney_datacenter(
                "RPT_DAILYBILLBOARD_DETAILSNEW",
                filter_str=(
                    f"(TRADE_DATE>='{start_date_str}')"
                    f"(TRADE_DATE<='{trade_date}')"
                    f'(SECURITY_CODE="{code}")'
                ),
                page_size=50,
                sort_columns="TRADE_DATE",
                sort_types="-1",
            )
            if not data:
                lines.append(f"\n近{look_back_days}日未上龙虎榜。")
            else:
                lines.append(f"\n## 上榜记录 ({len(data)} 次)")
                lines.append("日期 | 原因 | 净买入(万) | 换手率")
                for row in data:
                    net_buy = round((row.get("BILLBOARD_NET_AMT") or 0) / 10000, 1)
                    turnover = round(float(row.get("TURNOVERRATE") or 0), 2)
                    lines.append(
                        f"  {str(row.get('TRADE_DATE', ''))[:10]} "
                        f"| {row.get('EXPLANATION', '')} "
                        f"| {net_buy:.0f} "
                        f"| {turnover:.2f}%"
                    )
        except Exception as e:
            lines.append(f"龙虎榜列表查询失败: {e}")

        # 2. Latest seat details
        try:
            if data:
                latest_date = str(data[0].get("TRADE_DATE", ""))[:10]
                lines.append(f"\n## 最近上榜席位明细 ({latest_date})")

                buy_data = _eastmoney_datacenter(
                    "RPT_BILLBOARD_DAILYDETAILSBUY",
                    filter_str=f'(TRADE_DATE=\'{latest_date}\')(SECURITY_CODE="{code}")',
                    page_size=10,
                    sort_columns="BUY",
                    sort_types="-1",
                )
                if buy_data:
                    lines.append("\n### 买入席位 TOP5")
                    lines.append("营业部 | 买入(万) | 卖出(万) | 净额(万)")
                    for row in buy_data[:5]:
                        buy_amt = round((row.get("BUY") or 0) / 10000, 1)
                        sell_amt = round((row.get("SELL") or 0) / 10000, 1)
                        net = round((row.get("NET") or 0) / 10000, 1)
                        lines.append(
                            f"  {row.get('OPERATEDEPT_NAME', '')} "
                            f"| {buy_amt:.0f} | {sell_amt:.0f} | {net:.0f}"
                        )

                sell_data = _eastmoney_datacenter(
                    "RPT_BILLBOARD_DAILYDETAILSSELL",
                    filter_str=f'(TRADE_DATE=\'{latest_date}\')(SECURITY_CODE="{code}")',
                    page_size=10,
                    sort_columns="SELL",
                    sort_types="-1",
                )
                if sell_data:
                    lines.append("\n### 卖出席位 TOP5")
                    lines.append("营业部 | 买入(万) | 卖出(万) | 净额(万)")
                    for row in sell_data[:5]:
                        buy_amt = round((row.get("BUY") or 0) / 10000, 1)
                        sell_amt = round((row.get("SELL") or 0) / 10000, 1)
                        net = round((row.get("NET") or 0) / 10000, 1)
                        lines.append(
                            f"  {row.get('OPERATEDEPT_NAME', '')} "
                            f"| {buy_amt:.0f} | {sell_amt:.0f} | {net:.0f}"
                        )
        except Exception:
            pass

        # 3. Institutional activity
        try:
            inst_data = _eastmoney_datacenter(
                "RPT_ORGANIZATION_BUSSINESS",
                filter_str=f'(SECURITY_CODE="{code}")',
                page_size=1,
                sort_columns="TRADE_DATE",
                sort_types="-1",
            )
            if inst_data:
                row = inst_data[0]
                lines.append("\n## 机构动向")
                lines.append(
                    f"  机构买入 {row.get('BUY_TIMES', 0)} 家 "
                    f"| 卖出 {row.get('SELL_TIMES', 0)} 家 "
                    f"| 净额 {round((row.get('NET_BUY_AMT') or 0) / 10000, 1):.0f} 万"
                )
        except Exception:
            pass

        return "\n".join(lines)

    # ---- 7. get_lockup_expiry ----

    def get_lockup_expiry(self, ticker: str, trade_date: str, forward_days: int = 90) -> str:
        """Get lockup expiry schedule for a stock."""
        code = _normalize_ticker(ticker)
        lines = [f"# 限售解禁日历 | {code} | {trade_date}"]

        try:
            history_data = _eastmoney_datacenter(
                "RPT_LIFT_STAGE",
                filter_str=f'(SECURITY_CODE="{code}")',
                page_size=15,
                sort_columns="FREE_DATE",
                sort_types="-1",
            )
            if history_data:
                lines.append(f"\n## 个股解禁记录 (共 {len(history_data)} 批)")
                lines.append("解禁时间 | 类型 | 解禁数量 | 占比")
                for row in history_data:
                    lines.append(
                        f"  {str(row.get('FREE_DATE', ''))[:10]} "
                        f"| {row.get('LIMITED_STOCK_TYPE', '')} "
                        f"| {row.get('FREE_SHARES_NUM', '')} "
                        f"| {row.get('FREE_RATIO', '')}"
                    )
            else:
                lines.append("\n无历史解禁记录。")
        except Exception as e:
            lines.append(f"个股解禁查询失败: {e}")

        try:
            end_dt = datetime.strptime(trade_date, "%Y-%m-%d") + pd.Timedelta(days=forward_days)
            end_str = end_dt.strftime("%Y-%m-%d")
            upcoming_data = _eastmoney_datacenter(
                "RPT_LIFT_STAGE",
                filter_str=(
                    f'(SECURITY_CODE="{code}")'
                    f"(FREE_DATE>='{trade_date}')"
                    f"(FREE_DATE<='{end_str}')"
                ),
                page_size=20,
                sort_columns="FREE_DATE",
                sort_types="1",
            )
            if upcoming_data:
                lines.append(f"\n## 未来 {forward_days} 天待解禁")
                for row in upcoming_data:
                    lines.append(
                        f"  {str(row.get('FREE_DATE', ''))[:10]} "
                        f"| {row.get('LIMITED_STOCK_TYPE', '')} "
                        f"| 数量 {row.get('FREE_SHARES_NUM', '')} "
                        f"| 占比 {row.get('FREE_RATIO', '')}"
                    )
            else:
                lines.append(f"\n未来 {forward_days} 天无待解禁。")
        except Exception as e:
            lines.append(f"解禁日历查询失败: {e}")

        return "\n".join(lines)

    # ---- 8. get_industry_comparison ----

    def get_industry_comparison(self, ticker: str, trade_date: str, top_n: int = 20) -> str:
        """Get industry sector performance ranking from 东财 push2."""
        code = _normalize_ticker(ticker)
        lines = [f"# 行业横向对比 | {code} | {trade_date}"]

        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": str(top_n),
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90+t:2",
                "fields": "f2,f3,f4,f12,f14,f20",
                "_": str(int(datetime.now().timestamp() * 1000)),
            }
            r = _requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=10)
            d = r.json()
            items = (d.get("data") or {}).get("diff") or []

            if items:
                lines.append("\n## 行业板块涨跌排名")
                lines.append("排名 | 行业 | 涨幅% | 成交额(亿)")
                for i, item in enumerate(items, 1):
                    name = item.get("f14", "")
                    change = item.get("f3", 0)
                    amount = round((item.get("f20") or 0) / 1e8, 1)
                    lines.append(f"  {i}. {name}: {change}% | {amount}亿")
            else:
                lines.append("无法获取行业数据。")
        except Exception as e:
            lines.append(f"行业对比查询失败: {e}")

        return "\n".join(lines)

    # =======================================================================
    # Market Data Layer
    # =======================================================================

    def get_realtime_quote(self, ticker: str) -> str:
        """Get real-time quote with PE/PB/market cap/turnover from Tencent Finance."""
        code = _normalize_ticker(ticker)
        try:
            q = self._tencent_quote([code])
            if code not in q:
                return f"No real-time quote for {code}"

            d = q[code]
            lines = [
                f"# Real-time Quote for {d['name']} ({code})",
                f"Price: {d['price']}",
                f"Change: {d['change_pct']}%",
                f"Open: {d['open']}  High: {d['high']}  Low: {d['low']}",
                f"PE(TTM): {d['pe_ttm']}  PB: {d['pb']}",
                f"Market Cap: {d['mcap_yi']}亿  Float Cap: {d['float_mcap_yi']}亿",
                f"Turnover: {d['turnover_pct']}%",
                f"Limit Up: {d['limit_up']}  Limit Down: {d['limit_down']}",
                f"Source: Tencent Finance (qt.gtimg.cn)",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching real-time quote for {code}: {str(e)}"