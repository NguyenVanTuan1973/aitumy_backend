
import re
from typing import List, Dict
import PyPDF2
import logging

logger = logging.getLogger(__name__)


class ParserService:
    """
    Xử lý PDF pháp lý
    - Đọc PDF
    - Clean text
    - Parse Điều / Khoản / Điểm
    """

    # =========================
    # READ PDF
    # =========================

    def read_pdf(self, path: str) -> str:
        try:
            reader = PyPDF2.PdfReader(path)
            full_text = ""

            for page in reader.pages:
                full_text += page.extract_text() or ""

            return full_text

        except Exception as e:
            logger.error(f"PDF read error: {e}")
            return ""

    # =========================
    # CLEAN TEXT
    # =========================

    def clean_text(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    # =========================
    # PARSE STRUCTURE
    # =========================

    def parse_pdf_to_clauses(self, path: str) -> List[Dict]:
        """
        Parse PDF thành danh sách LegalClause data
        Trả về list dict để create LegalClause
        """

        raw_text = self.read_pdf(path)
        clean_text = self.clean_text(raw_text)

        # Tách theo Điều
        articles = re.split(r"(Điều\s+\d+\.?)", clean_text)

        clauses_data = []
        current_article = None

        for part in articles:
            if re.match(r"Điều\s+\d+", part):
                current_article = re.search(r"\d+", part).group()
            else:
                if not current_article:
                    continue

                # Tách Khoản
                clause_parts = re.split(r"(\d+\.)", part)

                for sub in clause_parts:
                    sub = sub.strip()
                    if not sub:
                        continue

                    clause_number = None
                    match = re.match(r"^(\d+)\.", sub)
                    if match:
                        clause_number = match.group(1)

                    clauses_data.append({
                        "chapter": "",
                        "article": current_article,
                        "clause": clause_number or "",
                        "point": "",
                        "title": "",
                        "content": sub,
                        "topic": ""
                    })

        return clauses_data

    # =========================
    # KEYWORD EXTRACTION
    # =========================

    def extract_keywords(self, text: str, max_keywords: int = 20) -> str:
        text = text.lower()
        words = re.findall(r'\b[a-zA-ZÀ-ỹ0-9]+\b', text)

        stopwords = {"và", "là", "của", "cho", "the", "and", "is"}
        filtered = [w for w in words if w not in stopwords and len(w) > 2]

        unique_words = list(dict.fromkeys(filtered))[:max_keywords]

        return " ".join(unique_words)