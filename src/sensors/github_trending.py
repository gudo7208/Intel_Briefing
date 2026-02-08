"""
GitHub Trending Sensor - 使用 GitHub GraphQL API 查找高潜力仓库。
聚焦"爆发型"仓库：近期创建且 star 增速快。
"""

import os
import sys
import logging
import datetime
from dataclasses import dataclass, field
from typing import Optional

# 优先使用 httpx，回退到 requests
try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    try:
        import requests
        HTTP_CLIENT = "requests"
    except ImportError:
        HTTP_CLIENT = None

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/graphql"

@dataclass
class GitHubTrend:
    """A single trending repository."""
    name: str                   # e.g., "owner/repo"
    url: str
    description: str
    language: Optional[str]
    stars: int
    forks: int
    created_at: str
    pushed_at: str
    readme_text: Optional[str] = None  # Fetched via GraphQL
    hype_score: int = field(init=False)

    def __post_init__(self):
        # Calculate hype: stars relative to age would be cool, 
        # but for now simple log scale of stars for "recently created" items
        import math
        # If it's new (search query ensures this), raw stars is a good proxy for hype
        self.hype_score = min(100, int(math.log10(max(self.stars, 1)) * 25))

def load_env_token() -> Optional[str]:
    """Load GITHUB_TOKEN from .env file manually."""
    # Strategy: Start with relative path, fallback to CWD
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    
    for env_path in candidates:
        if os.path.exists(env_path):
            try:
                # utf-8-sig handles BOM which is common on Windows
                with open(env_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        
                        # Case 1: Standard Key=Value
                        if "GITHUB_TOKEN=" in line:
                            return line.split("=", 1)[1].strip()
                            
                        # Case 2: Raw Token (User just pasted the token)
                        if line.startswith("ghp_") or line.startswith("github_pat_"):
                            return line
            except Exception:
                pass
                
    return os.environ.get("GITHUB_TOKEN")

def fetch_trending(language: Optional[str] = None) -> list[GitHubTrend]:
    """
    Fetch trending repositories using GitHub GraphQL API.
    Strategy: Search for repos created in the last 7 days, sorted by stars.
    """
    token = load_env_token()
    if not token:
        logger.error("未找到 GITHUB_TOKEN")
        return []

    if HTTP_CLIENT is None:
        logger.error("无可用 HTTP 客户端，请安装 httpx 或 requests")
        return []

    # Calculate date 7 days ago
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Build Search Query
    # Query: "created:>YYYY-MM-DD sort:stars"
    search_query = f"created:>{seven_days_ago} sort:stars"
    if language:
        search_query += f" language:{language}"

    graphql_query = """
    query($search_query: String!) {
      search(query: $search_query, type: REPOSITORY, first: 10) {
        edges {
          node {
            ... on Repository {
              nameWithOwner
              url
              description
              stargazerCount
              forkCount
              createdAt
              pushedAt
              primaryLanguage {
                name
              }
              object(expression: "HEAD:README.md") {
                ... on Blob {
                  text
                }
              }
            }
          }
        }
      }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Commercial-Agent-Sensor"
    }

    payload = {
        "query": graphql_query,
        "variables": {"search_query": search_query}
    }
    
    try:
        logger.info("正在发送 GraphQL 查询到 GitHub (%s)...", search_query)
        if HTTP_CLIENT == "httpx":
            response = httpx.post(GITHUB_API_URL, json=payload, headers=headers, timeout=30.0)
        else:
            response = requests.post(GITHUB_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error("API 返回 %d", response.status_code)
            logger.debug(response.text)
            return []
            
        data = response.json()
        if "errors" in data:
            logger.error("GraphQL 错误: %s", data['errors'])
            return []

        return _parse_graphql_response(data)

    except Exception as e:
        logger.error("请求失败: %s", e)
        return []

def _parse_graphql_response(data: dict) -> list[GitHubTrend]:
    trends = []
    edges = data.get("data", {}).get("search", {}).get("edges", [])
    
    for edge in edges:
        node = edge.get("node")
        if not node:
            continue
            
        # Extract README
        readme_obj = node.get("object")
        readme_text = readme_obj.get("text", "") if readme_obj else ""
            
        trends.append(GitHubTrend(
            name=node["nameWithOwner"],
            url=node["url"],
            description=node["description"] or "(No description)",
            language=node["primaryLanguage"]["name"] if node["primaryLanguage"] else None,
            stars=node["stargazerCount"],
            forks=node["forkCount"],
            created_at=node["createdAt"],
            pushed_at=node["pushedAt"],
            readme_text=readme_text[:5000]  # Truncate to save memory/tokens
        ))
        
    return trends

def print_trends(trends: list[GitHubTrend]) -> None:
    print(f"\n{'='*60}")
    print(f" 🚀 Breakout Repos (Last 7 Days) - Top {len(trends)}")
    print(f"{'='*60}\n")

    for i, t in enumerate(trends, 1):
        print(f"{i}. [{t.hype_score:3d}] {t.name}")
        print(f"   ⭐ {t.stars} | 🍴 {t.forks} | Created: {t.created_at[:10]}")
        if t.language:
            print(f"   📝 {t.language}")
        print(f"   {t.description[:100]}...")
        print(f"   🔗 {t.url}")
        print()

def trigger_ghostwriter(trend: GitHubTrend):
    """Invoke the Ghostwriter skill to draft an article."""
    import subprocess
    import tempfile
    
    logger.info("正在触发 Curator 分析 %s...", trend.name)
    
    # Create temp file for readme context
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', suffix='.txt') as f:
        f.write(trend.readme_text or "(No README)")
        readme_path = f.name
        
    try:
        # Call the Curator script
        script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Generators", "Curator", "curator.py")
        script_path = os.path.abspath(script_path)
        
        # Clean name for filename
        safe_name = trend.name.replace('/', '_')
        output_name = f"{safe_name}_briefing.md"
        
        cmd = [
            sys.executable, script_path,
            "--repo-name", trend.name,
            "--readme", readme_path,
            "--output", output_name
        ]
        
        # Run it
        subprocess.run(cmd, check=True)
        
    except Exception as e:
        logger.error("Curator 失败: %s", e)
    finally:
        os.unlink(readme_path)

if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else None
    trends = fetch_trending(lang)
    if trends:
        print_trends(trends)
        
        # MVP: Auto-trigger for the Top 1 item
        top_trend = trends[0]
        print(f"\n[Commercial Agent] 🧠 Automatically analyzing top opportunity: {top_trend.name}")
        trigger_ghostwriter(top_trend)
        
    else:
        print("No trends found.")
