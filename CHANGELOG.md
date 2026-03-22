# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 2.0.0

### Breaking Changes

- Requires JupyterLab >= 4.0.0 (drops JupyterLab 3.x support)
- Requires `jupyter_server` >= 2.0.1 (drops notebook server support)
- Requires Python >= 3.8

### Added

- **Bucket management**: Create and delete S3 buckets from the context menu
- **Cross-bucket operations**: Copy and move files/folders between S3 paths via a path picker dialog
- **S3 to local transfer**: Copy files between S3 and the local filesystem
- **Copy to S3**: Right-click files in the default file browser to copy them to S3
- **Upload button**: Upload files from your computer directly to S3 (toolbar button)
- **Filter button**: Filter files/folders by name in the current S3 directory (toolbar button)
- **Create Folder button**: Create new folders in the current S3 directory (toolbar button)
- **Delete from S3**: Context menu item for deleting files and folders (supports recursive deletion of non-empty folders)

### Changed

- Updated all `@jupyterlab/*` dependencies to v4.x
- Updated all `@lumino/*` dependencies to v2.x
- Replaced `jupyter_packaging` / `setuptools` build system with `hatchling` / `hatch-jupyter-builder`
- Replaced `iconClass` CSS-based sidebar icon with `LabIcon` for proper JupyterLab 4 icon rendering
- Replaced `@lumino/virtualdom` usage with standard DOM APIs in the authentication form
- Replaced Minio server-rack logo with new data lake icon (database with water waves)
- Icon now uses JupyterLab's `jp-icon3` CSS class with `var(--jp-inverse-layout-color3)` for automatic theme adaptation (light, dark, dark high contrast)
- Updated Lumino CSS class prefixes from `p-` to `lm-`
- Updated TypeScript target from ES2018 to ES2021
- Updated TypeScript to v5.5, ESLint to v8, Prettier to v3, Jest to v29, Stylelint to v16
- Updated CI workflows to use GitHub Actions v4 and JupyterLab 4
- Updated `@jupyterlab/galata` to v5.x for integration tests

### Fixed

- Delete operations now use boto3 `delete_object` (singular) instead of `s3fs.rm()` to avoid `MissingContentMD5` errors with MinIO's `DeleteObjects` batch API
- Rename/move/copy operations now use boto3 `copy_object` + `delete_object` instead of `s3fs.move()`/`s3fs.cp()` to avoid the same Content-MD5 issue
- "Copy to S3" context menu no longer appears in the S3 browser (scoped to default file browser only)
- "Copy to S3" now correctly reads the selected file path from the default file browser
- `S3Drive.delete()` now surfaces all backend errors, not just `DIR_NOT_EMPTY`
- Filter input dynamically resets the file list when clearing search text

### Removed

- Removed `setup.py` (replaced by `pyproject.toml`)
- Removed `jupyter-config/nb-config/` backward compatibility config for notebook server
- Removed backward compatibility aliases (`load_jupyter_server_extension`, `_jupyter_server_extension_paths`)
- Removed `jupyterlab-pygments` and `notebook` from dependencies
- Removed `stylelint-config-prettier` (unnecessary with stylelint 16 + prettier 3)
- Removed Lumino 1.x resolution overrides

<!-- <END NEW CHANGELOG ENTRY> -->

## 1.1.1

- Prettify codebase
- Update devcontainer configuration
- Lint fixes
- Update documentation
- Fix environment variable settings

## 1.1.0

- Initial prebuilt extension release for JupyterLab 3.x
