"""
NotifyProvider - 通知渠道抽象基类。
所有通知渠道应继承此类并实现 send_text() 和 send_file() 方法。
"""
from abc import ABC, abstractmethod
import logging
from typing import Optional


class NotifyProvider(ABC):
    """通知渠道抽象基类，所有通知实现必须继承此类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """通知渠道名称"""
        ...

    @abstractmethod
    def send_text(self, text: str) -> bool:
        """发送文本消息（支持 Markdown 格式）。

        Args:
            text: 要发送的文本内容。

        Returns:
            发送成功返回 True，否则返回 False。
        """
        ...

    @abstractmethod
    def send_file(self, file_path: str, caption: Optional[str] = None) -> bool:
        """发送文件。

        Args:
            file_path: 文件的本地路径。
            caption: 可选的文件说明文字。

        Returns:
            发送成功返回 True，否则返回 False。
        """
        ...

    def is_configured(self) -> bool:
        """检查该通知渠道是否已正确配置（如 Token、Webhook URL 等）。
        子类可覆盖此方法以实现自定义检查逻辑。
        """
        return True
