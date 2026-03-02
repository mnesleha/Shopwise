from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self) -> None:
        import accounts.signals  # noqa: F401 — registers post_save signal handlers
