#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unified Intelligence Fetcher - 统一情报获取引擎 V2
使用所有本地传感器进行跨平台情报收集。
输出杂志风格的晨报供 Revenue Architect 使用。
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# --- Path Setup ---
# Add project root for `from src.sensors.*` imports
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# --- 传感器导入（安全导入，失败时记录日志） ---
def _safe_import_sensor(module_path, class_name):
    """安全导入传感器类，失败时记录警告并返回 None"""
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        return cls()
    except (ImportError, Exception) as e:
        logger.warning("%s 传感器不可用，跳过: %s", class_name, e)
        return None

# 统一使用 BaseSensor 接口导入所有传感器
_hn_sensor = _safe_import_sensor("src.sensors.hacker_news", "HackerNewsSensor")
_gh_sensor = _safe_import_sensor("src.sensors.github_trending", "GitHubTrendingSensor")
_kr_sensor = _safe_import_sensor("src.sensors.kr36_sensor", "Kr36Sensor")
_wscn_sensor = _safe_import_sensor("src.sensors.wallstreetcn_sensor", "WallStreetCNSensor")
_v2ex_sensor = _safe_import_sensor("src.sensors.v2ex_radar", "V2EXSensor")
_ph_sensor = _safe_import_sensor("src.sensors.product_hunt", "ProductHuntSensor")
_arxiv_sensor = _safe_import_sensor("src.sensors.arxiv_ai", "ArxivSensor")
_grok_sensor = _safe_import_sensor("src.sensors.x_grok_sensor", "GrokSensor")
_xhs_sensor = _safe_import_sensor("src.sensors.xhs_radar", "XHSSensor")

# --- 反幻觉：链接验证器 ---
try:
    from src.utils.verifier import verify_link
    import re
    VERIFIER_AVAILABLE = True
except ImportError:
    VERIFIER_AVAILABLE = False
    logger.warning("链接验证器不可用，跳过幻觉检查")


def validate_grok_report(markdown_content: str) -> str:
    """
    Anti-Hallucination Layer: Extract and validate all links in Grok's output.
    Appends warning to invalid links.
    """
    if not VERIFIER_AVAILABLE:
        return markdown_content
    
    # Extract all markdown links
    link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    matches = re.findall(link_pattern, markdown_content)
    
    if not matches:
        return markdown_content
    
    logger.info("正在验证 Grok 输出中的 %d 个链接...", len(matches))
    validated_content = markdown_content
    
    for title, url in matches:
        # Skip known-good domains that block HEAD requests
        skip_domains = ['twitter.com', 'x.com', 'weibo.com', 'xiaohongshu.com']
        if any(domain in url for domain in skip_domains):
            continue
        
        is_valid = verify_link(url)
        if not is_valid:
            # Append warning to the link
            old_link = f"[{title}]({url})"
            new_link = f"[{title}]({url}) **(⚠️ 链接验证失败/404)**"
            validated_content = validated_content.replace(old_link, new_link)
            logger.warning("无效链接: %s", url)
        else:
            logger.debug("有效链接: %s...", url[:50])
    
    return validated_content


def _sensor_task(sensor, limit):
    """统一的传感器获取任务，使用 BaseSensor 接口"""
    if not sensor.is_available():
        logger.warning("%s 传感器不可用", sensor.name)
        return "", []
    results = sensor.fetch_with_cache(limit)
    if not results:
        return "", []
    items = []
    for r in results:
        item = r.to_dict()
        # Grok 特殊处理：保留 markdown_report 类型
        if r.metadata.get("type") == "markdown_report":
            content = r.metadata.get("content", "")
            validated = validate_grok_report(content)
            item["content"] = validated
            item["type"] = "markdown_report"
        items.append(item)
    return results[0].category, items


def fetch_all_sources(limit_per_source: int = 10) -> dict:
    """使用 ThreadPoolExecutor 并行获取所有数据源（统一 BaseSensor 接口）"""
    intel = {
        "tech_trends": [],
        "capital_flow": [],
        "product_gems": [],
        "community": [],
        "research": [],
        "social": [],
        "xhs_directives": [],
    }

    # 构建传感器列表：(传感器实例, 名称)
    all_sensors = [
        (_hn_sensor, "Hacker News"),
        (_gh_sensor, "GitHub"),
        (_kr_sensor, "36Kr"),
        (_wscn_sensor, "WallStreetCN"),
        (_v2ex_sensor, "V2EX"),
        (_ph_sensor, "Product Hunt"),
        (_arxiv_sensor, "ArXiv"),
        (_grok_sensor, "Grok/X"),
        (_xhs_sensor, "XHS"),
    ]

    available = [
        (s, name) for s, name in all_sensors if s is not None
    ]

    logger.info(
        "并行获取 %d 个数据源: %s",
        len(available),
        ", ".join(n for _, n in available),
    )

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(_sensor_task, s, limit_per_source): name
            for s, name in available
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                category, results = future.result()
                if category and category in intel:
                    intel[category].extend(results)
                logger.info("%s 完成，获取 %d 条", name, len(results))
            except Exception as e:
                logger.warning("%s 失败: %s", name, e)

    return intel


def generate_report(intel: dict, date_str: str) -> str:
    """Generate magazine-style markdown report."""
    lines = [
        f"# 🌐 全球情报日报 (Global Intel Briefing)",
        f"**日期:** {date_str}",
        f"**生成时间:** {datetime.now().strftime('%H:%M')}",
        f"**数据源:** HN, GitHub, 36Kr, WallStreetCN, V2EX, PH, ArXiv, X, XHS",
        "",
        "---",
        ""
    ]
    
    # --- Tech Trends ---
    lines.append("## 🛠️ 技术趋势 (Tech Trends)")
    lines.append("> Hacker News + GitHub Trending\n")
    
    if intel.get("tech_trends"):
        for i, item in enumerate(intel["tech_trends"][:10], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            heat = item.get("heat", "")
            time_str = item.get("timestamp", "") or item.get("summary", "")
            src = item.get("source", "")

            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"📍 {src} | 🔥 {heat} | 🕒 {time_str}")
            lines.append("")
    else:
        lines.append("*暂无数据*\n")
    
    # --- Capital Flow ---
    lines.append("## 💰 资本动向 (Capital Flow)")
    lines.append("> 36Kr + 华尔街见闻\n")
    
    if intel.get("capital_flow"):
        for i, item in enumerate(intel["capital_flow"][:10], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            time_str = item.get("timestamp", "")
            src = item.get("source", "")

            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"📍 {src} | 🕒 {time_str}")
            lines.append("")
    else:
        lines.append("*暂无数据*\n")
    
    # --- Research (ArXiv) ---
    lines.append("## 📚 学术前沿 (Research)")
    lines.append("> ArXiv AI/ML Papers\n")
    
    if intel.get("research"):
        for i, item in enumerate(intel["research"][:5], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            authors = item.get("summary", "")
            time_str = item.get("timestamp", "")

            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"👤 {authors} | 📅 {time_str}")
            lines.append("")
    else:
        lines.append("*暂无数据*\n")
    
    # --- Product Gems ---
    lines.append("## 💎 产品精选 (Product Gems)")
    lines.append("> Product Hunt Today\n")
    
    if intel.get("product_gems"):
        for i, item in enumerate(intel["product_gems"][:8], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            heat = item.get("heat", "")
            tagline = item.get("summary", "")

            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"> {tagline}")
            lines.append(f"🔥 {heat}")
            lines.append("")
    else:
        lines.append("*暂无数据 (Product Hunt API 可能需要配置)*\n")
    
    # --- Social (X/Twitter) ---
    lines.append("## 🐦 社交热议 (Social)")
    lines.append("> X (Twitter) - AI/Tech Discussions\n")
    
    if intel.get("social"):
        for item in intel["social"]:
            if item.get("type") == "markdown_report":
                lines.append(f"> 来源: {item.get('source', 'X')}\n")
                lines.append(item.get("content", "*无内容*"))
                lines.append("")
            else:
                title = item.get("title", "")
                url = item.get("url", "#")
                heat = item.get("heat", "")

                lines.append(f"### [{title}]({url})")
                lines.append(f"❤️ {heat}")
                lines.append("")
    else:
        lines.append("*暂无数据 (需要配置 XAI_API_KEY)*\n")
    
    # --- Community ---
    lines.append("## 🗣️ 社区热点 (Community)")
    lines.append("> V2EX 热门\n")
    
    if intel.get("community"):
        for i, item in enumerate(intel["community"][:5], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            heat = item.get("heat", "")
            
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"💬 {heat}")
            lines.append("")
    else:
        lines.append("*暂无数据*\n")
    
    # --- XHS Directives (Manual) ---
    lines.append("## 📕 小红书雷达 (XHS Radar)")
    lines.append("> 手动搜索指令 (点击链接进入搜索页)\n")
    
    if intel.get("xhs_directives"):
        for i, item in enumerate(intel["xhs_directives"][:6], 1):
            title = item.get("title", "")
            url = item.get("url", "#")
            summary = item.get("summary", "")
            
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"> {summary[:80]}...")
            lines.append("")
    else:
        lines.append("*XHS 传感器不可用*\n")
    
    lines.append("---")
    lines.append("*报告由 Unified Intelligence Engine V2 自动生成*")
    
    return "\n".join(lines)


def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Unified Intel Fetcher V2")
    parser.add_argument("--limit", type=int, default=10, help="Items per source")
    parser.add_argument("--test", action="store_true", help="Test mode (1 item per source)")
    parser.add_argument("--output", type=str, help="Custom output path")
    args = parser.parse_args()

    limit = 1 if args.test else args.limit
    date_str = datetime.now().strftime("%Y-%m-%d")

    logger.info("统一情报获取引擎 V2 启动")
    logger.info("日期: %s | 每源限制: %d", date_str, limit)
    
    # Fetch
    intel = fetch_all_sources(limit_per_source=limit)
    
    # Generate report
    report = generate_report(intel, date_str)
    
    # Save
    if args.output:
        output_path = args.output
    else:
        reports_dir = os.path.join(os.path.dirname(__file__), "reports", "daily_briefings")
        os.makedirs(reports_dir, exist_ok=True)
        
        if args.test:
            output_path = os.path.join(reports_dir, "Morning_Report_TEST.md")
        else:
            output_path = os.path.join(reports_dir, f"Morning_Report_{date_str}.md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n[SUCCESS] Report saved to: {output_path}")
    print(f"\n--- Preview (first 40 lines) ---\n")
    for line in report.split("\n")[:40]:
        print(line)
    

if __name__ == "__main__":
    main()
