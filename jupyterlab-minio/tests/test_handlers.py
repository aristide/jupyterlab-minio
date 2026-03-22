import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Import validate_local_path from the parent package.
# The package directory uses hyphens, so we set up the package context
# before importing handlers.py (which uses relative imports).
import importlib
import importlib.util
import sys
import types

_pkg_dir = os.path.dirname(os.path.dirname(__file__))

# Create a synthetic package so relative imports work
_pkg_name = "jupyterlab_minio_pkg"
_pkg = types.ModuleType(_pkg_name)
_pkg.__path__ = [_pkg_dir]
_pkg.__package__ = _pkg_name
sys.modules[_pkg_name] = _pkg

# Load utils first (handlers imports from .utils)
_utils_spec = importlib.util.spec_from_file_location(
    f"{_pkg_name}.utils",
    os.path.join(_pkg_dir, "utils.py"),
    submodule_search_locations=[],
)
_utils_mod = importlib.util.module_from_spec(_utils_spec)
_utils_mod.__package__ = _pkg_name
sys.modules[f"{_pkg_name}.utils"] = _utils_mod
_utils_spec.loader.exec_module(_utils_mod)

# Now load handlers
_handlers_spec = importlib.util.spec_from_file_location(
    f"{_pkg_name}.handlers",
    os.path.join(_pkg_dir, "handlers.py"),
    submodule_search_locations=[],
)
_handlers_mod = importlib.util.module_from_spec(_handlers_spec)
_handlers_mod.__package__ = _pkg_name
sys.modules[f"{_pkg_name}.handlers"] = _handlers_mod
_handlers_spec.loader.exec_module(_handlers_mod)

validate_local_path = _handlers_mod.validate_local_path


class TestValidateLocalPath:
    """Tests for the validate_local_path utility function."""

    def test_valid_path(self):
        with tempfile.TemporaryDirectory() as root:
            result = validate_local_path("subdir/file.txt", root)
            assert result == os.path.join(root, "subdir", "file.txt")

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with pytest.raises(ValueError, match="Path traversal detected"):
                validate_local_path("../../etc/passwd", root)

    def test_path_traversal_with_nested_dotdot(self):
        with tempfile.TemporaryDirectory() as root:
            with pytest.raises(ValueError, match="Path traversal detected"):
                validate_local_path("subdir/../../..", root)

    def test_simple_filename(self):
        with tempfile.TemporaryDirectory() as root:
            result = validate_local_path("file.txt", root)
            assert result == os.path.join(root, "file.txt")

    def test_nested_path(self):
        with tempfile.TemporaryDirectory() as root:
            result = validate_local_path("a/b/c/file.txt", root)
            assert result == os.path.join(root, "a", "b", "c", "file.txt")

    def test_root_path_itself(self):
        with tempfile.TemporaryDirectory() as root:
            # Empty string resolves to root itself, which should be allowed
            result = validate_local_path("", root)
            assert result == root


class TestBucketNameValidation:
    """Tests for bucket name validation regex."""

    def test_valid_names(self):
        import re
        pattern = r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$'
        valid_names = [
            "my-bucket",
            "test-bucket-123",
            "abc",
            "a" * 63,
            "123-test",
        ]
        for name in valid_names:
            assert re.match(pattern, name), f"{name} should be valid"

    def test_invalid_names(self):
        import re
        pattern = r'^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$'
        invalid_names = [
            "ab",               # too short
            "a" * 64,           # too long
            "My-Bucket",        # uppercase
            "-bucket",          # starts with hyphen
            "bucket-",          # ends with hyphen
            "bucket.name",      # dot
            "bucket name",      # space
            "bucket_name",      # underscore
        ]
        for name in invalid_names:
            assert not re.match(pattern, name), f"{name} should be invalid"


async def test_get_example(jp_fetch):
    # When
    response = await jp_fetch("jupyterlab-minio", "get_example")

    # Then
    assert response.code == 200
    payload = json.loads(response.body)
    assert payload == {
        "data": "This is /jupyterlab-minio/get_example endpoint!"
    }
