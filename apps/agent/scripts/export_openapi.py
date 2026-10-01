"""Exporta o contrato da API sem subir servidor nem banco.

Uso: uv run python scripts/export_openapi.py > openapi.json
"""

import json
import os
import sys

os.environ.setdefault("OPENROUTER_API_KEY", "export")
os.environ.setdefault("DATABASE_URL", "postgresql://export")

from agent.api.main import create_app  # noqa: E402

json.dump(create_app().openapi(), sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
