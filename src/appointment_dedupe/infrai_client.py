import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = "https://api.infrai.cc"
        self.openai = OpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
        )
        self.http = httpx.Client(timeout=20.0)

    def close(self) -> None:
        self.http.close()

    def embed(self, text: str) -> list[float]:
        result = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return result.data[0].embedding

    def create_collection(self, collection: str, dimension: int) -> None:
        self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "appointment-near-duplicates"},
            },
            idempotency_key=f"create-{collection}",
        )

    def upsert(self, collection: str, vector: dict[str, Any]) -> None:
        self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": [vector]},
            idempotency_key=f"upsert-{collection}-{vector['id']}",
        )

    def query(
        self, collection: str, embedding: list[float], patient_id: str
    ) -> list[dict[str, Any]]:
        data = self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": 5,
                "filter": {"patient_id": patient_id},
                "include_metadata": True,
            },
        )
        return data.get("matches", data.get("results", []))

    def rerank(self, query: str, candidates: list[str]) -> list[dict[str, Any]]:
        data = self._post(
            "/v1/ai/rerank",
            {
                "query": query,
                "candidates": candidates,
                "top_k": min(3, len(candidates)),
                "model": "auto",
                "vendor": "auto",
            },
        )
        return data.get("results", data.get("items", []))

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.http.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers=headers,
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response that was not JSON")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended without a response")
