"""
DiscordNotifier - 基于 Discord Webhook 的通知实现。
支持发送 Markdown 格式的报告摘要和完整报告文件。
从 .env 读取 DISCORD_WEBHOOK_URL。
"""
import json
import os
import logging
from typing import Optional

import httpx

from src.notify.base import NotifyProvider

logger = logging.getLogger(__name__)

# Discord Webhook 单条消息最大字符数
MAX_MESSAGE_LENGTH = 2000


class DiscordNotifier(NotifyProvider):
    """Discord Webhook 通知渠道"""

    def __init__(self):
        super().__init__()
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")

    @property
    def name(self) -> str:
        return "Discord"

    def is_configured(self) -> bool:
        """检查 Discord Webhook URL 是否已配置"""
        return bool(self.webhook_url)

    def _split_message(self, text: str) -> list[str]:
        """将超长文本按 Discord 限制拆分为多条消息。

        按行拆分，尽量保持每条消息完整性。
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks: list[str] = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                if current:
                    chunks.append(current)
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
        """发送文本消息到 Discord Webhook，支持 Markdown 格式。

        超长文本会自动拆分为多条消息发送。
        """
        if not self.is_configured():
            self.logger.warning("Discord Webhook 未配置，跳过发送")
            return False

        chunks = self._split_message(text)
        try:
            with httpx.Client(timeout=30) as client:
                for chunk in chunks:
                    resp = client.post(
                        self.webhook_url,
                        json={"content": chunk},
                    )
                    if resp.status_code not in (200, 204):
                        self.logger.error(
                            "Discord 发送失败: %s %s",
                            resp.status_code, resp.text,
                        )
                        return False
            self.logger.info("Discord 消息发送成功 (%d 条)", len(chunks))
            return True
        except httpx.HTTPError as e:
            self.logger.error("Discord 请求异常: %s", e)
            return False

    def send_file(self, file_path: str, caption: Optional[str] = None) -> bool:
        """发送文件到 Discord Webhook。

        Args:
            file_path: 本地文件路径。
            caption: 可选的文件说明文字。
        """
        if not self.is_configured():
            self.logger.warning("Discord Webhook 未配置，跳过发送")
            return False

        if not os.path.isfile(file_path):
            self.logger.error("文件不存在: %s", file_path)
            return False

        try:
            with (
                httpx.Client(timeout=60) as client,
                open(file_path, "rb") as f,
            ):
                payload = {}
                if caption:
                    payload["content"] = caption[:MAX_MESSAGE_LENGTH]

                resp = client.post(
                    self.webhook_url,
                    data={"payload_json": json.dumps(payload)} if payload else None,
                    files={"file": (os.path.basename(file_path), f)},
                )
                if resp.status_code not in (200, 204):
                    self.logger.error(
                        "Discord 文件发送失败: %s %s",
                        resp.status_code, resp.text,
                    )
                    return False

            self.logger.info("Discord 文件发送成功: %s", file_path)
            return True
        except httpx.HTTPError as e:
            self.logger.error("Discord 文件发送异常: %s", e)
            return False
