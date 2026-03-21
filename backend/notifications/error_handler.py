import logging

import sentry_sdk

from .exceptions import NotificationSendError

logger = logging.getLogger(__name__)


class NotificationErrorHandler:
    @staticmethod
    def handle(err: NotificationSendError) -> None:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("category", "application")
            scope.set_tag("subsystem", "notifications")
            scope.set_tag("operation", "delivery")
            scope.set_tag("error_code", err.code)
            scope.set_context("notification_error", {
                "code": err.code,
                "message": err.message,
                **(err.context or {}),
            })
            logger.exception(
                err.message,
                extra={"code": err.code, **(err.context or {})},
            )
