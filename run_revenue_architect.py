import os
import sys
import glob
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 stdout (may fail on some Linux systems)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass

# Load environment variables
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
ENV_PATHS = [
    PROJECT_ROOT / ".env",
]
for p in ENV_PATHS:
    if p.exists():
        load_dotenv(p)

# 导入 LLM 抽象层
from src.llm.factory import get_llm_provider

# Paths (relative to project root)
INTEL_DIR = PROJECT_ROOT / "reports" / "daily_briefings"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "opportunities"
SKILL_PROMPT_PATH = PROJECT_ROOT / ".agent" / "skills" / "revenue-architect" / "prompts" / "commercial_logic.md"

def query_llm(system_prompt: str, user_input: str) -> str:
    """通过 LLM 抽象层发送请求，自动选择配置的 Provider。"""
    try:
        llm = get_llm_provider()
        return llm.analyze(system_prompt, user_input, timeout=90)
    except Exception as e:
        return f"⚠️ LLM 调用失败: {e}"

def get_latest_briefing() -> Path:
    """Find the most recent Daily Briefing markdown file."""
    # Pattern: Morning_Report_*.md and Weekly_Report_*.md
    files = list(INTEL_DIR.glob("*_Report_*.md"))
    if not files:
        return None
    # Sort by name (which contains date) descending
    files.sort(key=lambda x: x.name, reverse=True)
    return files[0]

def run_revenue_architect(test_mode: bool = False):
    print("🏗️ Revenue Architect: Initializing...")
    
    # 1. Get Input Data
    if test_mode:
        print("🧪 TEST MODE: Using Mock Data")
        intel_content = """
        # Daily Briefing Mock Data (Expanded for Testing)
        
        ## 1. DeepSeek-V3 API Released
        DeepSeek has released their V3 model API. It is claimed to be 50% cheaper than GPT-4o while offering comparable performance on coding tasks. 
        The context window is 128k tokens. Developers are flocking to it for building low-cost agents.
        
        ## 2. OpenAI Search Goes Paid
        OpenAI has moved their 'SearchGPT' feature behind the Plus paywall effectively. This creates a gap for free, ad-supported search wrappers or niche search tools.
        
        ## 3. Cursor Editor Plugins
        The Cursor AI code editor is seeing a massive surge in plugin development. Users are asking for 'Voice Coding' and 'Figma to Cursor' bridges.
        
        ## 4. Solana Agent Frameworks
        New frameworks for deploying AI agents on Solana are trending. 'Eliza' framework allows agents to hold wallets and trade tokens autonomously.
        
        ## 5. Super-Individual Trends
        More designers are using 'Midjourney + Runway' to create full short films alone. The tooling is ready for 'One Person Netflix'.
        """
        date_str = "TEST_RUN"
    else:
        briefing_file = get_latest_briefing()
        if not briefing_file:
            print("❌ No briefing reports found in:", INTEL_DIR)
            return

        print(f"📄 Reading Intelligence: {briefing_file.name}")
        intel_content = briefing_file.read_text(encoding='utf-8')
        date_str = datetime.date.today().strftime("%Y-%m-%d")

    # 2. Circuit Breaker
    if len(intel_content) < 200:
        print("⚠️ Intel too sparse (<200 chars). Skipping execution.")
        return

    # 3. Load Skill Brain
    if not SKILL_PROMPT_PATH.exists():
        print(f"❌ Skill Prompt not found at: {SKILL_PROMPT_PATH}")
        return
    
    system_prompt = SKILL_PROMPT_PATH.read_text(encoding='utf-8')

    # 4. Execute
    # 通过 LLM 抽象层获取当前 Provider 信息
    try:
        llm = get_llm_provider()
        model_info = f"{llm.name} ({getattr(llm, 'model', 'N/A')})"
    except Exception:
        model_info = "未知"
    print(f"🧠 Analyzing Intel with Model: {model_info}...")
    mission_plan = query_llm(
        system_prompt=system_prompt,
        user_input=f"Here is the latest Intelligence Report. Identify actionable Antigravity Missions:\n\n{intel_content}"
    )
    
    # 5. Output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("--- RAW LLM RESPONSE START ---")
    print(mission_plan)
    print("--- RAW LLM RESPONSE END ---")
    
    if "NO OPPORTUNITY DETECTED" in mission_plan:
        print("💤 Revenue Architect found no opportunities today.")
        return

    output_file = OUTPUT_DIR / f"{date_str}_Mission_Plan.md"
    output_file.write_text(mission_plan, encoding='utf-8')
    
    print("\n" + "="*50)
    print(f"✅ Mission Plan Generated: {output_file}")
    print("="*50)
    print("👉 ACTION: Open the file and copy the 'Antigravity Execution Prompts'.")

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_revenue_architect(test_mode=True)
    else:
        run_revenue_architect()
