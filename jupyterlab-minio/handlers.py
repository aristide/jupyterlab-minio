import base64
import json
import os
import logging
import colorlog
from pathlib import Path

import boto3
import s3fs
import tornado
from botocore.exceptions import NoCredentialsError
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
from .utils import EnvironmentManager, MinIOConfigHelper


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

########################### Custom helpers

minio_config_helper = MinIOConfigHelper()
# bash_helper = BashrcEnvManager()
env_manager = EnvironmentManager()

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
        
        authenticated = False
        if has_minio_role_access():
            authenticated = True

        if not authenticated:

            try:
                config = self.config
                if config.url and config.accessKey and config.secretKey:
                    test_minio_credentials(
                        config.url,
                        config.accessKey,
                        config.secretKey,
                    )
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

        os.environ["MYVAR"] = self.config.url
        
        if authenticated:
            # update environment variable with the new credentials
            env_manager.update_env_var("MINIO_ENDPOINT", self.config.url)
            env_manager.update_env_var("MINIO_ACCESS_KEY", self.config.accessKey)
            env_manager.update_env_var("MINIO_SECRET_KEY", self.config.secretKey)
        else:
            # delete minio environment variable
            env_manager.remove_env_var("MINIO_ENDPOINT")
            env_manager.remove_env_var("MINIO_ACCESS_KEY")
            env_manager.remove_env_var("MINIO_SECRET_KEY")
        
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
            
            # update minio config gile
            minio_config_helper.update_alias(url, accessKey, secretKey)
            # update environment variable with the new credentials
            env_manager.update_env_var("MINIO_ENDPOINT", self.config.url)
            env_manager.update_env_var("MINIO_ACCESS_KEY", self.config.accessKey)
            env_manager.update_env_var("MINIO_SECRET_KEY", self.config.secretKey)
            
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
            # delete minio environment variable
            env_manager.remove_env_var("MINIO_ENDPOINT")
            env_manager.remove_env_var("MINIO_ACCESS_KEY")
            env_manager.remove_env_var("MINIO_SECRET_KEY")
            
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
        path = path[1:]

        try:
            if not self.s3fs:
                self.s3fs = create_s3fs(self.config)

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

                # copying issue is because of dir/file mixup?
                if "/" not in source:
                    path = path + "/.keep"

                #  logger.info("copying {} -> {}".format(source, path))
                self.s3fs.cp(source, path, recursive=True)
                # why read again?
                with self.s3fs.open(path, "rb") as f:
                    result = {
                        "path": path,
                        "type": "file",
                        "content": base64.encodebytes(f.read()).decode("ascii"),
                    }
            elif "X-Custom-S3-Move-Src" in self.request.headers:
                source = self.request.headers["X-Custom-S3-Move-Src"]

                #  logger.info("moving {} -> {}".format(source, path))
                self.s3fs.move(source, path, recursive=True)
                # why read again?
                with self.s3fs.open(path, "rb") as f:
                    result = {
                        "path": path,
                        "type": "file",
                        "content": base64.encodebytes(f.read()).decode("ascii"),
                    }
            elif "X-Custom-S3-Is-Dir" in self.request.headers:
                path = path.lower()
                if not path[-1] == "/":
                    path = path + "/"

                #  logger.info("creating new dir: {}".format(path))
                self.s3fs.mkdir(path)
                self.s3fs.touch(path + ".keep")
            elif self.request.body:
                request = json.loads(self.request.body)
                with self.s3fs.open(path, "w") as f:
                    f.write(request["content"])
                    # todo: optimize
                    result = {
                        "path": path,
                        "type": "file",
                        "content": request["content"],
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
        Takes a path and returns lists of files/objects
        and directories/prefixes based on the path.
        """
        path = path[1:]
        #  logger.info("DELETE: {}".format(path))

        result = {}

        try:
            if not self.s3fs:
                self.s3fs = create_s3fs(self.config)
            if not self.s3_resource:
                self.s3_resource = create_s3_resource(self.config)

            if self.s3fs.exists(path + "/.keep"):
                self.s3fs.rm(path + "/.keep")

            objects_matching_prefix = self.s3fs.listdir(path + "/")
            is_directory = (len(objects_matching_prefix) > 1) or (
                (len(objects_matching_prefix) == 1)
                and objects_matching_prefix[0]["Key"] != path
            )

            if is_directory:
                if (len(objects_matching_prefix) > 1) or (
                    (len(objects_matching_prefix) == 1)
                    and objects_matching_prefix[0]["Key"] != path + "/"
                ):
                    raise DirectoryNotEmptyException()
                else:
                    # for some reason s3fs.rm doesn't work reliably
                    if path.count("/") > 1:
                        bucket_name, prefix = path.split("/", 1)
                        bucket = self.s3_resource.Bucket(bucket_name)
                        bucket.objects.filter(Prefix=prefix).delete()
                    else:
                        self.s3fs.rm(path)
            else:
                self.s3fs.rm(path)

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


########################### Setup lab handler
def setup_handlers(web_app):
    host_pattern = ".*"

    base_url = web_app.settings["base_url"]
    handlers = [
        (url_path_join(base_url, "jupyterlab-minio", "auth(.*)"), AuthRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "files(.*)"), S3PathRouteHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
