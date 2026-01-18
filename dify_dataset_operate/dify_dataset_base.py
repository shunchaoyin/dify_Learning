#!/usr/bin/env python3
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class DifyDatasetBaseClient:
    def __init__(self, env_file: Optional[Path] = None) -> None:
        self._load_env_file(env_file or Path(__file__).with_name("dify_dataset.env"))
        self.api_key = os.getenv("DIFY_DATASET_API_KEY")
        self.dataset_id = os.getenv("DIFY_DATASET_ID")
        base_url = os.getenv("DIFY_DATASET_URL", "http://localhost/v1")
        if not self.api_key:
            raise RuntimeError("DIFY_DATASET_API_KEY is required")
        if not self.dataset_id:
            raise RuntimeError("DIFY_DATASET_ID is required")
        self.base_url = base_url.rstrip("/")

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
        log_path = target_dir / f"dify_dataset_{timestamp}.log"

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
