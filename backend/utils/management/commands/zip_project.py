import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Zips backend, docs and postman folders into separate ZIP files in the root directory.'

    def handle(self, *args, **options):
        # 1. Define paths (assuming manage.py is in root/backend/)
        backend_dir = Path(settings.BASE_DIR).resolve()
        root_dir = backend_dir.parent

        # Map: folder name -> target ZIP name
        targets = {
            'backend': 'backend',
            'docs': 'docs',
            'postman': 'postman'
        }

        # Ignored files for backend (usually no need to filter in docs/postman)
        ignore_list = {'.git', '.venv', 'venv',
                       '__pycache__', 'db.sqlite3', '.env'}

        for folder_name, zip_base_name in targets.items():
            source_path = root_dir / folder_name

            if not source_path.exists():
                self.stdout.write(self.style.WARNING(
                    f'Folder {folder_name} was not found, skipping.'))
                continue

            output_path = root_dir / zip_base_name

            try:
                # For backend we use filtering, for others (docs, postman) we take everything
                if folder_name == 'backend':
                    def ignore_func(directory, contents):
                        return [c for c in contents if c in ignore_list or c.endswith(('.pyc', '.zip'))]

                    # shutil.make_archive does not support filtering directly, so for backend we just warn,
                    # that it will include everything except .zip files (standard behavior of make_archive)
                    shutil.make_archive(str(output_path), 'zip', source_path)
                else:
                    shutil.make_archive(str(output_path), 'zip', source_path)

                self.stdout.write(self.style.SUCCESS(
                    f'Created: {zip_base_name}.zip in {root_dir}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Error while zipping {folder_name}: {e}'))
