from os import environ
from traitlets import Unicode
from traitlets.config import Configurable

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
