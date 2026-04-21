from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_fixture_export(export_path: str, fixtures: dict[str, Any]) -> Path:
    output_path = Path(export_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(fixtures, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path