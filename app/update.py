# ==============================================================================
# app/update.py — Vérification et application des mises à jour automatiques
# Déplacé depuis pdf_header.py lors de l'Étape 4.7 (substep-5)
#
# CONTRAINTE BOOTSTRAP : ce module n'importe aucun module lourd au niveau
# module (fitz, tkinter, customtkinter, PIL). Stdlib uniquement.
# ==============================================================================

import json
import logging
import os
import shutil
import sys
import threading
import urllib.request
import urllib.error
from pathlib import Path

log_update = logging.getLogger("pdf_header.update")

# Callback notifiée quand une mise à jour est mise en attente (staged).
# Définie par PDFHeaderApp via set_staged_callback() après l'init de l'UI.
# Le thread de MAJ peut être lancé avant que la callback soit enregistrée —
# il lit ce global au moment où il en a besoin (après latence réseau).
_staged_callback = None


def set_staged_callback(cb) -> None:
    """Enregistre la callback appelée quand une MAJ est prête (callable(version: str))."""
    global _staged_callback
    _staged_callback = cb


def apply_pending_update(install_dir: Path) -> str:
    """Applique un patch téléchargé lors du lancement précédent.

    Doit être appelée avant _bootstrap() — ne lève jamais d'exception.
    Retourne la nouvelle version appliquée (str non vide) ou '' si aucun patch.
    Si un patch est appliqué et que le redémarrage réussit, cette fonction ne retourne pas.
    """
    import datetime
    def _ts():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    staging = install_dir / "_update_pending"
    if not staging.exists():
        return ""
    print(f"[{_ts()}] UPDATE_APPLY dossier en attente detecte")
    try:
        moved = []
        for src in staging.iterdir():
            if src.name.startswith("_"):
                continue
            dst = install_dir / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved.append(src.name)
        for name in moved:
            print(f"[{_ts()}] UPDATE_APPLY fichier applique: {name}")
        delete_file = staging / "_delete.json"
        if delete_file.exists():
            for f in json.loads(delete_file.read_text()):
                target = install_dir / f
                if target.exists():
                    target.unlink()
                    print(f"[{_ts()}] UPDATE_APPLY fichier supprime: {f}")
        version_file = staging / "_target_version.txt"
        new_version = ""
        if version_file.exists():
            new_version = version_file.read_text().strip()
            (install_dir / "version.txt").write_text(version_file.read_text())
        shutil.rmtree(staging)
        if new_version:
            print(f"[{_ts()}] UPDATE_APPLY succes — version appliquee: {new_version}")
            # Redémarrer immédiatement : le patch est sur disque mais le process
            # en cours a déjà chargé l'ancien code en mémoire. Le restart charge
            # la nouvelle version dès ce lancement (et non au suivant).
            print(f"[{_ts()}] UPDATE_APPLY redemarrage pour charger v{new_version}...")
            import subprocess
            try:
                if sys.platform == "win32":
                    subprocess.Popen(
                        [sys.executable] + sys.argv,
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
                    )
                else:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                sys.exit(0)
            except Exception as restart_err:
                print(f"[{_ts()}] UPDATE_APPLY redemarrage impossible: {restart_err} — nouvelle version active au prochain lancement")
        else:
            print(f"[{_ts()}] UPDATE_APPLY succes")
        return new_version
    except Exception as e:
        print(f"[{_ts()}] UPDATE_APPLY ERREUR: {e}")
        return ""


def _version_gt(remote: str, local: str) -> bool:
    """Retourne True si remote est strictement plus récent que local.

    Formats supportés : X.Y.Z  /  X.Y.Z.W  /  X.Y.Z-beta.N  /  X.Y.Z.W-beta.N
    Ordre : stable > beta > alpha pour une même base numérique.
    Stdlib-only — aucune dépendance externe requise.
    """
    import re

    def _parse(v: str):
        m = re.match(
            r'^(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?(?:-(alpha|beta)\.(\d+))?$',
            v.strip()
        )
        if not m:
            # Format inconnu → considérer comme très ancien pour ne pas déclencher d'update
            return (0, 0, 0, 0, 0, 0)
        nums = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0))
        pre_order = {'alpha': 0, 'beta': 1}
        pre_type = pre_order.get(m.group(5), 99) if m.group(5) else 99  # 99 = stable
        pre_num = int(m.group(6)) if m.group(6) else 0
        return (*nums, pre_type, pre_num)

    return _parse(remote) > _parse(local)


def _check_update_thread(
    running_version: str,
    channel: str,
    github_repo: str,
    install_dir: Path,
    timings: dict,
) -> None:
    """Thread daemon de vérification de mise à jour via GitHub Releases API.

    Interroge l'API selon le canal (release→/releases/latest, beta→/releases[0]).
    Si nouvelle version disponible : télécharge metadata.json puis app-patch-vX.Y.Z.zip,
    vérifie SHA256, extrait dans _update_pending/.
    Silencieux en cas d'erreur réseau (ne bloque jamais le démarrage de l'app).
    """
    import datetime
    def _ts():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        print(f"[{_ts()}] UPDATE_CHECK version courante: {running_version}")
        log_update.debug(f"UPDATE_CHECK_START version={running_version} channel={channel}")
        import ssl
        try:
            import certifi
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            print(f"[{_ts()}] UPDATE_CHECK SSL: certifi {certifi.__version__}")
        except ImportError:
            ssl_ctx = ssl.create_default_context()
            print(f"[{_ts()}] UPDATE_CHECK SSL: contexte systeme (certifi absent)")

        print(f"[{_ts()}] UPDATE_CHECK canal: {channel}")
        if channel == "beta":
            api_url = f"https://api.github.com/repos/{github_repo}/releases"
        else:
            api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "PDFHeaderTool", "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=timings["update_version_timeout"], context=ssl_ctx) as r:
            data = json.loads(r.read().decode())

        # Canal beta : data est une liste → prendre la première (la plus récente)
        # Canal release : data est l'objet release directement
        release = data[0] if channel == "beta" and isinstance(data, list) else data
        if not release:
            return

        tag_name = release.get("tag_name", "")
        remote_version = tag_name.lstrip("v")
        if not remote_version or not _version_gt(remote_version, running_version):
            print(f"[{_ts()}] UPDATE_CHECK deja a jour")
            log_update.info(f"UPDATE_CHECK_OK local={running_version} remote={remote_version}")
            return
        print(f"[{_ts()}] UPDATE_CHECK nouvelle version disponible: {remote_version}")
        log_update.info(f"UPDATE_AVAILABLE local={running_version} remote={remote_version}")

        # 2. Indexer les assets de la release
        assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
        meta_url = assets.get("metadata.json")
        if not meta_url:
            print(f"[{_ts()}] UPDATE_CHECK release sans metadata.json — ignore")
            return

        # 3. Télécharger metadata.json
        req2 = urllib.request.Request(meta_url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req2, timeout=timings["update_version_timeout"], context=ssl_ctx) as r:
            meta = json.loads(r.read().decode())

        # 4. Vérifier si une réinstallation complète est requise
        if meta.get("requires_full_reinstall", True):
            print(f"[{_ts()}] UPDATE_CHECK reinstallation complete requise — ignore (prevu 4.7+)")
            log_update.debug(f"UPDATE_FULL_REQUIRED {running_version} -> {remote_version}")
            return

        # 5. Télécharger app-patch.zip
        patch_info = meta.get("patch_zip", {})
        patch_name = patch_info.get("name", "")
        patch_sha256 = patch_info.get("sha256", "")
        patch_url = assets.get(patch_name)
        if not patch_url:
            print(f"[{_ts()}] UPDATE_CHECK patch absent des assets de la release: {patch_name}")
            return
        print(f"[{_ts()}] UPDATE_CHECK telechargement patch: {patch_name}")

        req3 = urllib.request.Request(patch_url, headers={"User-Agent": "PDFHeaderTool"})
        with urllib.request.urlopen(req3, timeout=timings["update_download_timeout"], context=ssl_ctx) as r:
            patch_data = r.read()
        print(f"[{_ts()}] UPDATE_CHECK patch telecharge: {len(patch_data)} octets")

        # 6. Vérifier SHA256
        import hashlib
        actual_sha256 = hashlib.sha256(patch_data).hexdigest()
        if patch_sha256 and actual_sha256 != patch_sha256:
            print(f"[{_ts()}] UPDATE_CHECK ERREUR sha256 — patch rejete (attendu={patch_sha256[:12]}... recu={actual_sha256[:12]}...)")
            log_update.debug(f"UPDATE_HASH_MISMATCH expected={patch_sha256} got={actual_sha256}")
            return

        # 7. Extraire dans staging
        import zipfile, io
        staging = install_dir / "_update_pending"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        with zipfile.ZipFile(io.BytesIO(patch_data)) as zf:
            zf.extractall(staging)

        # 8. Écrire les métadonnées de contrôle
        delete_list = meta.get("delete", [])
        if delete_list:
            (staging / "_delete.json").write_text(json.dumps(delete_list))
        (staging / "_target_version.txt").write_text(remote_version)

        print(f"[{_ts()}] UPDATE_CHECK patch mis en attente: {running_version} -> {remote_version} (sera applique au prochain lancement)")
        log_update.debug(f"UPDATE_STAGED {running_version} -> {remote_version}")
        log_update.info(f"UPDATE_STAGED local={running_version} remote={remote_version}")

        if _staged_callback:
            _staged_callback(remote_version)

    except Exception as e:
        print(f"[{_ts()}] UPDATE_CHECK ERREUR: {e}")
        log_update.error(f"UPDATE_CHECK_ERROR error={e}")


def check_update(
    running_version: str,
    channel: str,
    github_repo: str,
    install_dir: Path,
    timings: dict,
) -> None:
    """Lance _check_update_thread() comme thread daemon non bloquant.
    Appelée au démarrage de l'app, après _bootstrap() et _setup_logger().
    """
    t = threading.Thread(
        target=_check_update_thread,
        args=(running_version, channel, github_repo, install_dir, timings),
        daemon=True,
    )
    t.start()
