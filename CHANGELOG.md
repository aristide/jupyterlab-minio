# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 2.0.0

### Breaking Changes

- Requires JupyterLab >= 4.0.0 (drops JupyterLab 3.x support)
- Requires `jupyter_server` >= 2.0.1 (drops notebook server support)
- Requires Python >= 3.8

### Changed

- Updated all `@jupyterlab/*` dependencies to v4.x
- Updated all `@lumino/*` dependencies to v2.x
- Replaced `jupyter_packaging` / `setuptools` build system with `hatchling` / `hatch-jupyter-builder`
- Replaced `iconClass` CSS-based sidebar icon with `LabIcon` for proper JupyterLab 4 icon rendering
- Replaced `@lumino/virtualdom` usage with standard DOM APIs in the authentication form
- Updated Lumino CSS class prefixes from `p-` to `lm-`
- Updated TypeScript target from ES2018 to ES2021
- Updated TypeScript to v5.5, ESLint to v8, Prettier to v3, Jest to v29, Stylelint to v16
- Updated CI workflows to use GitHub Actions v4 and JupyterLab 4
- Updated `@jupyterlab/galata` to v5.x for integration tests

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
