# ==============================================================================
# app/models.py — Dataclasses préparatoires (Étape 4.7 substep-5)
# Non utilisées directement en v0.4.7 — prévues pour les tests (Étape 4.9+)
# et comme contrats entre les services.
# ==============================================================================

from __future__ import annotations  # Python 3.8 compat pour les annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FontDescriptor:
    """Décrit une police : nom d'affichage, chemin fichier et type (builtin/système)."""
    name: str
    path: Path | None
    is_builtin: bool


@dataclass
class Position:
    """Position courante du texte : ratios [0.0-1.0], preset et marges en pts PDF."""
    ratio_x: float
    ratio_y: float
    preset_key: str
    margin_x_pt: float
    margin_y_pt: float


@dataclass
class InsertResult:
    """Résultat de l'insertion d'un en-tête sur une page (retour de insert_header())."""
    remaining_chars: int
    truncated: bool
    text_rect: tuple
    applied_ratio_x: float
    applied_ratio_y: float
