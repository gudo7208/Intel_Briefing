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
# Add local src for sensors and utils
LOCAL_SRC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if LOCAL_SRC_PATH not in sys.path:
    sys.path.insert(0, LOCAL_SRC_PATH)

# --- 传感器导入（安全导入，失败时记录日志） ---
def _safe_import(module_path, name):
    """安全导入模块，失败时记录警告"""
    try:
        mod = __import__(module_path, fromlist=[name])
        return getattr(mod, name), True
    except ImportError:
        logger.warning("%s 传感器不可用，跳过", name)
        return None, False

_fetch_hn, HN_AVAILABLE = _safe_import("sensors.hacker_news", "fetch_top_stories")
_fetch_github, GH_AVAILABLE = _safe_import("sensors.github_trending", "fetch_trending")
_fetch_36kr, KR_AVAILABLE = _safe_import("sensors.kr36_sensor", "fetch_36kr")
_fetch_wscn, WSCN_AVAILABLE = _safe_import("sensors.wallstreetcn_sensor", "fetch_wallstreetcn")
V2EXRadar, V2EX_AVAILABLE = _safe_import("sensors.v2ex_radar", "V2EXRadar")
fetch_trending_products, PH_AVAILABLE = _safe_import("sensors.product_hunt", "fetch_trending_products")
fetch_ai_papers, ARXIV_AVAILABLE = _safe_import("sensors.arxiv_ai", "fetch_ai_papers")
fetch_grok_intel, GROK_AVAILABLE = _safe_import("sensors.x_grok_sensor", "fetch_grok_intel")
XHSRadar, XHS_AVAILABLE = _safe_import("sensors.xhs_radar", "XHSRadar")

# --- 反幻觉：链接验证器 ---
try:
    from utils.verifier import verify_link
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


def _fetch_hn_task(limit):
    """HN 获取任务"""
    results = []
    stories = _fetch_hn(limit=limit)
    for s in stories:
        results.append({
            "title": s.title,
            "url": s.url or s.hn_url,
            "heat": f"{s.score} points",
            "time": f"{s.descendants} comments",
            "category": "Hacker News",
        })
    return "tech_trends", results


def _fetch_github_task(limit):
    """GitHub 获取任务"""
    results = []
    trends = _fetch_github()
    for t in trends[:limit]:
        results.append({
            "title": t.name,
            "url": t.url,
            "heat": f"{t.stars} stars",
            "time": t.created_at[:10] if t.created_at else "",
            "category": "GitHub",
        })
    return "tech_trends", results


def _fetch_36kr_task(limit):
    """36Kr 获取任务"""
    results = []
    items = _fetch_36kr(limit=limit)
    for a in items:
        results.append({
            "title": a.title, "url": a.url,
            "time": a.published, "category": "36Kr",
        })
    return "capital_flow", results


def _fetch_wscn_task(limit):
    """华尔街见闻获取任务"""
    results = []
    items = _fetch_wscn(limit=limit)
    for a in items:
        results.append({
            "title": a.title, "url": a.url,
            "time": a.published, "category": "WallStreetCN",
        })
    return "capital_flow", results


def _fetch_v2ex_task(limit):
    """V2EX 获取任务"""
    results = []
    radar = V2EXRadar()
    leads = radar.fetch_leads(days=1)
    for lead in leads[:limit]:
        results.append({
            "title": lead.title, "url": lead.url,
            "heat": f"Score: {lead.desperation_score}",
            "category": "V2EX",
        })
    return "community", results


def _fetch_ph_task(limit):
    """Product Hunt 获取任务"""
    results = []
    products = fetch_trending_products(limit)
    for p in products:
        results.append({
            "source": "Product Hunt",
            "category": "Product Hunt",
            "title": p.name,
            "url": p.url,
            "heat": f"{p.votes_count} votes",
            "time": "Today",
            "tagline": p.tagline,
            "grok_review": None,
        })
    return "product_gems", results


def _fetch_arxiv_task(limit):
    """ArXiv 获取任务"""
    results = []
    papers = fetch_ai_papers(limit=limit)
    for p in papers:
        results.append({
            "source": "ArXiv",
            "category": "ArXiv",
            "title": p.title,
            "url": p.url,
            "authors": ", ".join(p.authors[:2]),
            "time": p.published,
            "categories": ", ".join(p.categories[:2]),
        })
    return "research", results


def _fetch_grok_task(_limit):
    """Grok/X 获取任务"""
    results = []
    report = fetch_grok_intel("AI Agents, LLM, Tech Startups")
    if report and "Error" not in report:
        validated = validate_grok_report(report)
        results.append({
            "source": "X (via Grok)",
            "category": "X/Grok",
            "content": validated,
            "type": "markdown_report",
        })
        logger.info("Grok 返回 X 情报报告（链接已验证）")
    else:
        logger.warning("Grok 未返回数据或出错")
    return "social", results


def _fetch_xhs_task(_limit):
    """小红书获取任务"""
    results = []
    radar = XHSRadar()
    leads = radar.fetch_leads()
    for lead in leads[:8]:
        results.append({
            "source": "小红书",
            "category": "XHS",
            "title": lead.title,
            "url": lead.url,
            "summary": lead.summary,
        })
    return "xhs_directives", results


def fetch_all_sources(limit_per_source: int = 10) -> dict:
    """使用 ThreadPoolExecutor 并行获取所有数据源"""
    intel = {
        "tech_trends": [],
        "capital_flow": [],
        "product_gems": [],
        "community": [],
        "research": [],
        "social": [],
        "xhs_directives": [],
    }

    # 构建任务列表：(任务函数, 名称, 是否可用)
    tasks = [
        (_fetch_hn_task, "Hacker News", HN_AVAILABLE),
        (_fetch_github_task, "GitHub", GH_AVAILABLE),
        (_fetch_36kr_task, "36Kr", KR_AVAILABLE),
        (_fetch_wscn_task, "WallStreetCN", WSCN_AVAILABLE),
        (_fetch_v2ex_task, "V2EX", V2EX_AVAILABLE),
        (_fetch_ph_task, "Product Hunt", PH_AVAILABLE),
        (_fetch_arxiv_task, "ArXiv", ARXIV_AVAILABLE),
        (_fetch_grok_task, "Grok/X", GROK_AVAILABLE),
        (_fetch_xhs_task, "XHS", XHS_AVAILABLE),
    ]

    available_tasks = [
        (fn, name) for fn, name, avail in tasks if avail
    ]

    logger.info(
        "并行获取 %d 个数据源: %s",
        len(available_tasks),
        ", ".join(n for _, n in available_tasks),
    )

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(fn, limit_per_source): name
            for fn, name in available_tasks
        }

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                category, results = future.result()
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
            time_str = item.get("time", "")
            cat = item.get("category", "")
            
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"📍 {cat} | 🔥 {heat} | 🕒 {time_str}")
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
            time_str = item.get("time", "")
            cat = item.get("category", "")
            
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"📍 {cat} | 🕒 {time_str}")
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
            authors = item.get("authors", "")
            time_str = item.get("time", "")
            
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
            tagline = item.get("tagline", "")
            grok_review = item.get("grok_review")
            
            lines.append(f"### {i}. [{title}]({url})")
            lines.append(f"> {tagline}")
            lines.append(f"🔥 {heat}")
            lines.append("")
            
            # Add Grok sentiment review if available (for top 3)
            if grok_review:
                lines.append(f"> **🦅 Grok 舆情核查**: {grok_review}")
                lines.append("")
    else:
        lines.append("*暂无数据 (Product Hunt API 可能需要配置)*\n")
    
    # --- Social (X/Twitter) ---
    lines.append("## 🐦 社交热议 (Social)")
    lines.append("> X (Twitter) - AI/Tech Discussions\n")
    
    if intel.get("social"):
        for item in intel["social"]:
            # Check if it's a Grok markdown report
            if item.get("type") == "markdown_report":
                lines.append(f"> 来源: {item.get('source', 'X')}\n")
                lines.append(item.get("content", "*无内容*"))
                lines.append("")
            else:
                # Old format (individual posts)
                title = item.get("title", "")
                url = item.get("url", "#")
                author = item.get("author", "")
                heat = item.get("heat", "")
                
                lines.append(f"### {author}")
                lines.append(f"> {title}")
                lines.append(f"❤️ {heat} | 🔗 [Link]({url})")
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
