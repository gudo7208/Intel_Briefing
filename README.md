# Intel Briefing - AI 情报聚合系统

<p align="center">
  <strong>用 AI 帮你每天追踪 Tech 热点、产品趋势、学术前沿、财经动态</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Docker-lightgrey" alt="Platform">
</p>

---

## 功能特性

- **Hacker News** - 每日热门技术讨论
- **Product Hunt** - 最新产品发布追踪
- **arXiv** - AI/ML 前沿论文速递
- **GitHub Trending** - 热门开源项目（爆发型仓库检测）
- **Chrome 扩展商店** - 新兴插件雷达
- **V2EX** - 中文开发者社区动态
- **小红书** - 趋势话题采集
- **X (Twitter)** - 通过 Grok API 分析舆情
- **华尔街见闻** - 实时财经新闻
- **36Kr** - 科技商业热榜

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/77AutumN/Intel_Briefing.git
cd Intel_Briefing
```

### 2. 安装依赖

#### Linux (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### macOS

```bash
# 使用 Homebrew 安装 Python（如未安装）
brew install python@3.10

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

**需要的 API Key：**

| Key | 用途 | 是否必须 | 获取地址 |
|-----|------|----------|----------|
| `GITHUB_TOKEN` | GitHub Trending | 可选 | [GitHub Settings](https://github.com/settings/tokens) |
| `PRODUCTHUNT_TOKEN` | Product Hunt 数据 | 可选 | [PH Developer](https://www.producthunt.com/v2/oauth/applications) |
| `XAI_API_KEY` | X/Grok 舆情分析 | 可选 | [xAI Console](https://console.x.ai/) |

> 没有 API Key 的传感器会自动跳过或使用回退方案，不影响其他模块运行。

### 4. 运行

```bash
# 获取每日情报简报
python run_mission.py

# 战术狩猎（高价值机会）
python run_bounty_hunter.py

# Web3 Alpha 雷达
python run_alpha_radar.py

# 收入架构师（机会分析）
python run_revenue_architect.py
```

---

## Docker 使用

### 使用 Docker 直接运行

```bash
# 构建镜像
docker build -t intel-briefing .

# 运行（需要先配置 .env 文件）
docker run --env-file .env -v $(pwd)/reports:/app/reports intel-briefing
```

### 使用 Docker Compose

```bash
# 单次运行情报报告
docker compose run intel-report

# 启动定时任务（每天早上 8 点自动执行）
docker compose up -d cron

# 查看日志
docker compose logs -f cron
```

---

## 三司架构

| 部门 | 入口脚本 | 输出目录 | 职责 |
|------|----------|----------|------|
| **战略部** | `run_mission.py` | `reports/daily_briefings/` | 每日晨报 |
| **战术部** | `run_bounty_hunter.py` | `reports/tactical/` | Hit List |
| **Web3部** | `run_alpha_radar.py` | `reports/web3/` | Alpha Leak |
| **收入部** | `run_revenue_architect.py` | `reports/opportunities/` | 机会分析 |

---

## 项目结构

```
Intel_Briefing/
├── src/
│   ├── sensors/                  # 数据采集模块（传感器）
│   │   ├── base.py               # 传感器基类 + 缓存 + 重试机制
│   │   ├── hacker_news.py        # Hacker News 传感器
│   │   ├── product_hunt.py       # Product Hunt 传感器
│   │   ├── arxiv_ai.py           # arXiv AI/ML 论文传感器
│   │   ├── github_trending.py    # GitHub 爆发型仓库传感器
│   │   ├── chrome_radar.py       # Chrome 扩展商店雷达
│   │   ├── v2ex_radar.py         # V2EX 社区线索雷达
│   │   ├── xhs_radar.py          # 小红书趋势雷达
│   │   ├── x_grok_sensor.py      # X/Grok AI 舆情传感器
│   │   ├── x_twitter.py          # X (Twitter) 浏览器采集
│   │   ├── wallstreetcn_sensor.py # 华尔街见闻传感器
│   │   └── kr36_sensor.py        # 36Kr 传感器
│   ├── generators/               # 报告生成器
│   │   └── curator.py            # 仓库分析 & 商业简报生成
│   └── utils/                    # 工具模块
│       └── verifier.py           # 链接验证器
├── tests/                        # 单元测试
│   └── test_sensors.py           # 传感器测试
├── .github/workflows/            # CI/CD 流水线
│   └── ci.yml                    # Lint + Test
├── reports/                      # 生成的报告（git ignored）
├── .agent/                       # Antigravity Agent 配置
├── docs/                         # 文档
├── run_mission.py                # 每日情报主入口
├── run_bounty_hunter.py          # 战术狩猎
├── run_alpha_radar.py            # Web3 Alpha 雷达
├── run_revenue_architect.py      # 收入架构师
├── fetch_unified_intel.py        # 统一情报获取
├── Dockerfile                    # Docker 镜像定义
├── docker-compose.yml            # Docker Compose 编排
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
└── CHANGELOG.md                  # 变更日志
```

---

## 传感器列表

| 模块 | 数据源 | 需要 API Key | 更新频率 | 基类 |
|------|--------|-------------|----------|------|
| `hacker_news.py` | Hacker News (Firebase API) | 否 | 每日 | BaseSensor |
| `product_hunt.py` | Product Hunt (GraphQL + 回退) | 可选 | 每日 | BaseSensor |
| `arxiv_ai.py` | arXiv (官方 API) | 否 | 每日 | BaseSensor |
| `github_trending.py` | GitHub (GraphQL API) | 是 | 每日 | BaseSensor |
| `chrome_radar.py` | Chrome Web Store | 否 | 每周 | BaseSensor |
| `v2ex_radar.py` | V2EX (RSS) | 否 | 每日 | BaseSensor |
| `xhs_radar.py` | 小红书 (手动模式) | 否 | 每日 | BaseSensor |
| `x_grok_sensor.py` | X/Grok (xAI API) | 是 | 每日 | BaseSensor |
| `wallstreetcn_sensor.py` | 华尔街见闻 (公开 API) | 否 | 实时 | BaseSensor |
| `kr36_sensor.py` | 36Kr (公开 API) | 否 | 实时 | BaseSensor |

---

## 开发者贡献指南

### 如何添加新 Sensor

所有传感器继承自 `BaseSensor`（定义在 `src/sensors/base.py`），遵循统一接口。

#### 第一步：创建传感器文件

在 `src/sensors/` 下新建文件，例如 `my_sensor.py`：

```python
import logging
from typing import List
from sensors.base import BaseSensor, SensorResult

logger = logging.getLogger(__name__)


class MySensor(BaseSensor):
    """我的自定义传感器"""

    @property
    def name(self) -> str:
        return "My Source"

    def is_available(self) -> bool:
        """检查传感器是否可用（如需要 API Key 则在此检查）"""
        return True

    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据，返回统一格式的 SensorResult 列表"""
        # 你的数据获取逻辑
        results = []
        # ...
        return [
            SensorResult(
                title="标题",
                url="https://example.com",
                source="My Source",
                category="tech_trends",  # 分类
                heat="100 points",       # 热度指标
                timestamp="2025-01-01",  # 发布时间
                summary="摘要",
                metadata={},             # 额外数据
            )
        ]
```

#### 第二步：使用内置工具

`base.py` 提供了以下工具，无需重复实现：

- **`retry_request(func)`** - 带指数退避的 HTTP 重试（处理 429/5xx）
- **`cached_fetch(key, fetcher, ttl)`** - 文件缓存（默认 30 分钟 TTL）
- **`fetch_with_cache(limit, ttl)`** - BaseSensor 内置的缓存 fetch

#### 第三步：注册到主流程

在 `run_mission.py` 或 `fetch_unified_intel.py` 中导入并添加你的传感器。

#### 第四步：添加测试

在 `tests/test_sensors.py` 中添加基本测试：

```python
from sensors.my_sensor import MySensor

def test_my_sensor_import():
    sensor = MySensor()
    assert sensor.name == "My Source"
    assert sensor.is_available()
```

### 开发规范

- 所有传感器必须继承 `BaseSensor`，实现 `name` 属性和 `fetch()` 方法
- 返回数据统一使用 `SensorResult` 数据类
- 使用 `logging` 模块记录日志，**禁止** print/log 输出 API Key
- 依赖写入 `requirements.txt`，**禁止**在代码中自动 `pip install`
- HTTP 请求使用 `httpx`，配合 `retry_request()` 处理重试

---

## 与 Antigravity Agent 配合使用

本项目设计为 [Google Antigravity](https://idx.dev/antigravity) 的 **Skill**，可以直接对 Agent 说：

```
"给我今日报告"
"看一下今天的晨报，帮我找赚钱机会"
"/daily-report"
```

---

## License

MIT License - 自由使用，欢迎 PR！
