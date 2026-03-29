"""IPython startup script: load MinIO env vars from shared JSON file.

This script is automatically installed by jupyterlab-minio into
~/.ipython/profile_default/startup/ and runs each time an IPython
kernel starts.  It reads ~/.jupyter/minio_env.json and sets (or unsets)
MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY in os.environ.
"""

import json
import os
from pathlib import Path as _Path

_ENV_FILE = _Path.home() / ".jupyter" / "minio_env.json"
_KEYS = ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")

if _ENV_FILE.exists():
    try:
        _data = json.loads(_ENV_FILE.read_text(encoding="utf-8"))
        for _k in _KEYS:
            _v = _data.get(_k, "")
            if _v:
                os.environ[_k] = _v
            elif _k in os.environ:
                del os.environ[_k]
    except Exception:
        pass
