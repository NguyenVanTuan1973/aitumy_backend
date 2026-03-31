
import numpy as np
from typing import List
from knowledge_base.models import KnowledgeIndex
from .embedding_service import EmbeddingService


class RetrievalService:

    def __init__(self):
        self.embedding_service = EmbeddingService()

    def cosine_similarity(self, v1, v2):
        v1 = np.array(v1)
        v2 = np.array(v2)

        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return 0.0

        return float(
            np.dot(v1, v2) /
            (np.linalg.norm(v1) * np.linalg.norm(v2))
        )

    def search(
        self,
        query: str,
        content_type: str = None,
        top_k: int = 5
    ) -> List[KnowledgeIndex]:

        # 1️⃣ Embed query
        query_embedding = self.embedding_service.embed_text(query)

        # 2️⃣ Pre-filter bằng keyword (optional)
        qs = KnowledgeIndex.objects.all()

        if content_type:
            qs = qs.filter(content_type=content_type)

        # Giới hạn số lượng để tránh load quá nhiều
        candidates = qs[:500]

        scored_results = []

        # 3️⃣ Tính similarity
        for item in candidates:
            score = self.cosine_similarity(
                query_embedding,
                item.embedding
            )
            scored_results.append((score, item))

        # 4️⃣ Sort giảm dần
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # 5️⃣ Lấy top_k
        top_items = [item for score, item in scored_results[:top_k]]

        return top_items