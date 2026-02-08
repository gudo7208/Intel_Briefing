"""
TelegramNotifier - 基于 Telegram Bot API 的通知实现。
支持发送 Markdown 格式的报告摘要和完整报告文件。
从 .env 读取 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID。
"""
import os
import logging
from typing import Optional

import httpx

from src.notify.base import NotifyProvider

logger = logging.getLogger(__name__)

# Telegram Bot API 基础地址
TELEGRAM_API = "https://api.telegram.org"

# Telegram 单条消息最大字符数
MAX_MESSAGE_LENGTH = 4096


class TelegramNotifier(NotifyProvider):
    """Telegram Bot 通知渠道"""

    def __init__(self):
        super().__init__()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def name(self) -> str:
        return "Telegram"

    def is_configured(self) -> bool:
        """检查 Telegram Bot Token 和 Chat ID 是否已配置"""
        return bool(self.token and self.chat_id)

    def _api_url(self, method: str) -> str:
        """拼接 Telegram Bot API 请求地址"""
        return f"{TELEGRAM_API}/bot{self.token}/{method}"

    def _split_message(self, text: str) -> list[str]:
        """将超长文本按 Telegram 限制拆分为多条消息。

        按行拆分，尽量保持每条消息完整性。
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks: list[str] = []
        current = ""
        for line in text.split("\n"):
            # 如果当前块加上新行会超限，先保存当前块
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                if current:
                    chunks.append(current)
                # 单行超长时直接截断
                if len(line) > MAX_MESSAGE_LENGTH:
                    chunks.append(line[:MAX_MESSAGE_LENGTH])
                else:
                    current = line
            else:
                current = f"{current}\n{line}" if current else line

        if current:
            chunks.append(current)
        return chunks

    def send_text(self, text: str) -> bool:
        """发送文本消息到 Telegram，支持 Markdown 格式。

        超长文本会自动拆分为多条消息发送。
        """
        if not self.is_configured():
            self.logger.warning("Telegram 未配置，跳过发送")
            return False

        chunks = self._split_message(text)
        try:
            with httpx.Client(timeout=30) as client:
                for chunk in chunks:
                    resp = client.post(
                        self._api_url("sendMessage"),
                        json={
                            "chat_id": self.chat_id,
                            "text": chunk,
                            "parse_mode": "Markdown",
                        },
                    )
                    if resp.status_code != 200:
                        self.logger.error(
                            "Telegram 发送失败: %s %s",
                            resp.status_code, resp.text,
                        )
                        return False
            self.logger.info("Telegram 消息发送成功 (%d 条)", len(chunks))
            return True
        except httpx.HTTPError as e:
            self.logger.error("Telegram 请求异常: %s", e)
            return False

    def send_file(self, file_path: str, caption: Optional[str] = None) -> bool:
        """发送文件到 Telegram。

        Args:
            file_path: 本地文件路径。
            caption: 可选的文件说明（最长 1024 字符）。
        """
        if not self.is_configured():
            self.logger.warning("Telegram 未配置，跳过发送")
            return False

        if not os.path.isfile(file_path):
            self.logger.error("文件不存在: %s", file_path)
            return False

        try:
            with (
                httpx.Client(timeout=60) as client,
                open(file_path, "rb") as f,
            ):
                data = {"chat_id": self.chat_id}
                if caption:
                    data["caption"] = caption[:1024]

                resp = client.post(
                    self._api_url("sendDocument"),
                    data=data,
                    files={"document": (os.path.basename(file_path), f)},
                )
                if resp.status_code != 200:
                    self.logger.error(
                        "Telegram 文件发送失败: %s %s",
                        resp.status_code, resp.text,
                    )
                    return False

            self.logger.info("Telegram 文件发送成功: %s", file_path)
            return True
        except httpx.HTTPError as e:
            self.logger.error("Telegram 文件发送异常: %s", e)
            return False
