from functools import lru_cache
from typing import Optional

from documents.models import RegisterMapping


@lru_cache(maxsize=100)
def resolve_doc_register(plan_code: Optional[str], job_code: Optional[str]) -> str:
    """
    Resolve doc_register from RegisterMapping
    → Lấy FormTemplate.code (VD: S1a-HKD)
    """

    if not plan_code or not job_code:
        return ""

    mapping = (
        RegisterMapping.objects
        .select_related("form_template")
        .filter(
            plan_code=plan_code,
            flow=job_code,
            is_active=True
        )
        .first()
    )

    if not mapping or not mapping.form_template:
        return ""

    # 🔥 Lấy code thay vì name
    return (mapping.form_template.code or "").strip()