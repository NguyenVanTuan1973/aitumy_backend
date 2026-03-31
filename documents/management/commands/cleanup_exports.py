from django.core.management.base import BaseCommand
from ..cleanup.export_file_cleanup import cleanup_export_files

class Command(BaseCommand):
    help = "Cleanup expired export PDF files"

    def handle(self, *args, **options):
        cleanup_export_files(force=True)
        self.stdout.write(self.style.SUCCESS("Export files cleaned"))
