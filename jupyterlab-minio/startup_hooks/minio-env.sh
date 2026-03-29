#!/bin/sh
# jupyterlab-minio: load MinIO env vars from shared JSON file.
# This script is sourced by ~/.bashrc (installed by jupyterlab-minio).

_MINIO_ENV_FILE="$HOME/.jupyter/minio_env.json"

if [ -f "$_MINIO_ENV_FILE" ]; then
    eval "$(python3 -c "
import json, sys
try:
    data = json.load(open('$_MINIO_ENV_FILE'))
    for k in ('MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY'):
        v = data.get(k, '')
        if v:
            print('export %s=\"%s\"' % (k, v))
        else:
            print('unset %s 2>/dev/null' % k)
except Exception:
    pass
" 2>/dev/null)"
fi

unset _MINIO_ENV_FILE
