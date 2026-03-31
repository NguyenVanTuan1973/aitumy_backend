from ..models import LegalDocument, LegalClause, KnowledgeIndex
from .embedding_service import EmbeddingService
from .parser_service import ParserService


def process_legal_document(document):

    parser = ParserService()
    embedder = EmbeddingService()

    clauses_data = parser.parse_pdf_to_clauses(document.file.path)

    created_clauses = []

    for data in clauses_data:
        clause = LegalClause.objects.create(
            document=document,
            **data
        )
        created_clauses.append(clause)

    # Embed batch theo clause
    contents = [c.content for c in created_clauses]
    embeddings = embedder.embed_batch(contents)

    for clause, vector in zip(created_clauses, embeddings):
        KnowledgeIndex.objects.create(
            content_type="legal_clause",
            object_id=clause.id,
            text_content=clause.content,
            embedding=vector,
            keywords=parser.extract_keywords(clause.content)
        )