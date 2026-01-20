import logging
from .exceptions import NotificationSendError

logger = logging.getLogger(__name__)


class NotificationErrorHandler:
    @staticmethod
    def handle(err: NotificationSendError) -> None:
        logger.exception(
            err.message,
            extra={"code": err.code, **(err.context or {})},
        )
