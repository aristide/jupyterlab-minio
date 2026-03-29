"""
Manages MinIO environment variables via a shared JSON file (~/.jupyter/minio_env.json).

On server startup, loads persisted values into os.environ so that JupyterLabS3
traitlets pick them up. On credential set/reset, writes the file atomically
and updates os.environ so new kernels/terminals inherit the values.

Also installs IPython and shell startup hooks that read the JSON file,
ensuring kernels and terminals started independently also get the vars.
"""

import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_FILE = Path.home() / ".jupyter" / "minio_env.json"

MINIO_KEYS = ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")

# Marker used in ~/.bashrc to identify our injected source line
_BASHRC_MARKER = "# jupyterlab-minio-env"


class EnvFileManager:
    """Read/write MinIO credentials to a shared JSON file."""

    def __init__(self, path=None):
        self.path = Path(path) if path else ENV_FILE

    # ------------------------------------------------------------------ #
    #  File I/O (atomic writes)
    # ------------------------------------------------------------------ #

    def write(self, endpoint, access_key, secret_key):
        """Persist credentials to the JSON file and update os.environ."""
        data = {
            "MINIO_ENDPOINT": endpoint,
            "MINIO_ACCESS_KEY": access_key,
            "MINIO_SECRET_KEY": secret_key,
        }
        self._atomic_write(data)
        # Also update the running server's environ
        for key, value in data.items():
            os.environ[key] = value

    def read(self):
        """Return the contents of the JSON file, or {} if missing/malformed."""
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("minio env_manager: failed to read %s", self.path)
            return {}

    def clear(self):
        """Write an empty dict (so startup hooks unset the vars) and clean os.environ."""
        self._atomic_write({})
        for key in MINIO_KEYS:
            os.environ.pop(key, None)

    def load_into_environ(self):
        """Load the JSON file into os.environ.  Called once at server startup."""
        data = self.read()
        if not data:
            return
        for key in MINIO_KEYS:
            value = data.get(key, "")
            if value:
                os.environ[key] = value
        logger.info("minio env_manager: loaded env vars from %s", self.path)

    # ------------------------------------------------------------------ #
    #  Generic kernel fallback: patch all running kernel managers
    # ------------------------------------------------------------------ #

    def patch_running_kernels(self, server_app):
        """Patch env on all running kernel managers via update_env().

        This is language-agnostic: it ensures that when any kernel is
        restarted (by us or later by the user), the new process inherits
        the correct MinIO env vars regardless of kernel language.
        """
        try:
            multi_km = server_app.kernel_manager
            env_patch = {k: os.environ.get(k, "") for k in MINIO_KEYS}
            for kid in multi_km.list_kernel_ids():
                try:
                    km = multi_km.get_kernel(kid)
                    km.update_env(env=env_patch)
                except Exception as e:
                    logger.warning(
                        "minio env_manager: failed to patch kernel %s: %s", kid, e
                    )
            logger.info(
                "minio env_manager: patched %d running kernel(s)",
                len(multi_km.list_kernel_ids()),
            )
        except Exception as e:
            logger.warning("minio env_manager: patch_running_kernels failed: %s", e)

    # ------------------------------------------------------------------ #
    #  Startup hook installation (idempotent)
    # ------------------------------------------------------------------ #

    def install_startup_hooks(self):
        """Copy IPython, R, Julia, and shell startup scripts to user directories."""
        self._install_ipython_hook()
        self._install_r_hook()
        self._install_julia_hook()
        self._install_shell_hook()

    # ------------------------------------------------------------------ #
    #  Private helpers
    # ------------------------------------------------------------------ #

    def _atomic_write(self, data):
        """Write JSON atomically: write to .tmp then os.replace."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(self.path))

    def _install_ipython_hook(self):
        """Copy 00-minio-env.py into ~/.ipython/profile_default/startup/."""
        src = Path(__file__).parent / "startup_hooks" / "00-minio-env.py"
        if not src.exists():
            logger.warning("minio env_manager: IPython hook source not found: %s", src)
            return

        dest_dir = Path.home() / ".ipython" / "profile_default" / "startup"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "00-minio-env.py"

        # Only write if content differs (idempotent)
        src_content = src.read_text(encoding="utf-8")
        if dest.exists() and dest.read_text(encoding="utf-8") == src_content:
            return
        dest.write_text(src_content, encoding="utf-8")
        logger.info("minio env_manager: installed IPython startup hook → %s", dest)

    def _install_r_hook(self):
        """Append MinIO env loading to ~/.Rprofile."""
        src = Path(__file__).parent / "startup_hooks" / ".Rprofile"
        if not src.exists():
            logger.warning("minio env_manager: R hook source not found: %s", src)
            return

        dest = Path.home() / ".Rprofile"
        src_content = src.read_text(encoding="utf-8")
        marker = "# jupyterlab-minio:"

        if dest.exists():
            existing = dest.read_text(encoding="utf-8")
            if marker in existing:
                return  # already installed
            # Append to existing .Rprofile
            with open(dest, "a", encoding="utf-8") as f:
                f.write("\n" + src_content)
        else:
            dest.write_text(src_content, encoding="utf-8")
        logger.info("minio env_manager: installed R startup hook → %s", dest)

    def _install_julia_hook(self):
        """Copy startup.jl to ~/.julia/config/startup.jl."""
        src = Path(__file__).parent / "startup_hooks" / "startup.jl"
        if not src.exists():
            logger.warning("minio env_manager: Julia hook source not found: %s", src)
            return

        dest_dir = Path.home() / ".julia" / "config"
        dest = dest_dir / "startup.jl"
        src_content = src.read_text(encoding="utf-8")
        marker = "# jupyterlab-minio:"

        if dest.exists():
            existing = dest.read_text(encoding="utf-8")
            if marker in existing:
                return  # already installed
            # Append to existing startup.jl
            with open(dest, "a", encoding="utf-8") as f:
                f.write("\n" + src_content)
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(src_content, encoding="utf-8")
        logger.info("minio env_manager: installed Julia startup hook → %s", dest)

    def _install_shell_hook(self):
        """Copy minio-env.sh to ~/.jupyter/ and add source line to ~/.bashrc."""
        src = Path(__file__).parent / "startup_hooks" / "minio-env.sh"
        if not src.exists():
            logger.warning("minio env_manager: shell hook source not found: %s", src)
            return

        # Copy script to ~/.jupyter/minio-env.sh
        dest = Path.home() / ".jupyter" / "minio-env.sh"
        dest.parent.mkdir(parents=True, exist_ok=True)
        src_content = src.read_text(encoding="utf-8")
        if not dest.exists() or dest.read_text(encoding="utf-8") != src_content:
            dest.write_text(src_content, encoding="utf-8")
            logger.info("minio env_manager: installed shell hook → %s", dest)

        # Append source line to ~/.bashrc if not already present
        bashrc = Path.home() / ".bashrc"
        source_line = (
            '[ -f "$HOME/.jupyter/minio-env.sh" ] && '
            '. "$HOME/.jupyter/minio-env.sh" ' + _BASHRC_MARKER
        )
        if bashrc.exists():
            content = bashrc.read_text(encoding="utf-8")
            if _BASHRC_MARKER in content:
                return
        else:
            content = ""
        with open(bashrc, "a", encoding="utf-8") as f:
            f.write("\n" + source_line + "\n")
        logger.info("minio env_manager: added source line to %s", bashrc)
