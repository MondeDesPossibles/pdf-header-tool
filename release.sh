#!/usr/bin/env bash
# ==============================================================================
# PDF Header Tool — release.sh
# Usage : ./release.sh [X.Y.Z[-beta.N]] [--full-reinstall] [--beta]
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
    # Incrémente le dernier segment numérique : 0.4.6.3 -> 0.4.6.4 / 0.4.7 -> 0.4.8
    echo "$1" | awk -F. -v OFS=. '{$NF=$NF+1; print}'
}

_bump_beta() {
    # Incrémente le N dans X.Y.Z-beta.N : 0.4.7-beta.1 -> 0.4.7-beta.2
    local base suffix n
    base="${1%-beta.*}"
    suffix="${1##*-beta.}"
    n=$((suffix + 1))
    echo "${base}-beta.${n}"
}

_is_beta_version() {
    [[ "$1" == *"-beta."* ]]
}

# ------------------------------------------------------------------------------
# Arguments
# ------------------------------------------------------------------------------
FULL_REINSTALL=false
BETA=false
VERSION=""

for arg in "$@"; do
    case "$arg" in
        --full-reinstall) FULL_REINSTALL=true ;;
        --beta) BETA=true ;;
        --*)
            echo "Erreur : option inconnue : $arg"
            echo "Usage: ./release.sh [X.Y.Z[-beta.N]] [--full-reinstall] [--beta]"
            exit 1
            ;;
        *) VERSION="$arg" ;;
    esac
done

# Auto-bump si pas de version fournie
if [[ -z "$VERSION" ]]; then
    CURRENT_VERSION=$(cat version.txt 2>/dev/null | tr -d '[:space:]' || echo "0.4.0")
    if [[ "$BETA" == "true" ]]; then
        if _is_beta_version "$CURRENT_VERSION"; then
            VERSION=$(_bump_beta "$CURRENT_VERSION")
        else
            # Première beta depuis une version stable : X.Y.Z -> X.Y.Z-beta.1
            VERSION="${CURRENT_VERSION}-beta.1"
        fi
    else
        if _is_beta_version "$CURRENT_VERSION"; then
            # Passer d'une beta à la version stable correspondante
            VERSION="${CURRENT_VERSION%-beta.*}"
        else
            VERSION=$(_bump_patch "$CURRENT_VERSION")
        fi
    fi
    echo "  Auto-bump : ${CURRENT_VERSION} -> ${VERSION}"
fi

# Valider le format de version (X.Y, X.Y.Z, X.Y.Z.W, X.Y.Z-beta.N, X.Y.Z.W-beta.N)
if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)+(-beta\.[0-9]+)?$ ]]; then
    echo "Erreur : format de version invalide."
    echo "  Stable : X.Y.Z  (ex: 0.4.7)"
    echo "  Beta   : X.Y.Z-beta.N  (ex: 0.4.7-beta.1)"
    exit 1
fi

# Détecter automatiquement si c'est une beta d'après la version
if _is_beta_version "$VERSION"; then
    BETA=true
fi

TAG="v${VERSION}"
TODAY="$(date +%Y.%m.%d)"
BUILD_ID="build-${TODAY}.01"
CHANNEL="release"
[[ "$BETA" == "true" ]] && CHANNEL="beta"

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
    if [[ "$BETA" == "true" ]]; then
        echo "  2) Bump     — utiliser $(_bump_beta "$VERSION") a la place"
    else
        echo "  2) Bump     — utiliser $(_bump_patch "$VERSION") a la place"
    fi
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
            if [[ "$BETA" == "true" ]]; then
                VERSION=$(_bump_beta "$VERSION")
            else
                VERSION=$(_bump_patch "$VERSION")
            fi
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
echo "  Canal   : ${CHANNEL}"
echo "  Build ID : ${BUILD_ID}"
echo "  Full reinstall : ${FULL_REINSTALL}"
echo "======================================================"
echo ""

# ------------------------------------------------------------------------------
# 1. Mettre à jour VERSION, BUILD_ID et CHANNEL dans pdf_header.py
# ------------------------------------------------------------------------------
echo "[1/9] Mise a jour VERSION/CHANNEL dans pdf_header.py..."
sed -i "s/^VERSION     = .*/VERSION     = \"${VERSION}\"/" pdf_header.py
sed -i "s/^BUILD_ID    = .*/BUILD_ID    = \"${BUILD_ID}\"/" pdf_header.py
sed -i "s/^CHANNEL     = .*/CHANNEL     = \"${CHANNEL}\"/" pdf_header.py

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
git commit -m "chore: bump version ${TAG} [${CHANNEL}]"

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
PATCH_ZIP="dist/app-patch-${TAG}.zip"
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
        if [[ "$BETA" == "true" ]]; then
            gh release edit "${TAG}" --prerelease
            echo "  Release marquee comme pre-release."
        fi
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
    [[ "$BETA" == "true" ]] && echo "    gh release edit ${TAG} --prerelease"
    [[ -f "$METADATA" ]]  && echo "    gh release upload ${TAG} ${METADATA} --clobber"
    [[ -f "$PATCH_ZIP" ]] && echo "    gh release upload ${TAG} ${PATCH_ZIP} --clobber"
    [[ -f "$FULL_ZIP" ]]  && echo "    gh release upload ${TAG} ${FULL_ZIP} --clobber"
fi

echo ""
echo "======================================================"
echo "  Release ${TAG} [${CHANNEL}] terminee."
echo "======================================================"
