#!/usr/bin/env python3
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from dify_dataset_base import DifyDatasetBaseClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class DifyDatasetDocClient(DifyDatasetBaseClient):
    def __init__(self, env_file: Optional[Path] = None) -> None:
        super().__init__(env_file)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request(self, method: str, url: str, *, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logging.info("%s %s", method, url)
        resp = requests.request(method, url, headers=self._headers(), json=json_body, timeout=60)
        logging.info("status=%s", resp.status_code)
        if resp.status_code >= 400:
            logging.error("response=%s", resp.text)
        resp.raise_for_status()
        if not resp.text:
            return {}
        return resp.json()

    @staticmethod
    def _guess_content_type(file_path: str) -> str:
        guessed, _ = mimetypes.guess_type(file_path)
        return guessed or "application/octet-stream"

    # 获取知识库的文档形式
    def _get_dataset_doc_form(self) -> str:
        url = f"{self.base_url}/datasets/{self.dataset_id}"
        logging.info("GET %s", url)
        resp = requests.get(url, headers=self._headers(), timeout=30)
        logging.info("status=%s", resp.status_code)
        if resp.status_code >= 400:
            logging.error("response=%s", resp.text)
        resp.raise_for_status()
        data = resp.json() if resp.text else {}
        return data.get("doc_form") or "text_model"

    # 通过文本创建文档
    def create_by_text(self, text: str) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}/document/create-by-text"
        doc_form = self._get_dataset_doc_form()
        logging.info("doc_form=%s", doc_form)
        payload = {
            "name": "test.txt",
            "text": text,
            "indexing_technique": "economy",
            "doc_form": doc_form,
            "doc_language": "中文",
            "process_rule": {
                "mode": "automatic",
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True}
                ],
                # "rules": {
                #     "segmentation": {"separator": "\\n", "max_tokens": 1024},
                #     "parent_mode": "full-doc",
                #     "subchunk_segmentation": {
                #         "separator": "\\n",
                #         "max_tokens": 512,
                #         "chunk_overlap": 128,
                #     },
                # },
            },
        }
        return self._request("POST", url, json_body=payload)
    # 上传文件创建文档
    def create_by_file(self, file_path: str, *, content_type: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}/document/create-by-file"
        doc_form = self._get_dataset_doc_form()
        logging.info("doc_form=%s", doc_form)
        payload = {
            "name": os.path.basename(file_path),
            "indexing_technique": "economy",
            "doc_form": doc_form,
            "doc_language": "中文",
            "process_rule": {
                "mode": "automatic",
                "pre_processing_rules": [
                    {"id": "remove_extra_spaces", "enabled": True}
                ],
                # "rules": {
                #     "segmentation": {"separator": "\\n", "max_tokens": 1024},
                #     "parent_mode": "full-doc",
                #     "subchunk_segmentation": {
                #         "separator": "\\n",
                #         "max_tokens": 512,
                #         "chunk_overlap": 128,
                #     },
                # },
            },
        }

        logging.info("POST %s", url)
        file_mime = content_type or self._guess_content_type(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, file_mime)}
            data = {"data": json.dumps(payload, ensure_ascii=False)}
            resp = requests.post(url, headers=self._headers(), files=files, data=data, timeout=120)
            logging.info("status=%s", resp.status_code)
            if resp.status_code >= 400:
                logging.error("response=%s", resp.text)
            resp.raise_for_status()
            return resp.json() if resp.text else {}
    # 文件更新文档
    def update_by_file(self, document_id: str, file_path: str, *, content_type: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}/documents/{document_id}/update-by-file"
        payload = {"name": os.path.basename(file_path), "process_rule": {"mode": "automatic"}}

        logging.info("POST %s", url)
        file_mime = content_type or self._guess_content_type(file_path)
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, file_mime)}
            data = {"data": json.dumps(payload, ensure_ascii=False)}
            resp = requests.post(url, headers=self._headers(), files=files, data=data, timeout=120)
            logging.info("status=%s", resp.status_code)
            if resp.status_code >= 400:
                logging.error("response=%s", resp.text)
            resp.raise_for_status()
            return resp.json() if resp.text else {}

if __name__ == "__main__":
    log_path = DifyDatasetBaseClient.configure_logging()
    logging.info("log_file=%s", log_path)
    client = DifyDatasetDocClient()
    sample_text = "#班级有多少人  班级一共有40个人，其中男生有22人，女生有28个人。"

    logging.info("create_by_text")
    print(json.dumps(client.create_by_text(sample_text), ensure_ascii=False, indent=2))

    logging.info("create_by_file")
    print(json.dumps(client.create_by_file("test.md"), ensure_ascii=False, indent=2))
