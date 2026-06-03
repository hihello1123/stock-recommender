import fcntl
import json
from pathlib import Path
from urllib import request

from django.conf import settings


class LocalLLMClientError(RuntimeError):
    pass


def chat_completion(payload: dict, *, timeout_seconds: int) -> dict:
    lock_path = Path(settings.BASE_DIR) / "logs" / "llm.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    api_url = settings.LOCAL_LLM_BASE_URL.rstrip("/") + "/api/chat"
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        api_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with lock_path.open("w") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                with request.urlopen(http_request, timeout=timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise LocalLLMClientError("로컬 LLM 호출에 실패했습니다.") from exc
