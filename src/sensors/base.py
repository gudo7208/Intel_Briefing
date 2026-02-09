"""
BaseSensor - 传感器基类，定义统一接口。
所有传感器应继承此类并实现 fetch() 方法。
包含统一的错误重试机制（exponential backoff）和文件缓存。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Callable, TypeVar, Optional
import hashlib
import json
import logging
import random
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache"


def cached_fetch(
    key: str,
    fetcher: Callable[[], T],
    ttl_seconds: int = 1800,
) -> T:
    """文件缓存：在 TTL 内直接返回缓存结果，避免重复抓取。

    Args:
        key: 缓存键（通常是 sensor 名 + 参数）。
        fetcher: 无参可调用对象，返回需要缓存的数据。
        ttl_seconds: 缓存有效期，默认 30 分钟。
    """
    cache_file = CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - data["ts"] < ttl_seconds:
                logger.info("缓存命中: %s", key)
                return data["payload"]
        except (json.JSONDecodeError, KeyError):
            pass  # 缓存损坏，重新获取

    result = fetcher()

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({"ts": time.time(), "payload": result}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("写入缓存失败: %s", e)

    return result


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------
def retry_request(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_status: tuple = (429, 500, 502, 503, 504),
) -> T:
    """带指数退避的重试机制。

    对 httpx 请求进行重试，处理网络错误和可重试的 HTTP 状态码。
    """
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            result = func()
            # 如果返回的是 httpx.Response，检查状态码
            if isinstance(result, httpx.Response) and result.status_code in retryable_status:
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logger.warning(
                        "HTTP %d，第 %d/%d 次重试，等待 %.1fs",
                        result.status_code, attempt + 1, max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                result.raise_for_status()
            return result
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
            last_exc = e
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                logger.warning(
                    "%s，第 %d/%d 次重试，等待 %.1fs",
                    type(e).__name__, attempt + 1, max_retries, delay,
                )
                time.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SensorResult
# ---------------------------------------------------------------------------
@dataclass
class SensorResult:
    """传感器统一返回数据结构"""
    title: str
    url: str
    source: str
    category: str
    heat: str = ""
    timestamp: str = ""
    summary: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SensorResult":
        return cls(**d)


# ---------------------------------------------------------------------------
# BaseSensor
# ---------------------------------------------------------------------------
class BaseSensor(ABC):
    """传感器抽象基类，所有传感器必须实现 name 属性和 fetch() 方法"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """传感器名称"""
        ...

    @abstractmethod
    def fetch(self, limit: int = 10) -> List[SensorResult]:
        """获取数据，返回统一格式的 SensorResult 列表"""
        ...

    def is_available(self) -> bool:
        """检查传感器是否可用（如依赖、API Key 等）"""
        return True

    def fetch_with_cache(self, limit: int = 10, ttl_seconds: int = 1800) -> List[SensorResult]:
        """带缓存的 fetch，避免短时间内重复抓取。"""
        cache_key = f"{self.name}:limit={limit}"

        def _fetcher():
            results = self.fetch(limit)
            return [r.to_dict() for r in results]

        raw = cached_fetch(cache_key, _fetcher, ttl_seconds)
        return [SensorResult.from_dict(d) for d in raw]
