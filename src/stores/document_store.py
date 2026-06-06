from __future__ import annotations

import json
from pathlib import Path


class DocumentStore:
    def __init__(
        self,
        data_path: str = "data/documents/documents.json",
        documents: dict[str, dict] | None = None,
    ):
        # An explicit ``documents`` mapping (e.g. built from DB-uploaded files)
        # overrides the file-backed store. Used to verify real uploaded docs.
        if documents is not None:
            self._documents: dict[str, dict] = documents
        else:
            path = Path(data_path)
            self._documents = json.loads(path.read_text()) if path.exists() else {}

    def verify(self, document_id: str) -> dict:
        doc = self._documents.get(document_id)
        if doc is None:
            return {
                "document_id": document_id,
                "document_type": "unknown",
                "status": "MISSING",
                "issues": [f"Document {document_id} not found in system"],
            }
        return {
            "document_id": doc["document_id"],
            "document_type": doc["document_type"],
            "status": doc["status"],
            "issues": doc.get("issues", []),
        }
