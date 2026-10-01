"""Configuración de pytest: hace importable la raíz del repositorio para que
`api.gap_heuristic` resuelva sin instalar el paquete.

  pytest data_pipeline/tests/ -v
  pytest -q              (desde la raíz del repositorio)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
