# Intel Briefing - Comprehensive Optimization Plan

> **Author**: Architecture Review
> **Date**: 2026-02-09
> **Branch**: `feature/cross-platform-support`
> **Scope**: Full codebase analysis — 22 Python files, 11 sensors, 6 entry points

## Priority Legend

| Priority | Meaning |
|----------|---------|
| **P0** | Critical — Blocks reliability or causes failures |
| **P1** | High — Significant quality/performance improvement |
| **P2** | Medium — Good engineering practice |
| **P3** | Nice-to-have — Future enhancement |

| Effort | Meaning |
|--------|---------|
| **S** | Small — A few hours |
| **M** | Medium — 1-2 days |
| **L** | Large — 3-5 days |

---

## Table of Contents

1. [Architecture & Code Quality](#1-architecture--code-quality)
2. [Performance](#2-performance)
3. [Reliability & Resilience](#3-reliability--resilience)
4. [DevOps & Deployment](#4-devops--deployment)
5. [Security](#5-security)
6. [New Feature Ideas](#6-new-feature-ideas)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Architecture & Code Quality

### 1.1 Hardcoded Windows Paths — `P0 / S`

**Files**: `src/generators/curator.py:68`, `fetch_ph_clean.py:13`

**Problem**: Hardcoded `D:\` paths break on Linux/macOS:

- `curator.py:68`: `STUDIO_PATH = r"D:\Intel_Briefing"`
- `fetch_ph_clean.py:13`: `sys.path.append(os.path.join(os.getcwd(), 'd:\\Intel_Briefing\\src'))`

**Solution**: Replace with `Path(__file__).resolve().parent` relative paths throughout.

### 1.2 No Sensor Base Class / Interface — `P1 / M`

**Files**: All 11 files in `src/sensors/`

**Problem**: Every sensor is standalone with no shared interface. Mixed patterns:

| Sensor | Style | Return Type |
|--------|-------|-------------|
| `hacker_news.py` | bare function `fetch_top_stories()` | `List[HNStory]` |
| `v2ex_radar.py` | class `V2EXRadar.fetch_leads()` | `List[Lead]` |
| `chrome_radar.py` | class `ChromeRadar.scan_opportunities()` | `List[ChromeAssetOpportunity]` |
| `xhs_radar.py` | class `XHSRadar.fetch_leads()` | `List[Lead]` |
| `product_hunt.py` | bare function `fetch_trending_products()` | `List[PHProduct]` |
| `kr36_sensor.py` | bare function `fetch_36kr()` | `List[KrArticle]` |
| `wallstreetcn_sensor.py` | bare function `fetch_wallstreetcn()` | `List[WSCNArticle]` |
| `arxiv_ai.py` | bare function `fetch_ai_papers()` | `List[ArxivPaper]` |
| `x_grok_sensor.py` | bare function `fetch_grok_intel()` | raw `str` |
| `github_trending.py` | bare function `fetch_trending()` | `list[GitHubTrend]` |
| `x_twitter.py` | cache-based `load_cached_posts()` | `List[XPost]` |

This forces `fetch_unified_intel.py:25-96` to use 9 separate try/except blocks with individual `_AVAILABLE` booleans.

**Solution**: Create `src/sensors/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

@dataclass
class SensorResult:
    title: str
    url: str
    source: str
    category: str
    heat: str = ""
    timestamp: str = ""
    summary: str = ""
    metadata: dict = field(default_factory=dict)

class BaseSensor(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def fetch(self, limit: int = 10) -> List[SensorResult]: ...

    def is_available(self) -> bool:
        return True
```

### 1.3 Duplicated .env Loading Logic — `P1 / S`

**Files**: `product_hunt.py:33-54`, `x_grok_sensor.py:14-15`, `run_revenue_architect.py:18-24`, `github_trending.py:51-78`

**Problem**: Four different implementations of "find and load .env":

1. `product_hunt.py:33-54` — Manual file parsing, searches 3 hardcoded paths, handles BOM
2. `x_grok_sensor.py:14-15` — `load_dotenv()` with no path (relies on cwd)
3. `run_revenue_architect.py:18-24` — Iterates `ENV_PATHS` list
4. `github_trending.py:51-78` — Custom `load_env_token()` with manual line parsing

**Solution**: Centralize in `src/utils/config.py`:

```python
from pathlib import Path
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def init_env():
    load_dotenv(PROJECT_ROOT / ".env")

def get_required(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val
```

### 1.4 sys.path Manipulation Instead of Proper Packages — `P1 / M`

**Files**: `run_bounty_hunter.py:9`, `run_alpha_radar.py:7-10`, `fetch_unified_intel.py:20-22`, `fetch_ph_clean.py:7,13`

**Problem**: Every entry point hacks `sys.path`:

```python
# run_bounty_hunter.py:9
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "sensors"))
# run_alpha_radar.py:7-8
sys.path.append(os.path.join(os.path.dirname(__file__), "src", "sensors"))
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
```

This causes import inconsistencies — some files use `from sensors.hacker_news import ...`, others use bare `from hacker_news import ...`.

**Solution**: Add `pyproject.toml` with `pip install -e .` so all imports become `from src.sensors.hacker_news import ...`.

### 1.5 print() Instead of Proper Logging — `P1 / M`

**Files**: All 22 `.py` files

**Problem**: The entire codebase uses `print()` for debug, errors, warnings, and status. Examples:

- `fetch_unified_intel.py:150`: `print("[*] Fetching Hacker News...")`
- `fetch_unified_intel.py:162`: `print(f"  [WARN] HN failed: {e}")`
- `x_grok_sensor.py:83-85`: Prints entire Grok API response to stdout
- `run_revenue_architect.py:134-136`: Prints raw LLM response between markers

No way to control verbosity, redirect logs, or distinguish errors from info.

**Solution**: Use Python `logging` module with `src/utils/log.py` setup function.

### 1.6 Duplicate `Lead` Dataclass — `P2 / S`

**Files**: `src/sensors/v2ex_radar.py:17-24`, `src/sensors/xhs_radar.py:13-21`

**Problem**: Identical `Lead` dataclass defined in both files. `run_bounty_hunter.py:12` imports `Lead` from `v2ex_radar`, creating hidden coupling.

**Solution**: Move `Lead` to `src/sensors/base.py` or `src/models.py`.

### 1.7 Monolithic `fetch_unified_intel.py` — `P2 / M`

**Files**: `fetch_unified_intel.py` (517 lines)

**Problem**: Three unrelated responsibilities:
1. Sensor imports + availability checks (lines 25-96)
2. Orchestration in `fetch_all_sources()` (lines 136-317)
3. Report rendering in `generate_report()` (lines 320-468, 148 lines of string concatenation)

**Solution**: Split into:
- `src/orchestrator.py` — sensor registry + parallel fetch
- `src/renderers/markdown.py` — report generation
- Keep `fetch_unified_intel.py` as thin CLI entry point

### 1.8 Auto-installing Dependencies at Import Time — `P2 / S`

**Files**: `hacker_news.py:13-14`, `arxiv_ai.py:13-14`, `product_hunt.py:15-16`, `kr36_sensor.py:13-14`, `wallstreetcn_sensor.py:13-14`

**Problem**: Five sensors auto-run `pip install httpx` on import failure:

```python
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx
```

This is a side-effect at import time, breaks in locked environments, and is a security concern.

**Solution**: Add `requirements.txt` (or `pyproject.toml` dependencies) and remove auto-install blocks.

---

## 2. Performance

### 2.1 Sequential API Calls in `fetch_all_sources()` — `P0 / M`

**Files**: `fetch_unified_intel.py:136-317`

**Problem**: All 9 sensors are called sequentially. Each makes 1+ HTTP requests with 10-60s timeouts. Worst-case request count per run:

| Sensor | HTTP Calls | Timeout |
|--------|-----------|---------|
| HN | 11 (1 list + 10 items) | 10-15s each |
| GitHub | 1 GraphQL | 30s |
| 36Kr | 1-2 (primary + fallback) | 15s |
| WallStreetCN | 1-2 (primary + fallback) | 15s |
| V2EX | 2 (2 RSS feeds) | 15s |
| Product Hunt | 1-2 (API + fallback) | 15s |
| ArXiv | 1 | 30s |
| Grok/X general | 1 | 60s |
| Grok PH sentiment x3 | 3 | 60s each |
| XHS | 0 (URL generation only) | — |

**Total worst-case**: ~23 sequential HTTP requests, 3-5 minutes wall time.

**Solution**: Use `concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_all_sources(limit: int = 10) -> dict:
    sensors = [s for s in registry if s.is_available()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(s.fetch, limit): s for s in sensors}
        for future in as_completed(futures):
            sensor = futures[future]
            try:
                results = future.result(timeout=60)
                intel[sensor.category].extend(results)
            except Exception as e:
                logger.warning("%s failed: %s", sensor.name, e)
```

**Impact**: Reduces total fetch time from ~3-5 min to ~60s (bounded by slowest sensor, Grok at 60s timeout).

### 2.2 Hacker News N+1 HTTP Problem — `P1 / S`

**Files**: `src/sensors/hacker_news.py:36-51`

**Problem**: Fetching N stories requires N+1 HTTP calls — 1 for the ID list, then 1 per story sequentially:

```python
# hacker_news.py:40-41
for sid in story_ids:
    item_resp = httpx.get(f".../{sid}.json", timeout=10)
```

For `limit=10`, that's 11 sequential requests with 10s timeout each.

**Solution**: Fetch story details in parallel with `ThreadPoolExecutor` or `asyncio.gather()`.

**Impact**: Reduces HN fetch from ~10s to ~1-2s.

### 2.3 Chrome Web Store Sequential Scraping — `P2 / S`

**Files**: `src/sensors/chrome_radar.py:49-121`

**Problem**: `scan_opportunities()` visits each extension detail page sequentially with `time.sleep(random.uniform(0.5, 1.5))` (line 112). For 20 low-rated extensions, this adds 10-30s of pure sleep.

**Solution**: Batch detail-page requests with a semaphore (max 3 concurrent) to stay polite while reducing wall time.

### 2.4 No Caching Layer — `P2 / M`

**Files**: All sensors

**Problem**: Every run fetches everything from scratch. If the script crashes during report generation, all fetched data is lost. The only caching is `x_twitter.py:28` (manual browser workflow, not automated).

**Solution**: Add file-based cache with TTL in `src/utils/cache.py`:

```python
import json, hashlib, time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".cache"

def cached_fetch(key: str, fetcher, ttl_seconds: int = 3600):
    cache_file = CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        if time.time() - data["ts"] < ttl_seconds:
            return data["payload"]
    result = fetcher()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"ts": time.time(), "payload": result}))
    return result
```

---

## 3. Reliability & Resilience

### 3.1 No Retry Logic on HTTP Requests — `P0 / S`

**Files**: `hacker_news.py:36-41`, `arxiv_ai.py:44-45`, `kr36_sensor.py:43`, `wallstreetcn_sensor.py:42`, `x_grok_sensor.py:77`

**Problem**: Every sensor makes bare `httpx.get()`/`httpx.post()` calls with no retry. A single transient error (timeout, 502, rate limit) kills the entire sensor:

```python
# hacker_news.py:36 — one timeout kills the whole fetch
resp = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15)
```

**Solution**: Use `httpx` transport-level retries:

```python
transport = httpx.HTTPTransport(retries=3)
client = httpx.Client(transport=transport, timeout=15.0)
```

Or `tenacity` for finer control (exponential backoff, retry on specific status codes).

### 3.2 Bare `except Exception` Swallows All Errors — `P1 / S`

**Files**: `fetch_unified_intel.py:161-162`, `run_revenue_architect.py:63-64`, `chrome_radar.py:114-115`

**Problem**: Most sensors catch `Exception` broadly and only print a warning. The caller has no way to know if a sensor partially succeeded or completely failed. In `fetch_unified_intel.py`, each sensor block catches `Exception` and continues silently:

```python
# fetch_unified_intel.py:161-162
except Exception as e:
    print(f"  [WARN] HN failed: {e}")
```

No structured error reporting, no metrics on failure rates.

**Solution**: With the `BaseSensor` pattern, wrap each sensor call and collect a `SensorStatus` result:

```python
@dataclass
class SensorStatus:
    name: str
    success: bool
    item_count: int
    error: Optional[str] = None
    duration_ms: int = 0
```

Log these statuses and include a health summary in the report footer.

### 3.3 No Graceful Degradation for Missing API Keys — `P1 / S`

**Files**: `x_grok_sensor.py:28-30`, `run_revenue_architect.py:38-39`, `github_trending.py:86-88`

**Problem**: Missing API keys cause different behaviors across sensors:

- `x_grok_sensor.py:28-30`: Returns error string `"Error: No API Key."` — caller must string-match to detect failure
- `run_revenue_architect.py:38-39`: Returns error string mixed with normal output
- `github_trending.py:86-88`: Prints error and returns empty list

**Solution**: Standardize: sensors should raise a specific `SensorConfigError` or return an empty result with a status flag. The orchestrator decides whether to skip or warn.

### 3.4 SSL Verification Disabled — `P1 / S`

**Files**: `run_revenue_architect.py:58`

**Problem**: `verify=False` disables SSL certificate verification:

```python
response = httpx.post(XAI_BASE_URL, headers=headers, json=payload, timeout=90, verify=False)
```

This was added to handle proxy SSL interception but is a security risk in production.

**Solution**: Use `verify=False` only when an explicit env var like `DISABLE_SSL_VERIFY=1` is set, and log a warning when active.

### 3.5 No Report Directory Pre-creation — `P2 / S`

**Files**: `run_alpha_radar.py:87-88`, `run_bounty_hunter.py:108`

**Problem**: `run_alpha_radar.py` writes to `reports/web3/` and `run_bounty_hunter.py` writes to `reports/tactical/` without calling `os.makedirs()` first. If the directory doesn't exist, the script crashes with `FileNotFoundError`. Only `run_mission.py:28` and `run_revenue_architect.py:132` correctly call `os.makedirs(exist_ok=True)`.

**Solution**: Add `os.makedirs(os.path.dirname(filename), exist_ok=True)` before every file write, or centralize report output in a helper.

### 3.6 UTF-8 Reconfigure Boilerplate — `P2 / S`

**Files**: `run_alpha_radar.py:22-25`, `run_bounty_hunter.py:19-22`, `run_revenue_architect.py:12-14`, `v2ex_radar.py:10-14`, `xhs_radar.py:7-11`, `chrome_radar.py:12-15`

**Problem**: Six files contain the identical UTF-8 stdout reconfigure block:

```python
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass
```

**Solution**: Move to a single `src/utils/compat.py` and call once at startup.

---

## 4. DevOps & Deployment

### 4.1 No `requirements.txt` or `pyproject.toml` — `P0 / S`

**Files**: Project root (missing)

**Problem**: No dependency manifest exists. Dependencies are scattered across files:

| Dependency | Used In |
|-----------|---------|
| `httpx` | 8 sensors + `verifier.py` + `run_revenue_architect.py` |
| `python-dotenv` | `x_grok_sensor.py`, `run_revenue_architect.py` |
| `beautifulsoup4` | `chrome_radar.py` |

Users must guess what to install, or rely on the auto-`pip install` hack in 5 sensors.

**Solution**: Create `requirements.txt`:

```
httpx>=0.25.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
```

### 4.2 No Dockerfile — `P1 / M`

**Files**: Project root (missing)

**Problem**: No containerization. The project depends on system Python, manual `.env` setup, and correct cwd. Deploying to a server or running in CI requires manual environment setup each time.

**Solution**: Add a minimal `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "run_mission.py"]
```

Add `docker-compose.yml` for local dev with `.env` mounting and volume for `reports/`.

### 4.3 No CI/CD Pipeline — `P1 / M`

**Files**: `.github/workflows/` (missing)

**Problem**: No automated testing, linting, or deployment. Changes go directly to `main` without validation.

**Solution**: Add `.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff
      - run: ruff check src/ *.py
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt && pip install pytest
      - run: pytest tests/ -v
```

### 4.4 No Tests — `P1 / M`

**Files**: `tests/` (missing)

**Problem**: Zero test files in the project. No unit tests, no integration tests. Any refactoring risks silent breakage.

**Solution**: Add `tests/` directory with at minimum:

- `tests/test_sensors.py` — mock HTTP responses, verify each sensor parses correctly
- `tests/test_report_generation.py` — verify `generate_report()` output format
- `tests/test_config.py` — verify `.env` loading and missing-key behavior

Use `pytest` + `respx` (httpx mock library) for HTTP mocking.
