"""
BaseSensor - 传感器基类，定义统一接口。
所有传感器应继承此类并实现 fetch() 方法。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List
import logging


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
