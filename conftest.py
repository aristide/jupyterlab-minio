import importlib

collect_ignore_glob = ["jupyterlab-minio/*.py"]

# Only load jupyter_server fixtures if pytest_jupyter is available
if importlib.util.find_spec("pytest_jupyter"):
    pytest_plugins = ("pytest_jupyter.jupyter_server",)

    import pytest

    @pytest.fixture
    def jp_server_config(jp_server_config):
        return {"ServerApp": {"jpserver_extensions": {"jupyterlab-minio": True}}}
