#!/usr/bin/env python3
import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class DifyWorkflowBase:
    def __init__(self, env_file: Optional[Path] = None) -> None:
        self._load_env_file(env_file or Path(__file__).with_name("workflow.env"))
        self.api_key = os.getenv("DIFY_WORKFLOW_API_KEY")
        self.base_url = os.getenv("DIFY_WORKFLOW_BASE_URL", "http://localhost/v1").rstrip("/")
        self.user = os.getenv("DIFY_WORKFLOW_USER", "abc-123")
        self.response_mode = os.getenv("DIFY_WORKFLOW_RESPONSE_MODE", "blocking")
        if not self.api_key:
            raise RuntimeError("DIFY_WORKFLOW_API_KEY is required")

    @staticmethod
    def _load_env_file(env_file: Path) -> None:
        if not env_file.exists():
            return
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

    @staticmethod
    def configure_logging(log_dir: Optional[Path] = None) -> Path:
        target_dir = log_dir or Path(__file__).with_name("logs")
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = target_dir / f"dify_workflow_{timestamp}.log"

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

        has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

        if not has_file_handler:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if not has_stream_handler:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return log_path


class DifyWorkflowClient(DifyWorkflowBase):
    def __init__(self, env_file: Optional[Path] = None) -> None:
        super().__init__(env_file)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _guess_content_type(file_path: str) -> str:
        guessed, _ = mimetypes.guess_type(file_path)
        return guessed or "application/octet-stream"

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        url = f"{self.base_url}/files/upload"
        logging.info("POST %s", url)
        logging.info("upload_file=%s", file_path)
        file_mime = self._guess_content_type(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, file_mime)}
            data = {"user": self.user}
            resp = requests.post(url, headers=self._headers(), files=files, data=data, timeout=120)
            logging.info("status=%s", resp.status_code)
            if resp.status_code >= 400:
                logging.error("response=%s", resp.text)
            resp.raise_for_status()
            return resp.json() if resp.text else {}

    def chat_messages(self, query: str, upload_file_id: str, *, file_type: str = "document") -> Dict[str, Any]:
        url = f"{self.base_url}/chat-messages"
        payload = {
            "inputs": {},
            "query": query,
            "response_mode": self.response_mode,
            "conversation_id": "",
            "user": self.user,
            "files": [
                {
                    "type": file_type,
                    "transfer_method": "local_file",
                    "upload_file_id": upload_file_id,
                }
            ],
        }
        logging.info("POST %s", url)
        logging.info("chat_query=%s", query)
        resp = requests.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        logging.info("status=%s", resp.status_code)
        try:
            answer = resp.json().get("answer")
        except Exception:
            answer = None
        logging.info("chat_answer=%s", answer)
        if resp.status_code >= 400:
            logging.error("response=%s", resp.text)
        resp.raise_for_status()
        return resp.json() if resp.text else {}


if __name__ == "__main__":
    log_path = DifyWorkflowBase.configure_logging()
    logging.info("log_file=%s", log_path)

    client = DifyWorkflowClient()

    file_path = os.getenv(
        "DIFY_WORKFLOW_FILE_PATH",
        "/Users/yinshunchao/code/dify/data/dify_Learning/doc/test.csv",
    )
    query = os.getenv("DIFY_WORKFLOW_QUERY", "你是谁？")

    upload_resp = client.upload_file(file_path)
    upload_file_id = upload_resp.get("id", "")
    if not upload_file_id:
        raise RuntimeError(f"upload failed: {upload_resp}")

    result = client.chat_messages(query, upload_file_id, file_type="document")
    print(json.dumps(result, ensure_ascii=False, indent=2))
