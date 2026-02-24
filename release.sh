#!/usr/bin/env bash
# ==============================================================================
# PDF Header Tool — release.sh
# Usage : ./release.sh [X.Y.Z[-beta.N]] [--full-reinstall] [--beta]
#         [--branch <name>] [--dry-run] [--list-package]
#         Sans version : auto-bump depuis version.txt
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
_bump_patch() {
    echo "$1" | awk -F. -v OFS=. '{$NF=$NF+1; print}'
}

_bump_beta() {
    local base suffix n
    base="${1%-beta.*}"
    suffix="${1##*-beta.}"
    n=$((suffix + 1))
    echo "${base}-beta.${n}"
}

_is_beta_version() {
    [[ "$1" == *"-beta."* ]]
}

_usage() {
    cat <<USAGE
Usage: ./release.sh [X.Y.Z[-beta.N]] [--full-reinstall] [--beta] [--branch <name>] [--dry-run] [--list-package]

Options:
  --beta             Canal beta (pre-release)
  --full-reinstall   Marque metadata requires_full_reinstall=true
  --branch <name>    Branche de push/tag (defaut: branche courante)
  --dry-run          Valide et affiche le plan sans modifier git/fichiers
  --list-package     Affiche la whitelist de packaging via build_dist.py --list-files
USAGE
}

_get_var_value() {
    local file="$1"
    local key="$2"
    sed -n "s/^${key}[[:space:]]*=[[:space:]]*\"\([^\"]*\)\"/\1/p" "$file" | head -1
}

_require_clean_worktree() {
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "ERREUR: working tree non propre. Committez/stashez avant release." >&2
        git status --short
        exit 1
    fi
}

_validate_build_id_format() {
    local v="$1"
    if ! [[ "$v" =~ ^build-[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]{2}$ ]]; then
        echo "ERREUR: BUILD_ID invalide: $v (attendu: build-YYYY.MM.DD.NN)" >&2
        exit 1
    fi
}

_validate_current_consistency() {
    local v_file v_py b_py b_dist b_launcher c_py
    v_file="$(tr -d '[:space:]' < version.txt)"
    v_py="$(_get_var_value pdf_header.py VERSION)"
    b_py="$(_get_var_value pdf_header.py BUILD_ID)"
    c_py="$(_get_var_value pdf_header.py CHANNEL)"
    b_dist="$(sed -n 's/^BUILD_ID[[:space:]]*=[[:space:]]*"\([^"]*\)"/\1/p' build_dist.py | head -1)"
    b_launcher="$(sed -n 's/^set "BUILD_ID=\(build-[0-9.]*\)"/\1/p' lancer.bat | head -1)"

    if [[ -z "$v_py" || -z "$b_py" || -z "$c_py" || -z "$b_dist" || -z "$b_launcher" ]]; then
        echo "ERREUR: impossible de lire VERSION/BUILD_ID/CHANNEL dans les fichiers cibles." >&2
        exit 1
    fi

    if [[ "$v_file" != "$v_py" ]]; then
        echo "ERREUR: incoherence version.txt ($v_file) vs pdf_header.py VERSION ($v_py)." >&2
        exit 1
    fi

    if [[ "$b_py" != "$b_dist" ]]; then
        echo "ERREUR: incoherence BUILD_ID pdf_header.py ($b_py) vs build_dist.py ($b_dist)." >&2
        exit 1
    fi

    if [[ "$b_py" != "$b_launcher" ]]; then
        echo "ERREUR: incoherence BUILD_ID pdf_header.py ($b_py) vs lancer.bat ($b_launcher)." >&2
        exit 1
    fi

    _validate_build_id_format "$b_py"
}

_validate_branch_state() {
    local target_branch="$1"
    local current_branch
    current_branch="$(git branch --show-current)"

    if [[ "$current_branch" != "$target_branch" ]]; then
        echo "ERREUR: branche courante=$current_branch, --branch=$target_branch. Basculez d'abord sur la branche cible." >&2
        exit 1
    fi

    if git show-ref --verify --quiet "refs/remotes/origin/${target_branch}"; then
        local ahead behind
        read -r ahead behind < <(git rev-list --left-right --count "HEAD...origin/${target_branch}" | awk '{print $1, $2}')
        if [[ "$behind" -gt 0 ]]; then
            echo "ERREUR: la branche est en retard de ${behind} commit(s) sur origin/${target_branch}." >&2
            echo "Action: git pull --rebase origin ${target_branch}" >&2
            exit 1
        fi
    fi
}

_validate_github_prerequisites() {
    local origin_url repo_slug
    origin_url="$(git remote get-url origin 2>/dev/null || true)"

    if [[ -z "$origin_url" ]]; then
        echo "ERREUR: remote 'origin' introuvable." >&2
        exit 1
    fi

    # Le workflow release attendu repose sur SSH pour git push.
    if ! [[ "$origin_url" =~ ^git@ ]] && ! [[ "$origin_url" =~ ^ssh:// ]]; then
        echo "ERREUR: remote origin non configure en SSH: $origin_url" >&2
        echo "Action: configurez une URL SSH (git@... ou ssh://...) puis relancez." >&2
        exit 1
    fi

    if ! git ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
        echo "ERREUR: acces SSH a origin indisponible (reseau/cle/permissions)." >&2
        echo "Action: verifiez votre cle SSH et la connectivite, puis relancez." >&2
        exit 1
    fi

    if ! command -v gh >/dev/null 2>&1; then
        echo "ERREUR: gh CLI non installe. Necessaire pour marquer pre-release et uploader les assets." >&2
        echo "Action: installez gh puis relancez." >&2
        exit 1
    fi

    if ! gh auth status >/dev/null 2>&1; then
        echo "ERREUR: gh CLI non authentifie." >&2
        echo "Action: executez 'gh auth login' puis relancez." >&2
        exit 1
    fi

    # Extraire owner/repo depuis l'URL origin pour verifier que gh cible le bon depot.
    case "$origin_url" in
        git@*:*/*.git)
            repo_slug="${origin_url#*:}"
            repo_slug="${repo_slug%.git}"
            ;;
        git@*:*/*)
            repo_slug="${origin_url#*:}"
            ;;
        ssh://git@*/*.git)
            repo_slug="${origin_url#ssh://git@*/}"
            repo_slug="${repo_slug%.git}"
            ;;
        ssh://git@*/*)
            repo_slug="${origin_url#ssh://git@*/}"
            ;;
        *)
            echo "ERREUR: format d'URL origin non supporte: $origin_url" >&2
            echo "Action: utilisez une URL SSH standard vers GitHub." >&2
            exit 1
            ;;
    esac

    if ! [[ "$repo_slug" =~ ^[^/]+/[^/]+$ ]]; then
        echo "ERREUR: impossible d'extraire owner/repo depuis origin: $origin_url" >&2
        exit 1
    fi

    if ! gh repo view "$repo_slug" >/dev/null 2>&1; then
        echo "ERREUR: gh est authentifie mais n'a pas acces au depot $repo_slug." >&2
        echo "Action: verifiez le compte actif (gh auth status) et les droits repo, puis relancez." >&2
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# Arguments
# ------------------------------------------------------------------------------
FULL_REINSTALL=false
BETA=false
DRY_RUN=false
LIST_PACKAGE=false
VERSION=""
TARGET_BRANCH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full-reinstall)
            FULL_REINSTALL=true
            shift
            ;;
        --beta)
            BETA=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --list-package)
            LIST_PACKAGE=true
            shift
            ;;
        --branch)
            [[ $# -lt 2 ]] && { echo "ERREUR: --branch requiert une valeur" >&2; _usage; exit 1; }
            TARGET_BRANCH="$2"
            shift 2
            ;;
        --help|-h)
            _usage
            exit 0
            ;;
        --*)
            echo "ERREUR: option inconnue $1" >&2
            _usage
            exit 1
            ;;
        *)
            if [[ -n "$VERSION" ]]; then
                echo "ERREUR: plusieurs versions passees ($VERSION, $1)" >&2
                exit 1
            fi
            VERSION="$1"
            shift
            ;;
    esac
done

if [[ -z "$TARGET_BRANCH" ]]; then
    TARGET_BRANCH="$(git branch --show-current)"
fi

if [[ -z "$VERSION" ]]; then
    CURRENT_VERSION=$(cat version.txt 2>/dev/null | tr -d '[:space:]' || echo "0.4.0")
    if [[ "$BETA" == "true" ]]; then
        if _is_beta_version "$CURRENT_VERSION"; then
            VERSION=$(_bump_beta "$CURRENT_VERSION")
        else
            VERSION="${CURRENT_VERSION}-beta.1"
        fi
    else
        if _is_beta_version "$CURRENT_VERSION"; then
            VERSION="${CURRENT_VERSION%-beta.*}"
        else
            VERSION=$(_bump_patch "$CURRENT_VERSION")
        fi
    fi
    echo "  Auto-bump : ${CURRENT_VERSION} -> ${VERSION}"
fi

if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)+(-beta\.[0-9]+)?$ ]]; then
    echo "ERREUR: format de version invalide ($VERSION)." >&2
    echo "  Stable : X.Y.Z" >&2
    echo "  Beta   : X.Y.Z-beta.N" >&2
    exit 1
fi

if _is_beta_version "$VERSION"; then
    BETA=true
fi

TAG="v${VERSION}"
TODAY="$(date +%Y.%m.%d)"
BUILD_ID="build-${TODAY}.01"
CHANNEL="release"
[[ "$BETA" == "true" ]] && CHANNEL="beta"

_validate_current_consistency
_validate_branch_state "$TARGET_BRANCH"

if [[ "$DRY_RUN" != "true" ]]; then
    _validate_github_prerequisites
    _require_clean_worktree
fi

if [[ "$LIST_PACKAGE" == "true" ]]; then
    echo "[LIST] Whitelist packaging (build_dist.py --list-files)"
    python3 build_dist.py --list-files
fi

LOCAL_TAG_EXISTS=false
REMOTE_TAG_EXISTS=false
if git tag -l | grep -q "^${TAG}$"; then LOCAL_TAG_EXISTS=true; fi
if git ls-remote --tags origin 2>/dev/null | grep -q "refs/tags/${TAG}$"; then REMOTE_TAG_EXISTS=true; fi

if [[ "$LOCAL_TAG_EXISTS" == "true" || "$REMOTE_TAG_EXISTS" == "true" ]]; then
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY-RUN] Tag ${TAG} existe deja (local=$LOCAL_TAG_EXISTS remote=$REMOTE_TAG_EXISTS)."
    else
        echo ""
        echo "Le tag ${TAG} existe deja :"
        [[ "$LOCAL_TAG_EXISTS" == "true" ]] && echo "  - local"
        [[ "$REMOTE_TAG_EXISTS" == "true" ]] && echo "  - remote"
        echo ""
        echo "  1) Ecraser"
        if [[ "$BETA" == "true" ]]; then
            echo "  2) Bump vers $(_bump_beta "$VERSION")"
        else
            echo "  2) Bump vers $(_bump_patch "$VERSION")"
        fi
        echo "  3) Annuler"
        read -rp "Votre choix [1/2/3] : " CHOICE
        case "$CHOICE" in
            1)
                [[ "$LOCAL_TAG_EXISTS" == "true" ]] && git tag -d "${TAG}"
                [[ "$REMOTE_TAG_EXISTS" == "true" ]] && git push origin --delete "${TAG}" || true
                ;;
            2)
                if [[ "$BETA" == "true" ]]; then
                    VERSION=$(_bump_beta "$VERSION")
                else
                    VERSION=$(_bump_patch "$VERSION")
                fi
                TAG="v${VERSION}"
                BUILD_ID="build-$(date +%Y.%m.%d).01"
                echo "Nouvelle version: $VERSION"
                ;;
            3)
                echo "Annule."
                exit 0
                ;;
            *)
                echo "Choix invalide." >&2
                exit 1
                ;;
        esac
    fi
fi

echo ""
echo "======================================================"
echo "  PDF Header Tool — Release ${TAG}"
echo "  Canal          : ${CHANNEL}"
echo "  Build ID       : ${BUILD_ID}"
echo "  Branche cible  : ${TARGET_BRANCH}"
echo "  Full reinstall : ${FULL_REINSTALL}"
echo "  Dry-run        : ${DRY_RUN}"
echo "======================================================"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY-RUN] Vérifications cibles :"
    echo "  - MAJ pdf_header.py VERSION/BUILD_ID/CHANNEL"
    echo "  - MAJ version.txt"
    echo "  - MAJ build_dist.py BUILD_ID"
    echo "  - MAJ lancer.bat BUILD_ID"
    echo "  - Commit + tag + push branche ${TARGET_BRANCH} + push tag"
    echo "  - Build distribution (build_dist.py)"
    echo "  - Upload metadata/patch/full zip"
    exit 0
fi

echo "[1/10] Mise a jour VERSION/BUILD_ID/CHANNEL..."
sed -i "s/^# Build   :.*/# Build   : ${BUILD_ID}/" pdf_header.py
sed -i "s/^VERSION     = .*/VERSION     = \"${VERSION}\"/" pdf_header.py
sed -i "s/^BUILD_ID    = .*/BUILD_ID    = \"${BUILD_ID}\"/" pdf_header.py
sed -i "s/^CHANNEL     = .*/CHANNEL     = \"${CHANNEL}\"/" pdf_header.py

echo "[2/10] Mise a jour version.txt..."
echo "${VERSION}" > version.txt

echo "[3/10] Mise a jour BUILD_ID dans build_dist.py..."
sed -i "s/^# Build   :.*/# Build   : ${BUILD_ID}/" build_dist.py
sed -i "s/^BUILD_ID *=.*/BUILD_ID = \"${BUILD_ID}\"/" build_dist.py

echo "[4/10] Mise a jour BUILD_ID dans lancer.bat..."
sed -i "s/^set \"BUILD_ID=.*/set \"BUILD_ID=${BUILD_ID}\"/" lancer.bat
sed -i "s/^:: Build   :.*/:: Build   : ${BUILD_ID}/" lancer.bat

echo "[5/10] Validation syntaxe Python..."
python3 -c "import ast; ast.parse(open('pdf_header.py').read()); print('  pdf_header.py : OK')"
python3 -c "import ast; ast.parse(open('build_dist.py').read()); print('  build_dist.py : OK')"

_validate_current_consistency

echo "[6/10] Commit..."
git add pdf_header.py version.txt build_dist.py lancer.bat
git commit -m "chore: bump version ${TAG} [${CHANNEL}]"

echo "[7/10] Tag ${TAG}..."
git tag "${TAG}"

echo "[8/10] Push origin ${TARGET_BRANCH} + ${TAG}..."
git push origin "${TARGET_BRANCH}"
git push origin "${TAG}"

echo "[9/10] Build distribution..."
if [[ "$FULL_REINSTALL" == "true" ]]; then
    python3 build_dist.py --full-reinstall
else
    python3 build_dist.py
fi

echo "[10/10] Upload assets..."
PATCH_ZIP="dist/app-patch-${TAG}.zip"
FULL_ZIP=$(ls dist/PDFHeaderTool-v${VERSION}-*.zip 2>/dev/null | head -1 || true)
METADATA="dist/metadata.json"

if command -v gh &>/dev/null; then
    UPLOAD_ARGS=()
    [[ -f "$METADATA" ]]  && UPLOAD_ARGS+=("$METADATA")
    [[ -f "$PATCH_ZIP" ]] && UPLOAD_ARGS+=("$PATCH_ZIP")
    [[ -f "$FULL_ZIP" ]]  && UPLOAD_ARGS+=("$FULL_ZIP")

    if [[ ${#UPLOAD_ARGS[@]} -gt 0 ]]; then
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
fi

echo ""
echo "======================================================"
echo "  Release ${TAG} [${CHANNEL}] terminee."
echo "======================================================"
