import base64
import json
import os
import re
import logging
import colorlog
from pathlib import Path

import boto3
import s3fs
import tornado
from botocore.exceptions import NoCredentialsError
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
from .utils import MinIOConfigHelper


########################### Custom logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class CustomFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        # Add the class name to the record dynamically
        record.classname = record.args.get('classname', record.name) if isinstance(record.args, dict) else 'NoClass'
        return super().format(record)
    
handler = colorlog.StreamHandler()
handler.setFormatter(CustomFormatter(
    '%(log_color)s[%(levelname).1s %(asctime)s %(classname)s %(funcName)s] %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red'
    }
))

logger.addHandler(handler)

import time as _time

########################### Custom helpers

minio_config_helper = MinIOConfigHelper()

########################### Custom exceptions
class DirectoryNotEmptyException(Exception):
    """Raise for attempted deletions of non-empty directories"""
    pass

class S3ResourceNotFoundException(Exception):
    pass


########################### Custom methods

def create_s3fs(config):

    if config.url and config.accessKey and config.secretKey:

        return s3fs.S3FileSystem(
            key=config.accessKey,
            secret=config.secretKey,
            client_kwargs={"endpoint_url": config.url},
        )
    else:
        return s3fs.S3FileSystem()


def create_s3_resource(config):

    if config.url and config.accessKey and config.secretKey:

        return boto3.resource(
            "s3",
            aws_access_key_id=config.accessKey,
            aws_secret_access_key=config.secretKey,
            endpoint_url=config.url,
        )

    else:
        return boto3.resource("s3")


def create_s3_client(config):

    if config.url and config.accessKey and config.secretKey:

        return boto3.client(
            "s3",
            aws_access_key_id=config.accessKey,
            aws_secret_access_key=config.secretKey,
            endpoint_url=config.url,
        )

    else:
        return boto3.client("s3")


def _s3_copy_or_move(s3fs_instance, s3_client, source, dest, delete_source=False):
    """
    Copy (or move) S3 objects using singular copy_object/delete_object calls
    to avoid the Content-MD5 requirement of the batch DeleteObjects API.
    """
    src_bucket, src_key = source.split("/", 1)
    dst_bucket, dst_key = dest.split("/", 1)

    if s3fs_instance.isdir(source):
        objects = s3fs_instance.ls(source, detail=False)
        for obj_path in objects:
            obj_bucket, obj_key = obj_path.split("/", 1)
            relative = obj_key[len(src_key):]
            new_key = dst_key + relative
            s3_client.copy_object(
                Bucket=dst_bucket,
                Key=new_key,
                CopySource={"Bucket": obj_bucket, "Key": obj_key},
            )
            if delete_source:
                s3_client.delete_object(Bucket=obj_bucket, Key=obj_key)
        if delete_source:
            for suffix in ["/", ""]:
                try:
                    s3_client.delete_object(Bucket=src_bucket, Key=src_key + suffix)
                except Exception:
                    pass
    else:
        s3_client.copy_object(
            Bucket=dst_bucket,
            Key=dst_key,
            CopySource={"Bucket": src_bucket, "Key": src_key},
        )
        if delete_source:
            s3_client.delete_object(Bucket=src_bucket, Key=src_key)


def get_minio_credentials():
    """
    Load Minio credential from configuration file
    """
    if minio_config_helper.exist:
        return minio_config_helper.config
    return None


def _test_minio_role_access(config):
    """
    Checks if we have access to minio bucket through role-based access
    """
    test = boto3.resource("s3",
        aws_access_key_id=config.accessKey,
        aws_secret_access_key=config.secretKey,
        endpoint_url=config.url,
    )
    all_buckets = test.buckets.all()
    result = [
        {"name": bucket.name + "/", "path": bucket.name + "/", "type": "directory"}
        for bucket in all_buckets
    ]
    return result


def has_minio_role_access():
    """
    Returns true if the user has access to an minio bucket
    """

    # avoid making requests to Minio if the user's ~/.mc/config.json file has credentials for a different provider,
    # e.g. https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-aws-cli#aws-cli-config
    
    config = get_minio_credentials()
    if not config:
        return False
    
    try:
        _test_minio_role_access(config)
        return True
    except NoCredentialsError:
        return False
    except Exception as e:
        logger.error(e)
        return False


def test_minio_credentials(url, accessKey, secretKey):
    """
    Checks if we're able to list buckets with these credentials.
    If not, it throws an exception.
    """
    test = boto3.resource(
        "s3",
        aws_access_key_id=accessKey,
        aws_secret_access_key=secretKey,
        endpoint_url=url,
    )
    all_buckets = test.buckets.all()
    logger.debug(
        [
            {"name": bucket.name + "/", "path": bucket.name + "/", "type": "directory"}
            for bucket in all_buckets
        ]
    )


def convertS3FStoJupyterFormat(result):
    return {
        "name": result["Key"].rsplit("/", 1)[-1],
        "path": result["Key"],
        "type": result["type"],
    }


########################### Custom class
class CustomAPIHandler(APIHandler):
    """
    Read Minio credential from config
    """
    
    @property
    def config(self):
        credentials = get_minio_credentials()
        if credentials:
            return credentials
        return self.settings["minio_config"]
         

class AuthRouteHandler(CustomAPIHandler):  # pylint: disable=abstract-method
    """
    handle api requests to change auth info
    """

    @tornado.web.authenticated
    def get(self, path=""):
        """
        Checks if the user is already authenticated
        against an s3 instance.
        """
        t_start = _time.time()
        logger.info("[minio-perf] GET /auth START")

        authenticated = False
        t0 = _time.time()
        logger.info("[minio-perf] has_minio_role_access START")
        if has_minio_role_access():
            authenticated = True
        logger.info("[minio-perf] has_minio_role_access END (%.0fms) result=%s",
                     (_time.time() - t0) * 1000, authenticated)

        if not authenticated:

            try:
                config = self.config
                if config.url and config.accessKey and config.secretKey:
                    t1 = _time.time()
                    logger.info("[minio-perf] test_minio_credentials START")
                    test_minio_credentials(
                        config.url,
                        config.accessKey,
                        config.secretKey,
                    )
                    logger.info("[minio-perf] test_minio_credentials END (%.0fms)",
                                 (_time.time() - t1) * 1000)
                    logger.debug("...successfully authenticated")

                    # If no exceptions were encountered during testS3Credentials,
                    # then assume we're authenticated
                    authenticated = True

            except Exception as err:
                # If an exception was encountered,
                # assume that we're not yet authenticated
                # or invalid credentials were provided
                logger.debug("...failed to authenticate")
                logger.debug(err)

        logger.info("[minio-perf] GET /auth END (%.0fms) authenticated=%s",
                     (_time.time() - t_start) * 1000, authenticated)

        self.finish(json.dumps({"authenticated": authenticated}))

    @tornado.web.authenticated
    def post(self, path=""):
        """
        Sets s3 credentials.
        """

        try:
            req = json.loads(self.request.body)
            url = req["url"]
            accessKey = req["accessKey"]
            secretKey = req["secretKey"]

            test_minio_credentials(url, accessKey, secretKey)

            self.config.url = url
            self.config.accessKey = accessKey
            self.config.secretKey = secretKey
            
            # update minio config file
            minio_config_helper.update_alias(url, accessKey, secretKey)
            # persist to shared env file for kernel/terminal startup hooks
            env_mgr = self.settings.get("minio_env_manager")
            if env_mgr:
                env_mgr.write(url, accessKey, secretKey)
                server_app = self.settings.get("jupyter_server_app")
                if server_app:
                    env_mgr.patch_running_kernels(server_app)

            self.finish(json.dumps({"success": True}))
        except Exception as err:
            logger.error("unable to authenticate using credentials {}".format(str(self.request.body)))
            self.finish(json.dumps({"success": False, "message": "{}".format(str(err))}))

    @tornado.web.authenticated
    def delete(self, path=""):
        """
        Remove the config file
        """
        try:

            # reset the config fields
            self.config.url = ""
            self.config.accessKey = ""
            self.config.secretKey = ""

            minio_config_helper.remove_config_path()
            # clear shared env file so startup hooks unset the vars
            env_mgr = self.settings.get("minio_env_manager")
            if env_mgr:
                env_mgr.clear()
                server_app = self.settings.get("jupyter_server_app")
                if server_app:
                    env_mgr.patch_running_kernels(server_app)

            self.finish(json.dumps({"success": True}))
        except Exception as err:
            logger.error("unable reconfigure using credentials {}".format(str(err)))
            self.finish(json.dumps({"success": False, "message": "{} ".format(str(err))}))


class S3PathRouteHandler(CustomAPIHandler):
    """
    Handles requests for getting S3 objects
    """

    s3fs = None
    s3_resource = None

    @tornado.web.authenticated
    def get(self, path=""):
        """
        Takes a path and returns lists of files/objects
        and directories/prefixes based on the path.
        """
        t_start = _time.time()
        path = path[1:]
        logger.info("[minio-perf] GET /files/%s START", path)

        try:
            if not self.s3fs:
                t0 = _time.time()
                logger.info("[minio-perf] create_s3fs START")
                self.s3fs = create_s3fs(self.config)
                logger.info("[minio-perf] create_s3fs END (%.0fms)",
                             (_time.time() - t0) * 1000)

            self.s3fs.invalidate_cache()

            if (path and not path.endswith("/")) and (
                "X-Custom-S3-Is-Dir" not in self.request.headers
            ):  # TODO: replace with function
                with self.s3fs.open(path, "rb") as f:
                    result = {
                        "path": path,
                        "type": "file",
                        "content": base64.encodebytes(f.read()).decode("ascii"),
                    }
            else:
                raw_result = list(
                    map(convertS3FStoJupyterFormat, self.s3fs.listdir(path))
                )
                result = list(filter(lambda x: x["name"] != "", raw_result))

        except S3ResourceNotFoundException as e:
            result = {
                "error": 404,
                "message": "The requested resource could not be found.",
            }
        except Exception as e:
            logger.error("Exception encountered while reading Minio resources {}: {}".format(path, e))
            result = {"error": 500, "message": str(e)}

        logger.info("[minio-perf] GET /files/%s END (%.0fms)",
                     path, (_time.time() - t_start) * 1000)
        self.finish(json.dumps(result))

    @tornado.web.authenticated
    def put(self, path=""):
        """
        Takes a path and returns lists of files/objects
        and directories/prefixes based on the path.
        """
        path = path[1:]

        result = {}

        try:
            if not self.s3fs:
                self.s3fs = create_s3fs(self.config)

            if "X-Custom-S3-Copy-Src" in self.request.headers:
                source = self.request.headers["X-Custom-S3-Copy-Src"]
                s3_client = create_s3_client(self.config)
                _s3_copy_or_move(self.s3fs, s3_client, source, path, delete_source=False)
                result = {"path": path, "type": "file"}

            elif "X-Custom-S3-Move-Src" in self.request.headers:
                source = self.request.headers["X-Custom-S3-Move-Src"]
                s3_client = create_s3_client(self.config)
                _s3_copy_or_move(self.s3fs, s3_client, source, path, delete_source=True)
                result = {"path": path, "type": "file"}
            elif "X-Custom-S3-Is-Dir" in self.request.headers:
                path = path.lower()
                if not path[-1] == "/":
                    path = path + "/"

                #  logger.info("creating new dir: {}".format(path))
                self.s3fs.mkdir(path)
                self.s3fs.touch(path + ".keep")
            elif self.request.body:
                request = json.loads(self.request.body)
                content = request["content"]
                if request.get("format") == "base64":
                    content = base64.b64decode(content)
                    with self.s3fs.open(path, "wb") as f:
                        f.write(content)
                    result = {
                        "path": path,
                        "type": "file",
                    }
                else:
                    with self.s3fs.open(path, "w") as f:
                        f.write(content)
                    result = {
                        "path": path,
                        "type": "file",
                        "content": content,
                    }

        except S3ResourceNotFoundException as e:
            #  logger.info(e)
            result = {
                "error": 404,
                "message": "The requested resource could not be found.",
            }
        except Exception as e:
            logger.error(e)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))

    @tornado.web.authenticated
    def delete(self, path=""):
        """
        Delete a file or empty directory from S3.
        Uses boto3 client delete_object (singular) to avoid
        Content-MD5 issues with the batch DeleteObjects API.
        """
        path = path[1:]

        result = {}

        try:
            if not self.s3fs:
                self.s3fs = create_s3fs(self.config)

            s3_client = create_s3_client(self.config)
            bucket_name, key = path.split("/", 1)

            # Remove .keep marker if present
            if self.s3fs.exists(path + "/.keep"):
                s3_client.delete_object(Bucket=bucket_name, Key=key + "/.keep")

            # Check what objects remain under this prefix
            try:
                objects_matching_prefix = self.s3fs.listdir(path + "/")
            except FileNotFoundError:
                objects_matching_prefix = []

            if len(objects_matching_prefix) == 0:
                # Nothing left — folder is already gone (was just .keep)
                try:
                    s3_client.delete_object(Bucket=bucket_name, Key=key + "/")
                except Exception:
                    pass
                try:
                    s3_client.delete_object(Bucket=bucket_name, Key=key)
                except Exception:
                    pass
            else:
                is_directory = (len(objects_matching_prefix) > 1) or (
                    (len(objects_matching_prefix) == 1)
                    and objects_matching_prefix[0]["Key"] != path
                )

                if is_directory:
                    # Delete all objects under this prefix recursively
                    all_objects = self.s3fs.ls(path, detail=False)
                    for obj_path in all_objects:
                        obj_bucket, obj_key = obj_path.split("/", 1)
                        s3_client.delete_object(Bucket=obj_bucket, Key=obj_key)
                    # Clean up directory markers
                    for suffix in ["/", ""]:
                        try:
                            s3_client.delete_object(Bucket=bucket_name, Key=key + suffix)
                        except Exception:
                            pass
                else:
                    s3_client.delete_object(Bucket=bucket_name, Key=key)

        except S3ResourceNotFoundException as e:
            logger.error(e)
            result = {
                "error": 404,
                "message": "The requested resource could not be found.",
            }
        except DirectoryNotEmptyException as e:
            #  logger.info("Attempted to delete non-empty directory")
            result = {"error": 400, "error": "DIR_NOT_EMPTY"}
        except Exception as e:
            logger.error("error while deleting")
            logger.error(e)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))


class BucketRouteHandler(CustomAPIHandler):
    """
    Handles requests for creating and deleting S3 buckets
    """

    @tornado.web.authenticated
    def post(self, path=""):
        """
        Create a new bucket.
        Body: {"bucket": "name"}
        """
        result = {}
        try:
            req = json.loads(self.request.body)
            name = req.get("bucket", "").strip()

            # Validate bucket name: lowercase, 3-63 chars, alphanumeric and hyphens only
            if not re.match(r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$', name):
                self.set_status(400)
                self.finish(json.dumps({
                    "error": 400,
                    "message": "Invalid bucket name. Must be 3-63 characters, lowercase alphanumeric and hyphens only, cannot start or end with a hyphen."
                }))
                return

            s3_resource = create_s3_resource(self.config)
            s3_resource.create_bucket(Bucket=name)
            result = {"success": True, "bucket": name}

        except Exception as e:
            logger.error("Error creating bucket: {}".format(e))
            self.set_status(500)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))

    @tornado.web.authenticated
    def delete(self, path=""):
        """
        Delete a bucket. The bucket name is extracted from the URL path.
        """
        name = path.strip("/")
        result = {}
        try:
            s3_resource = create_s3_resource(self.config)
            bucket = s3_resource.Bucket(name)
            bucket.delete()
            result = {"success": True}

        except Exception as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code == 'BucketNotEmpty' or 'not empty' in str(e).lower():
                self.set_status(400)
                result = {"error": 400, "message": "Bucket is not empty. Delete all objects first."}
            else:
                logger.error("Error deleting bucket: {}".format(e))
                self.set_status(500)
                result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))


class TransferRouteHandler(CustomAPIHandler):
    """
    Handles file transfers between S3 and local filesystem
    """

    s3fs = None

    @tornado.web.authenticated
    def post(self, path=""):
        """
        Transfer files between S3 and local filesystem.
        Body: {
            "source_type": "s3" | "local",
            "source_path": "...",
            "dest_type": "local" | "s3",
            "dest_path": "..."
        }
        """
        result = {}
        try:
            req = json.loads(self.request.body)
            source_type = req.get("source_type")
            source_path = req.get("source_path")
            dest_type = req.get("dest_type")
            dest_path = req.get("dest_path")

            if not all([source_type, source_path, dest_type, dest_path]):
                self.set_status(400)
                self.finish(json.dumps({"error": 400, "message": "Missing required fields."}))
                return

            if source_type == dest_type:
                self.set_status(400)
                self.finish(json.dumps({"error": 400, "message": "source_type and dest_type must be different."}))
                return

            root_dir = self.settings.get("server_root_dir", os.path.expanduser("~"))

            if not self.s3fs:
                self.s3fs = create_s3fs(self.config)

            if source_type == "s3" and dest_type == "local":
                local_abs = validate_local_path(dest_path, root_dir)
                # Check if source is a directory
                if self.s3fs.isdir(source_path):
                    _transfer_s3_to_local_recursive(self.s3fs, source_path, local_abs)
                else:
                    os.makedirs(os.path.dirname(local_abs), exist_ok=True)
                    with self.s3fs.open(source_path, "rb") as sf:
                        with open(local_abs, "wb") as lf:
                            lf.write(sf.read())
                result = {"success": True}

            elif source_type == "local" and dest_type == "s3":
                local_abs = validate_local_path(source_path, root_dir)
                if os.path.isdir(local_abs):
                    _transfer_local_to_s3_recursive(self.s3fs, local_abs, dest_path)
                else:
                    with open(local_abs, "rb") as lf:
                        with self.s3fs.open(dest_path, "wb") as sf:
                            sf.write(lf.read())
                result = {"success": True}
            else:
                self.set_status(400)
                self.finish(json.dumps({"error": 400, "message": "Invalid source_type/dest_type combination."}))
                return

        except ValueError as e:
            self.set_status(400)
            result = {"error": 400, "message": str(e)}
        except Exception as e:
            logger.error("Error during transfer: {}".format(e))
            self.set_status(500)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))


def validate_local_path(path, root_dir):
    """
    Resolve the path and verify it stays within the root directory.
    Prevents path traversal attacks with '..'.
    """
    root = os.path.realpath(root_dir)
    resolved = os.path.realpath(os.path.join(root, path))
    if not resolved.startswith(root + os.sep) and resolved != root:
        raise ValueError("Path traversal detected: path must be within the Jupyter root directory.")
    return resolved


def _transfer_s3_to_local_recursive(s3filesystem, s3_path, local_path):
    """Recursively transfer a directory from S3 to local filesystem."""
    os.makedirs(local_path, exist_ok=True)
    for dirpath, dirnames, filenames in s3filesystem.walk(s3_path):
        # Compute relative path from the source root
        rel = os.path.relpath(dirpath, s3_path) if dirpath != s3_path else ""
        local_dir = os.path.join(local_path, rel) if rel else local_path
        os.makedirs(local_dir, exist_ok=True)
        for fname in filenames:
            s3_file = dirpath + "/" + fname
            local_file = os.path.join(local_dir, fname)
            with s3filesystem.open(s3_file, "rb") as sf:
                with open(local_file, "wb") as lf:
                    lf.write(sf.read())


def _transfer_local_to_s3_recursive(s3filesystem, local_path, s3_path):
    """Recursively transfer a directory from local filesystem to S3."""
    for dirpath, dirnames, filenames in os.walk(local_path):
        rel = os.path.relpath(dirpath, local_path)
        s3_dir = s3_path + "/" + rel if rel != "." else s3_path
        for fname in filenames:
            local_file = os.path.join(dirpath, fname)
            s3_file = s3_dir + "/" + fname
            with open(local_file, "rb") as lf:
                with s3filesystem.open(s3_file, "wb") as sf:
                    sf.write(lf.read())


class ConfigRouteHandler(APIHandler):
    """
    Returns extension runtime configuration flags.
    """

    @tornado.web.authenticated
    def get(self):
        disable_reset = os.environ.get("MINIO_DISABLE_RESET", "").lower() == "true"
        self.finish(json.dumps({"disable_reset": disable_reset}))


########################### Setup lab handler
def setup_handlers(web_app):
    host_pattern = ".*"

    base_url = web_app.settings["base_url"]
    handlers = [
        (url_path_join(base_url, "jupyterlab-minio", "auth(.*)"), AuthRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "files(.*)"), S3PathRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "buckets(.*)"), BucketRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "transfer(.*)"), TransferRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "config"), ConfigRouteHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
