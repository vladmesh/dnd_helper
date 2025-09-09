"""Test factories for building minimal Telegram-like update objects.

These are lightweight stubs that mimic only the attributes our handlers read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class DummyUser:
    id: int
    is_bot: bool = False
    first_name: str = "Test"
    last_name: str = ""
    username: Optional[str] = None
    full_name: Optional[str] = None
    language_code: Optional[str] = None


@dataclass
class DummyChat:
    id: int
    type: str = "private"


class DummyMessage:
    def __init__(self, chat: DummyChat, text: str = "") -> None:
        self.chat = chat
        self.text = text
        self.date = datetime.now()
        # Capture last reply for assertions
        self.last_text: Optional[str] = None
        self.last_kwargs: dict[str, Any] = {}
        # Minimal message id emulation
        self.message_id: int = 1

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.last_text = text
        self.last_kwargs = kwargs
        # Return self to mimic telegram.Message with message_id
        self.message_id += 1
        return self


class DummyUpdate:
    def __init__(self, user: Optional[DummyUser], chat: DummyChat, message: Optional[DummyMessage]) -> None:
        self._effective_user = user
        self._effective_chat = chat
        self.message = message

    @property
    def effective_user(self) -> Optional[DummyUser]:
        return self._effective_user

    @property
    def effective_chat(self) -> DummyChat:
        return self._effective_chat


def make_message_update(chat_id: int = 100, user_id: int = 200, user_lang: str = "ru", text: str = "") -> DummyUpdate:
    user = DummyUser(
        id=user_id,
        is_bot=False,
        first_name="Test",
        username="tester",
        full_name="Test User",
        language_code=user_lang,
    )
    chat = DummyChat(id=chat_id)
    message = DummyMessage(chat=chat, text=text)
    return DummyUpdate(user=user, chat=chat, message=message)


