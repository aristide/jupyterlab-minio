import base64
import json
import logging
from pathlib import Path

import boto3
import s3fs
import tornado
from botocore.exceptions import NoCredentialsError
from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join


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


def save_s3_credentials(config):
    credentials_file = Path("{}/.mc/config.json".format(Path.home()))
    credientials = {
        "aliases": {
            "lakeStorage": {
                "url": "{}".format(config.url),
			    "accessKey": "{}".format(config.accessKey),
			    "secretKey": "{}".format(config.secretKey),
			    "api": "S3v4",
			    "path": "auto"
            }
        }
    }
    json.dump(credientials, open(credentials_file, 'wb'))


def _test_minio_role_access(config):
    """
    Checks if we have access to AWS S3 through role-based access
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


def has_minio_s3_role_access():
    """
    Returns true if the user has access to an aws S3 bucket
    """

    # avoid making requests to AWS if the user's ~/.mc/config.json file has credentials for a different provider,
    # e.g. https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-aws-cli#aws-cli-config
    credentials_file = Path("{}/.mc/config.json".format(Path.home()))
    if credentials_file.exists():
        with credentials_file.open() as credentials:
            configs = json.load(f)
            if not configs.get("aliases", {}).get("lakeStorage", {}).get("accessKey"):
                return False

    try:
        _test_minio_role_access(configs.get("aliases").get("lakeStorage"))
        return True
    except NoCredentialsError:
        return False
    except Exception as e:
        logging.error(e)
        return False


def test_s3_credentials(url, accessKey, secretKey):
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
    logging.debug(
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
class AuthRouteHandler(APIHandler):  # pylint: disable=abstract-method
    """
    handle api requests to change auth info
    """

    @property
    def config(self):
        return self.settings["config"]

    @tornado.web.authenticated
    def get(self, path=""):
        """
        Checks if the user is already authenticated
        against an s3 instance.
        """
        authenticated = False
        if has_minio_s3_role_access():
            authenticated = True

        if not authenticated:

            try:
                config = self.config
                if config.url and config.accessKey and config.secretKey:
                    test_s3_credentials(
                        config.url,
                        config.accessKey,
                        config.secretKey,
                    )
                    logging.debug("...successfully authenticated")

                    # If no exceptions were encountered during testS3Credentials,
                    # then assume we're authenticated
                    authenticated = True

            except Exception as err:
                # If an exception was encountered,
                # assume that we're not yet authenticated
                # or invalid credentials were provided
                logging.debug("...failed to authenticate")
                logging.debug(err)

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

            test_s3_credentials(url, accessKey, secretKey)
        
            self.config.url = url
            self.config.accessKey = accessKey
            self.config.secretKey = secretKey
            # save the config file
            save_s3_credentials(config)

            self.finish(json.dumps({"success": True}))
        except Exception as err:
            logging.info("unable to authenticate using credentials")
            self.finish(json.dumps({"success": False, "message": str(err)}))


class S3PathRouteHandler(APIHandler):
    """
    Handles requests for getting S3 objects
    """

    @property
    def config(self):
        return self.settings["config"]

    s3fs = None
    s3_resource = None

    @tornado.web.authenticated
    def get(self, path=""):
        """
        Takes a path and returns lists of files/objects
        and directories/prefixes based on the path.
        """
        path = path[1:]
        #  logging.info("GET {}".format(path))

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
            logging.error("Exception encountered during GET {}: {}".format(path, e))
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

                #  logging.info("copying {} -> {}".format(source, path))
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

                #  logging.info("moving {} -> {}".format(source, path))
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

                #  logging.info("creating new dir: {}".format(path))
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
            #  logging.info(e)
            result = {
                "error": 404,
                "message": "The requested resource could not be found.",
            }
        except Exception as e:
            logging.error(e)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))

    @tornado.web.authenticated
    def delete(self, path=""):
        """
        Takes a path and returns lists of files/objects
        and directories/prefixes based on the path.
        """
        path = path[1:]
        #  logging.info("DELETE: {}".format(path))

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
            logging.error(e)
            result = {
                "error": 404,
                "message": "The requested resource could not be found.",
            }
        except DirectoryNotEmptyException as e:
            #  logging.info("Attempted to delete non-empty directory")
            result = {"error": 400, "error": "DIR_NOT_EMPTY"}
        except Exception as e:
            logging.error("error while deleting")
            logging.error(e)
            result = {"error": 500, "message": str(e)}

        self.finish(json.dumps(result))


class HelloRouteHandler(APIHandler):
    # The following decorator should be present on all verb methods (head, get, post,
    # patch, put, delete, options) to ensure only authorized user can request the
    # Jupyter server
    @tornado.web.authenticated
    def get(self):
        self.finish(json.dumps({
            "data": "This is /jupyterlab-minio/hello endpoint!"
        }))


########################### Setup lab handler
def setup_handlers(web_app):
    host_pattern = ".*"

    base_url = web_app.settings["base_url"]
    handlers = [
        (url_path_join(base_url, "jupyterlab-minio", "get_example"), HelloRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "auth(.*)"), AuthRouteHandler),
        (url_path_join(base_url, "jupyterlab-minio", "files(.*)"), S3PathRouteHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
