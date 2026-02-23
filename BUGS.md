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
- **Fix pressenti** : dans `_apply()`, vérifier que `cfg["font_file"]` existe sur le disque avant
  d'appeler `insert_textbox()`. Si le fichier est absent ou None, basculer en fallback sur la police
  intégrée Courier avec un warning `log_font.warning(...)`. Vérifier aussi `_get_fitz_font_args()`
  — si `font_file` est None, la clé `fontfile` passe None à fitz, ce qui déclenche l'erreur.
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
- **Issue GitHub** :

---

## In Progress

<!-- Bugs en cours de correction -->

---

## Fixed

<!-- Bugs résolus — conserver pour référence -->
