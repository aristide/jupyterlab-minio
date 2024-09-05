from ._version import __version__

import json
from os import environ
from traitlets import Unicode
from traitlets.config import Configurable

from .handlers import setup_handlers


def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "jupyterlab-minio"
    }]


def _jupyter_server_extension_points():
    return [{
        "module": "jupyterlab-minio"
    }]


class JupyterLabS3(Configurable):
    """
    Config options for jupyterlab_minio
    """

    url = Unicode(
        default_value=environ.get("MINIO_ENDPOINT", ""),
        config=True,
        help="The url for the S3 api",
    )
    accessKey = Unicode(
        default_value=environ.get("MINIO_ACCESS_KEY", ""),
        config=True,
        help="The client ID for the S3 api",
    )
    secretKey = Unicode(
        default_value=environ.get("MINIO_SECRET_KEY", ""),
        config=True,
        help="The client secret for the S3 api",
    )


def _load_jupyter_server_extension(server_app):
    """Registers the API handler to receive HTTP requests from the frontend extension.

    Parameters
    ----------
    server_app: jupyterlab.labapp.LabApp
        JupyterLab application instance
    """
    config = JupyterLabS3(config=server_app.config)
    server_app.web_app.settings["config"] = config
    setup_handlers(server_app.web_app)
    name = "jupyterlab-minio"
    server_app.log.info(f"Registered {name} server extension")


# For backward compatibility with notebook server - useful for Binder/JupyterHub
load_jupyter_server_extension = _load_jupyter_server_extension
_jupyter_server_extension_paths = _jupyter_server_extension_points
