import time
from pathlib import Path
from django.conf import settings

_last_cleanup_time = 0

def cleanup_export_files(force: bool = False):
    """
    Xoá file export PDF quá TTL
    - force=True: bỏ qua interval (dùng cho cron)
    """

    global _last_cleanup_time
    now = time.time()

    # 1️⃣ Chặn chạy quá thường xuyên (khi gọi từ API)
    if not force:
        if now - _last_cleanup_time < settings.EXPORT_CLEANUP_INTERVAL_SECONDS:
            return

    export_dir: Path = settings.EXPORT_MEDIA_DIR
    if not export_dir.exists():
        return

    exclude_recent_seconds = settings.EXPORT_EXCLUDE_RECENT_SECONDS

    for file in export_dir.iterdir():
        if not file.is_file():
            continue

        try:
            mtime = file.stat().st_mtime
        except OSError:
            continue

        age = now - mtime

        # 2️⃣ File quá mới → bỏ qua luôn
        if age < exclude_recent_seconds:
            continue

        # 3️⃣ File đủ già → xóa
        if age > settings.EXPORT_FILE_TTL_SECONDS:
            try:
                file.unlink()
            except Exception:
                # Không raise – tránh ảnh hưởng request/user khác
                pass

    _last_cleanup_time = now
