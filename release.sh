#!/usr/bin/env bash
# ==============================================================================
# PDF Header Tool — release.sh
# Usage : ./release.sh [X.Y.Z] [--full-reinstall]
#         Sans version : auto-bump depuis version.txt
# Prérequis : gh CLI (sudo pacman -S github-cli && gh auth login)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
_bump_patch() {
    # Incrémente le dernier segment : 0.4.6.3 -> 0.4.6.4 / 0.4.7 -> 0.4.8
    echo "$1" | awk -F. -v OFS=. '{$NF=$NF+1; print}'
}

# ------------------------------------------------------------------------------
# Arguments
# ------------------------------------------------------------------------------
FULL_REINSTALL=false
VERSION=""

for arg in "$@"; do
    case "$arg" in
        --full-reinstall) FULL_REINSTALL=true ;;
        --*)
            echo "Erreur : option inconnue : $arg"
            echo "Usage: ./release.sh [X.Y.Z] [--full-reinstall]"
            exit 1
            ;;
        *) VERSION="$arg" ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    CURRENT_VERSION=$(cat version.txt 2>/dev/null | tr -d '[:space:]' || echo "0.4.0")
    VERSION=$(_bump_patch "$CURRENT_VERSION")
    echo "  Auto-bump : ${CURRENT_VERSION} -> ${VERSION}"
fi

# Valider le format de version (X.Y, X.Y.Z ou X.Y.Z.W)
if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
    echo "Erreur : format de version invalide. Attendu : X.Y.Z (ex: 0.4.7)"
    exit 1
fi

TAG="v${VERSION}"
TODAY="$(date +%Y.%m.%d)"
BUILD_ID="build-${TODAY}.01"

# ------------------------------------------------------------------------------
# Vérifier si le tag existe déjà → menu interactif
# ------------------------------------------------------------------------------
LOCAL_TAG_EXISTS=false
REMOTE_TAG_EXISTS=false
if git tag -l | grep -q "^${TAG}$"; then LOCAL_TAG_EXISTS=true; fi
if git ls-remote --tags origin 2>/dev/null | grep -q "refs/tags/${TAG}$"; then REMOTE_TAG_EXISTS=true; fi

if [[ "$LOCAL_TAG_EXISTS" == "true" || "$REMOTE_TAG_EXISTS" == "true" ]]; then
    echo ""
    echo "  Le tag ${TAG} existe deja :"
    if [[ "$LOCAL_TAG_EXISTS"  == "true" ]]; then echo "    - en local"; fi
    if [[ "$REMOTE_TAG_EXISTS" == "true" ]]; then echo "    - sur le remote"; fi
    echo ""
    echo "  1) Ecraser  — supprimer le tag existant et recreer"
    echo "  2) Bump     — utiliser $(_bump_patch "$VERSION") a la place"
    echo "  3) Annuler"
    echo ""
    read -rp "  Votre choix [1/2/3] : " CHOICE
    case "$CHOICE" in
        1)
            echo "  Suppression du tag ${TAG}..."
            if [[ "$LOCAL_TAG_EXISTS"  == "true" ]]; then git tag -d "${TAG}"; fi
            if [[ "$REMOTE_TAG_EXISTS" == "true" ]]; then git push origin --delete "${TAG}" || true; fi
            ;;
        2)
            VERSION=$(_bump_patch "$VERSION")
            TAG="v${VERSION}"
            BUILD_ID="build-$(date +%Y.%m.%d).01"
            echo "  Nouvelle version : ${VERSION}"
            ;;
        3)
            echo "  Annule."
            exit 0
            ;;
        *)
            echo "  Choix invalide. Annule."
            exit 1
            ;;
    esac
fi

echo ""
echo "======================================================"
echo "  PDF Header Tool — Release ${TAG}"
echo "  Build ID : ${BUILD_ID}"
echo "  Full reinstall : ${FULL_REINSTALL}"
echo "======================================================"
echo ""

# ------------------------------------------------------------------------------
# 1. Mettre à jour VERSION dans pdf_header.py
# ------------------------------------------------------------------------------
echo "[1/9] Mise a jour VERSION dans pdf_header.py..."
sed -i "s/^VERSION     = .*/VERSION     = \"${VERSION}\"/" pdf_header.py
sed -i "s/^BUILD_ID    = .*/BUILD_ID    = \"${BUILD_ID}\"/" pdf_header.py

# ------------------------------------------------------------------------------
# 2. Mettre à jour version.txt
# ------------------------------------------------------------------------------
echo "[2/9] Mise a jour version.txt..."
echo "${VERSION}" > version.txt

# ------------------------------------------------------------------------------
# 3. Mettre à jour BUILD_ID dans build_dist.py
# ------------------------------------------------------------------------------
echo "[3/9] Mise a jour BUILD_ID dans build_dist.py..."
sed -i "s/^BUILD_ID *=.*/BUILD_ID = \"${BUILD_ID}\"/" build_dist.py

# ------------------------------------------------------------------------------
# 4. Valider syntaxe Python
# ------------------------------------------------------------------------------
echo "[4/9] Validation syntaxe Python..."
python3 -c "import ast; ast.parse(open('pdf_header.py').read()); print('  pdf_header.py : OK')"

# ------------------------------------------------------------------------------
# 5. Commit
# ------------------------------------------------------------------------------
echo "[5/9] Commit..."
git add pdf_header.py version.txt build_dist.py
git commit -m "chore: bump version ${TAG}"

# ------------------------------------------------------------------------------
# 6. Tag
# ------------------------------------------------------------------------------
echo "[6/9] Tag ${TAG}..."
git tag "${TAG}"

# ------------------------------------------------------------------------------
# 7. Push
# ------------------------------------------------------------------------------
echo "[7/9] Push origin main + ${TAG}..."
git push origin main
git push origin "${TAG}"

# ------------------------------------------------------------------------------
# 8. Build distribution
# ------------------------------------------------------------------------------
echo "[8/9] Build distribution..."
if [[ "$FULL_REINSTALL" == "true" ]]; then
    python3 build_dist.py --full-reinstall
else
    python3 build_dist.py
fi

# ------------------------------------------------------------------------------
# 9. Upload assets vers GitHub Release
# ------------------------------------------------------------------------------
echo "[9/9] Upload assets..."
PATCH_ZIP="dist/app-patch-${VERSION}.zip"
FULL_ZIP=$(ls dist/PDFHeaderTool-v${VERSION}-*.zip 2>/dev/null | head -1 || true)
METADATA="dist/metadata.json"

if command -v gh &>/dev/null; then
    UPLOAD_ARGS=()
    [[ -f "$METADATA" ]]  && UPLOAD_ARGS+=("$METADATA")
    [[ -f "$PATCH_ZIP" ]] && UPLOAD_ARGS+=("$PATCH_ZIP")
    [[ -f "$FULL_ZIP" ]]  && UPLOAD_ARGS+=("$FULL_ZIP")

    if [[ ${#UPLOAD_ARGS[@]} -gt 0 ]]; then
        # Attendre que GitHub Actions ait cree la Release
        echo "  Attente de la GitHub Release..."
        for i in $(seq 1 12); do
            if gh release view "${TAG}" &>/dev/null 2>&1; then
                break
            fi
            echo "  Attente... (${i}/12)"
            sleep 5
        done
        gh release upload "${TAG}" "${UPLOAD_ARGS[@]}" --clobber
        echo "  Assets uploades avec succes."
    else
        echo "  Aucun asset trouve dans dist/ — rien a uploader."
    fi
else
    echo ""
    echo "  gh CLI non installe. Pour uploader manuellement :"
    echo "  sudo pacman -S github-cli && gh auth login"
    echo "  Puis :"
    [[ -f "$METADATA" ]]  && echo "    gh release upload ${TAG} ${METADATA} --clobber"
    [[ -f "$PATCH_ZIP" ]] && echo "    gh release upload ${TAG} ${PATCH_ZIP} --clobber"
    [[ -f "$FULL_ZIP" ]]  && echo "    gh release upload ${TAG} ${FULL_ZIP} --clobber"
fi

echo ""
echo "======================================================"
echo "  Release ${TAG} terminee."
echo "======================================================"
