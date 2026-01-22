import time
import requests


class MailpitClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def purge(self) -> None:
        requests.delete(f"{self.base_url}/api/v1/messages").raise_for_status()

    def list_messages(self) -> dict:
        r = requests.get(f"{self.base_url}/api/v1/messages")
        r.raise_for_status()
        return r.json()

    def get_message(self, message_id: str) -> dict:
        r = requests.get(f"{self.base_url}/api/v1/message/{message_id}")
        r.raise_for_status()
        return r.json()

    def wait_for_message_containing(self, needle: str, timeout_s: float = 10.0, poll_s: float = 0.2) -> dict:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            data = self.list_messages()
            msgs = data.get("messages") or []
            for m in msgs:
                if needle in str(m):
                    return m
            time.sleep(poll_s)
        raise AssertionError(
            f"No Mailpit message containing '{needle}' within timeout")
