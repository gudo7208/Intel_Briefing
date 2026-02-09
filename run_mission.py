import sys
import os
import argparse
import datetime
import logging
from fetch_unified_intel import fetch_all_sources, generate_report as generate_v2_report
from src.notify.telegram_bot import TelegramNotifier
from src.notify.discord_webhook import DiscordNotifier

logger = logging.getLogger(__name__)

# Configuration
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "daily_briefings")


def dispatch_notifications(report_file: str, report_title: str):
    """报告生成后，自动通过所有已配置的渠道推送通知。

    Args:
        report_file: 报告文件的本地路径。
        report_title: 报告标题，用于通知摘要。
    """
    notifiers = [TelegramNotifier(), DiscordNotifier()]

    # 过滤出已配置的通知渠道
    active = [n for n in notifiers if n.is_configured()]
    if not active:
        print("📭 未配置任何通知渠道，跳过推送")
        return

    summary = f"📊 *{report_title}*\n\n情报简报已生成，详见附件。"

    for notifier in active:
        try:
            # 先发送摘要文本
            notifier.send_text(summary)
            # 再发送完整报告文件
            notifier.send_file(report_file, caption=report_title)
            print(f"📤 已通过 {notifier.name} 推送通知")
        except Exception as e:
            logger.error("通过 %s 推送失败: %s", notifier.name, e)
            print(f"⚠️  {notifier.name} 推送失败: {e}")


def generate_morning_report(days: int = 1):
    """
    Orchestrate the collection of intelligence using Unified Engine V2.
    Supports Daily (days=1) or Weekly/Custom (days>1) briefings.
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Determine Report Type
    if days == 1:
        report_title = f"每日商业情报简报: {date_str}"
        file_name = f"Morning_Report_{date_str}.md"
        limit = 15
    else:
        report_title = f"周期性情报简报 (过去 {days} 天): {date_str}"
        file_name = f"Weekly_Report_{days}Days_{date_str}.md"
        limit = 30  # Fetch more for weekly
        
    report_file = os.path.join(REPORT_DIR, file_name)
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    print(f"🚀 开始生成情报简报 (Unified V2) - 周期: {days} 天...")
    print(f"   目标文件: {file_name}")
    print(f"   抓取数量: {limit}/源")
    
    # 1. Fetch from all 9 sources
    intel = fetch_all_sources(limit_per_source=limit)
    
    # 2. Generate Report using V2 Renderer
    # Note: generate_v2_report returns a string. We might need to wrap it with the custom title.
    body = generate_v2_report(intel, date_str)
    
    # Replace the default title with our custom one if needed, or just prepend
    final_content = f"# {report_title}\n\n" + body.replace("# 🌐 全球情报日报 (Global Intel Briefing)", "")
    
    # 3. Save
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"\n✅ 简报已生成: {report_file}")

    # 4. 推送通知到已配置的渠道
    dispatch_notifications(report_file, report_title)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成商业情报简报 (Unified V2)")
    parser.add_argument("days", nargs="?", type=int, default=1, help="分析天数 (默认: 1)")
    args = parser.parse_args()
    
    generate_morning_report(days=args.days)
