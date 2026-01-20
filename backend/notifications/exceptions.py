from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NotificationSendError(Exception):
    code: str
    message: str
    context: dict[str, Any] | None = None
