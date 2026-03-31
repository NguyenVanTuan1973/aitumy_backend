import logging
import time
from typing import List
from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service xử lý embedding cho KnowledgeIndex
    Có 2 mode:
    - Dev mode: mock embedding
    - Production: dùng OpenAI
    """

    def __init__(self):
        self.model = "text-embedding-3-small"
        self.max_characters = 8000
        self.use_openai = getattr(settings, "USE_OPENAI_EMBEDDING", False)

        if self.use_openai:
            from openai import OpenAI

            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if not api_key:
                raise ValueError("OPENAI_API_KEY chưa cấu hình")

            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.info("EmbeddingService chạy ở chế độ MOCK (không dùng OpenAI)")

    # -----------------------------------
    # MOCK EMBEDDING
    # -----------------------------------

    def _mock_embedding(self) -> List[float]:
        """
        Trả về vector giả 1536 chiều
        """
        return [0.0] * 1536

    # -----------------------------------
    # EMBED SINGLE TEXT
    # -----------------------------------

    def embed_text(self, text: str) -> List[float]:
        text = text[:self.max_characters]

        if not self.use_openai:
            return self._mock_embedding()

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return self._mock_embedding()

    # -----------------------------------
    # EMBED BATCH
    # -----------------------------------

    def embed_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        if not self.use_openai:
            return [self._mock_embedding() for _ in texts]

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = [t[:self.max_characters] for t in texts[i:i + batch_size]]

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                all_embeddings.extend(
                    [self._mock_embedding() for _ in batch]
                )

        return all_embeddings