import os
import zipfile
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Zips backend, frontend, docs and postman folders into separate ZIP files in the root directory.'

    def handle(self, *args, **options):
        backend_dir = Path(settings.BASE_DIR).resolve()   # root/backend
        root_dir = backend_dir.parent                     # root

        targets = {
            'backend': 'backend',
            'frontend': 'frontend',
            'docs': 'docs',
            'postman': 'postman',
        }

        ignore_map = {
            'backend': {
                '.git', '.venv', 'venv', '__pycache__',
                'db.sqlite3', '.env', '.pytest_cache',
            },
            'frontend': {
                '.git', 'node_modules', '.next', 'dist', 'build',
                '.env',
            },
            # docs/postman: no filtering
        }

        ignore_ext = {'.pyc', '.zip'}  # zip inside zip etc.

        for folder_name, zip_base_name in targets.items():
            source_path = root_dir / folder_name
            if not source_path.exists():
                self.stdout.write(self.style.WARNING(
                    f'Folder "{folder_name}" was not found, skipping.'
                ))
                continue

            zip_path = root_dir / f"{zip_base_name}.zip"

            ignore_set = ignore_map.get(folder_name, set())

            try:
                if zip_path.exists():
                    zip_path.unlink()  # overwrite safely

                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for current_dir, dirnames, filenames in os.walk(source_path):
                        current_path = Path(current_dir)

                        # filter directories in-place so os.walk won't descend into them
                        dirnames[:] = [
                            d for d in dirnames if d not in ignore_set]

                        for filename in filenames:
                            if filename in ignore_set:
                                continue

                            file_path = current_path / filename

                            if file_path.suffix.lower() in ignore_ext:
                                continue

                            # relative path inside the zip (include top folder name)
                            arcname = file_path.relative_to(root_dir)

                            try:
                                zf.write(file_path, arcname=str(arcname))
                            except PermissionError:
                                # common on Windows for lock files (.next/dev/lock etc.)
                                self.stdout.write(self.style.WARNING(
                                    f'Skipped locked file: {arcname}'
                                ))

                self.stdout.write(self.style.SUCCESS(
                    f'Created: {zip_path.name}'
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Error while zipping "{folder_name}": {e}'
                ))
