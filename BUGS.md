# ==============================================================================
# PDF Header Tool — BUGS.md
# Triage local des bugs. Confirmer avant d'ouvrir une GitHub Issue.
#
# Workflow :
#   1. Constater un bug → ajouter une entrée dans "Open" ci-dessous
#   2. Bug confirmé et reproductible → ouvrir une GitHub Issue, remplir "Issue GitHub"
#   3. Fix en cours → déplacer vers "In Progress"
#   4. Fix commité → déplacer vers "Fixed" (lien commit + version)
#
# Format d'une entrée :
#   ### [B-NNN] Titre court descriptif
#   - Sévérité    : high | medium | low
#   - Env         : dev | beta | release
#   - Version     : X.Y.Z
#   - Reproduit   : toujours | parfois | non
#   - Steps       :
#   - Attendu / Obtenu :
#   - Log         : (extrait structuré : PDF_INSERT_RESULT, APP_START, etc.)
#   - Fix pressenti :
#   - Issue GitHub : #N (vide si pas encore ouverte)
# ==============================================================================

---

## Open

### [B-001] Échec d'enregistrement avec certaines polices système — "need font file or buffer"
- **Sévérité**   : high
- **Env**        : dev | release
- **Version**    : 0.4.6.11
- **Reproduit**  : toujours (avec les polices système concernées)
- **Steps**      : sélectionner une police système (non built-in), charger un PDF, cliquer Appliquer
- **Attendu / Obtenu** : PDF enregistré avec l'en-tête / boîte de dialogue d'erreur "need font file or buffer"
- **Log**        :
  ```
  [2026-02-23 11:38:11] [ERROR  ] [pdf_header.pdf] PDF_PROCESS_ERROR file=2025-ACH-341.pdf error=need font file or buffer
  ```
- **Analyse révisée** (audit 2026-02-23) : `_get_fitz_font_args()` (`pdf_header.py:791`) vérifie
  déjà `if font_file and Path(str(font_file)).exists()` — il ne passe jamais `fontfile=None` à
  fitz. La cause documentée précédemment était incorrecte.
  Cause réelle probable : `font_file` pointe vers un fichier que `Path.exists()` juge présent
  mais que fitz ne peut pas lire (corrompu, permissions, format non supporté). Dans ce cas,
  `_get_fitz_font_args` retourne `{"fontfile": path, "fontname": "F0"}` et `insert_textbox()`
  lève l'exception — sans être protégée.
  Note : `fitz.Font(fontfile=...)` à la ligne 2245 est dans un `try/except Exception: pass`
  silencieux, mais `insert_textbox(**font_args)` à la ligne 2297 n'a pas de protection
  équivalente pour le même type d'erreur.
- **Fix pressenti (révisé)** : dans `_apply()`, entourer `insert_textbox(**font_args)` d'un
  try/except ciblant l'erreur "font file or buffer". En cas d'échec, retry avec le fallback
  Courier `{"fontname": "cour"}` et logguer `log_font.warning("font_fallback_to_courier ...")`.
  Cela est plus robuste qu'une validation upfront (fitz peut rejeter un fichier que l'OS accepte).
- **Scope** : hors scope 4.7 — fix dans une branche dédiée `fix/b-001-font-fallback`.
- **Issue GitHub** :

---

### [B-002] En-tête mal positionnée et pivotée à 270° sur certains PDFs
- **Sévérité**   : high
- **Env**        : dev | release
- **Version**    : 0.4.6.11
- **Reproduit**  : toujours (sur les PDFs concernés)
- **Steps**      : ouvrir un PDF dont les pages ont un attribut `/Rotate` (ex. scan paysage avec
  rotation 90°), positionner l'en-tête, cliquer Appliquer, ouvrir le PDF généré
- **Attendu / Obtenu** : en-tête au point cliqué, lisible / en-tête collée à gauche de la page,
  pivotée à 270° (illisible)
- **Log**        : consulter `PDF_INSERT_RESULT` — vérifier `page_dims`, `x_pt`, `y_pt` vs dimensions réelles
- **Fix pressenti** : les PDFs avec `/Rotate: 90` (ou 270) ont leurs dimensions `page.rect` déjà
  pivotées par PyMuPDF, mais `insert_textbox()` travaille dans l'espace de coordonnées pré-rotation.
  Dans `_apply()`, lire `page.rotation` et compenser : si rotation != 0, appliquer une transformation
  matricielle (`fitz.Matrix`) ou recalculer `x_pt`/`y_pt` en tenant compte de la rotation de la page
  avant d'appeler `insert_textbox()`.
- **Scope** : hors scope 4.7 — fix dans une branche dédiée `fix/b-002-rotated-pdf`.
- **Issue GitHub** :

---

## In Progress

<!-- Bugs en cours de correction -->

---

## Fixed

<!-- Bugs résolus — conserver pour référence -->
