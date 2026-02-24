# ==============================================================================
# app/services/sort_service.py — Tri naturel pour chemins/fichiers
# ==============================================================================

import re
from pathlib import Path
from typing import Iterable

_NATURAL_SPLIT_RE = re.compile(r"(\d+)")


def natural_sort_key(value: str | Path) -> tuple:
    """Retourne une clé de tri naturel (ex: fichier_2 < fichier_10)."""
    text = value.name if isinstance(value, Path) else str(value)
    parts = _NATURAL_SPLIT_RE.split(text.casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def sort_paths_natural(paths: Iterable[Path]) -> list[Path]:
    """Trie une collection de Path en ordre naturel sur le nom de fichier."""
    return sorted(paths, key=natural_sort_key)
