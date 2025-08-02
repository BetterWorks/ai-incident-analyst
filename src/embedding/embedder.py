from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from logging_utils.logger import setup_logger
from src.config import get_config

class LogEmbedder:
    def __init__(self, 
                 model_name: Optional[str] = None, 
                 batch_size: Optional[int] = None, 
                 fields_to_embed: Optional[List[str]] = None):
        self.logger = setup_logger()
        self.model_name = model_name or get_config("EMBEDDING_MODEL", default="all-MiniLM-L6-v2")
        self.batch_size = int(batch_size or get_config("EMBEDDING_BATCH_SIZE", default=32))
        self.fields_to_embed = fields_to_embed or get_config("EMBEDDING_FIELDS", default="message").split(",")
        self.logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.logger.info(f"LogEmbedder initialized with batch size {self.batch_size} and fields {self.fields_to_embed}")

    def _get_text(self, log: Dict) -> str:
        # Concatenate selected fields for embedding
        return " ".join(str(log.get(f, "")) for f in self.fields_to_embed if log.get(f) is not None)

    def embed_logs(self, logs: List[Dict]) -> List[Dict]:
        texts = [self._get_text(log) for log in logs]
        self.logger.info(f"Embedding {len(texts)} logs...")
        embeddings = self.model.encode(texts, batch_size=self.batch_size, show_progress_bar=True)
        for log, emb in zip(logs, embeddings):
            log["embedding"] = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
        self.logger.info("Embedding complete.")
        return logs

if __name__ == "__main__":
    # Example usage
    logs = [
        {"message": "User login failed", "event": "auth", "container_name": "svc1"},
        {"message": "Payment processed", "event": "payment", "container_name": "svc2"}
    ]
    embedder = LogEmbedder(fields_to_embed=["message", "event"])
    logs_with_emb = embedder.embed_logs(logs)
    for log in logs_with_emb:
        print(log)
