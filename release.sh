#!/usr/bin/env bash
# ==============================================================================
# PDF Header Tool — release.sh
# Usage : ./release.sh X.Y.Z [--full-reinstall]
# Prérequis : gh CLI (sudo pacman -S github-cli && gh auth login)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# Arguments
# ------------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    echo "Usage: ./release.sh X.Y.Z [--full-reinstall]"
    exit 1
fi

VERSION="$1"
FULL_REINSTALL=false
if [[ "${2:-}" == "--full-reinstall" ]]; then
    FULL_REINSTALL=true
fi

# Valider le format de version (X.Y, X.Y.Z ou X.Y.Z.W)
if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
    echo "Erreur : format de version invalide. Attendu : X.Y.Z (ex: 0.4.7)"
    exit 1
fi

TAG="v${VERSION}"
TODAY="$(date +%Y.%m.%d)"
BUILD_ID="build-${TODAY}.01"

# Vérifier que le tag n'existe pas déjà (local ou remote)
if git tag -l | grep -q "^${TAG}$"; then
    echo "Erreur : le tag ${TAG} existe déjà en local."
    echo "  Choisissez une nouvelle version, ou supprimez le tag : git tag -d ${TAG}"
    exit 1
fi
if git ls-remote --tags origin | grep -q "refs/tags/${TAG}$"; then
    echo "Erreur : le tag ${TAG} existe déjà sur le remote."
    echo "  Choisissez une nouvelle version."
    exit 1
fi

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
