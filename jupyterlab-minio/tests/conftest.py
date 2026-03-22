# This conftest.py prevents pytest from trying to import the parent
# jupyterlab-minio/__init__.py (which fails due to relative imports
# when the package isn't installed in development mode).
