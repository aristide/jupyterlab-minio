from ._version import __version__

from .handlers import setup_handlers
from .utils import JupyterLabS3
from .env_manager import EnvFileManager

def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "jupyterlab-minio"
    }]


def _jupyter_server_extension_points():
    return [{
        "module": "jupyterlab-minio"
    }]


def _load_jupyter_server_extension(server_app):
    """Registers the API handler to receive HTTP requests from the frontend extension.

    Parameters
    ----------
    server_app: jupyterlab.labapp.LabApp
        JupyterLab application instance
    """
    # Load persisted env vars from shared JSON file BEFORE creating the
    # config object so that JupyterLabS3 traitlets pick up the values.
    env_manager = EnvFileManager()
    env_manager.load_into_environ()
    env_manager.install_startup_hooks()

    minio_config = JupyterLabS3(config=server_app.config)
    server_app.web_app.settings["minio_config"] = minio_config
    server_app.web_app.settings["minio_env_manager"] = env_manager
    server_app.web_app.settings["jupyter_server_app"] = server_app
    setup_handlers(server_app.web_app)
    name = "jupyterlab-minio"
    server_app.log.info(f"Registered {name} server extension")

