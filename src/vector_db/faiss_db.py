import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from logging_utils.logger import setup_logger
from src.config import get_config
import os
import pickle

class FaissVectorDB:
    def __init__(self, 
                 dim: Optional[int] = None, 
                 db_path: Optional[str] = None):
        self.logger = setup_logger()
        self.db_path = db_path or get_config("FAISS_DB_PATH", default="faiss_index.bin")
        self.meta_path = self.db_path + ".meta"
        self.index = None
        self.metadata = []
        self.dim = dim
        if os.path.exists(self.db_path):
            self._load()
        else:
            self.logger.info("No existing FAISS index found. Will create new on first insert.")

    def _save(self):
        faiss.write_index(self.index, self.db_path)
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        self.logger.info(f"FAISS index and metadata saved to {self.db_path} and {self.meta_path}")

    def _load(self):
        self.index = faiss.read_index(self.db_path)
        with open(self.meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        self.dim = self.index.d
        self.logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors and dim {self.dim}")

    def add_logs(self, logs: List[Dict]):
        if not logs:
            return
        embeddings = np.array([log["embedding"] for log in logs]).astype(np.float32)
        if self.index is None:
            self.dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(self.dim)
            self.logger.info(f"Created new FAISS index with dim {self.dim}")
        self.index.add(embeddings)
        self.metadata.extend([{k: v for k, v in log.items() if k != "embedding"} for log in logs])
        self._save()

    def search(self, query_emb: List[float], k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            self.logger.warning("No vectors in index.")
            return []
        query = np.array([query_emb]).astype(np.float32)
        D, I = self.index.search(query, k)
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result["distance"] = float(dist)
                results.append(result)
        return results

if __name__ == "__main__":
    # Example usage
    db = FaissVectorDB(dim=384)
    logs = [
        {"message": "error", "embedding": [0.1]*384},
        {"message": "warning", "embedding": [0.2]*384}
    ]
    db.add_logs(logs)
    res = db.search([0.1]*384, k=2)
    print(res)
