#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from dify_dataset_base import DifyDatasetBaseClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


class DifyDatasetDBClient(DifyDatasetBaseClient):
    def __init__(self, env_file: Optional[Path] = None) -> None:
        super().__init__(env_file)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logging.info("%s %s", method, url)
        resp = requests.request(method, url, headers=self._headers(), params=params, timeout=30)
        logging.info("status=%s", resp.status_code)
        if resp.status_code >= 400:
            logging.error("response=%s", resp.text)
        resp.raise_for_status()
        if not resp.text:
            return {}
        return resp.json()
    # 获取知识库列表
    def list_datasets(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets"
        return self._request("GET", url, params={"page": page, "limit": limit})
    # 获取指定知识库详情
    def get_dataset_info(self) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}"
        return self._request("GET", url)
    # 获取知识库中的文档列表
    def list_documents(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}/documents"
        return self._request("GET", url, params={"page": page, "limit": limit})
    # 获取所有文档列表（自动翻页）
    def list_all_documents(self, *, limit: int = 100) -> list[Dict[str, Any]]:
        documents: list[Dict[str, Any]] = []
        page = 1
        while True:
            resp = self.list_documents(page=page, limit=limit)
            items = resp.get("data", []) or []
            documents.extend(items)
            if len(items) < limit:
                break
            page += 1
        return documents
    # 根据文件名从文档列表中获取文档ID
    def get_document_id_by_name(self, document_name: str, *, page: int = 1, limit: int = 100) -> Optional[str]:
        for item in self.list_all_documents(limit=limit):
            if item.get("name") == document_name:
                return item.get("id")
        return None
            
    # 删除知识库
    def delete_dataset(self) -> Dict[str, Any]:
        url = f"{self.base_url}/datasets/{self.dataset_id}"
        return self._request("DELETE", url)


if __name__ == "__main__":
    log_path = DifyDatasetBaseClient.configure_logging()
    logging.info("log_file=%s", log_path)
    client = DifyDatasetDBClient()

    logging.info("list_datasets")
    print(json.dumps(client.list_datasets(), ensure_ascii=False, indent=2))

    logging.info("get_dataset")
    print(json.dumps(client.get_dataset_info(), ensure_ascii=False, indent=2))

    logging.info("list_documents")
    print(json.dumps(client.list_documents(), ensure_ascii=False, indent=2))

    logging.info("get_document_id_by_name")
    print(json.dumps({"document_id": client.get_document_id_by_name("test.csv")}, ensure_ascii=False, indent=2))

    # logging.info("delete_dataset")
    # print(json.dumps(client.delete_dataset(), ensure_ascii=False, indent=2))
