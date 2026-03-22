# jupyterlab-minio

[![Github Actions Status](https://github.com/aristide/jupyterlab-minio/workflows/Build/badge.svg)](https://github.com/aristide/jupyterlab-minio/actions/workflows/build.yml)
[![PyPI version](https://badge.fury.io/py/jupyterlab-minio.svg)](https://badge.fury.io/py/jupyterlab-minio)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/jupyterlab-minio/jupyterlab-minio/master?urlpath=lab)

JupyterLab extension for browsing Minio object storage.

This extension is composed of a Python package named `jupyterlab-minio`.

![Jupyter Minio](https://raw.githubusercontent.com/aristide/jupyterlab-minio/master/minio-browser-screenshot.gif)

## Requirements

- JupyterLab >= 4.0.0
- Python >= 3.8
- Node.js >= 18 (for development only)

## Installation

To install:

```bash
pip install jupyterlab-minio
```

You may also need to run:

```bash
jupyter server extension enable jupyterlab-minio
```

to make sure the server extension is enabled. Then, restart (stop and start) JupyterLab.

## Features

- **Browse S3/MinIO** buckets and objects in a dedicated sidebar panel
- **Bucket management**: Create and delete buckets
- **File operations**: Upload, download, rename, copy, move, and delete files and folders
- **Cross-bucket copy/move**: Copy or move files between different S3 paths via a path picker dialog
- **S3 to local transfer**: Copy files between S3 and the local JupyterLab filesystem
- **Upload from computer**: Upload files directly from your computer to S3 using the toolbar upload button
- **Filter**: Quickly filter files and folders by name in the current directory
- **Create folders**: Create new folders within buckets from the toolbar
- **Recursive deletion**: Delete folders and all their contents
- **Copy to S3**: Right-click files in the default JupyterLab file browser to copy them to S3
- **Authentication**: Configure credentials via environment variables, `~/.mc/config.json`, or the built-in form
- **Theme-aware icon**: Sidebar icon automatically adapts to JupyterLab Light, Dark, and Dark High Contrast themes

## Usage

### Configuration

If you have a `~/.mc/config.json` file, no further configuration is necessary.

To configure using environment variables, set:

```bash
export MINIO_ENDPOINT="https://s3.us.cloud-object-storage.appdomain.cloud"
export MINIO_ACCESS_KEY="my-access-key-id"
export MINIO_SECRET_KEY="secret"
```

Alternatively, you can start without any configuration and fill in your endpoint and credentials through the form when prompted.

### S3 Browser Toolbar

The S3 browser sidebar includes toolbar buttons for common operations:

| Button         | Action                                                      |
| -------------- | ----------------------------------------------------------- |
| **+**          | Create a new bucket (at root level)                         |
| **New Folder** | Create a new folder in the current directory                |
| **Upload**     | Upload files from your computer to the current S3 directory |
| **Filter**     | Toggle a search bar to filter files by name                 |
| **Refresh**    | Refresh the current directory listing                       |
| **Settings**   | Reset your S3 credentials                                   |

### Context Menu

Right-click on files or folders in the S3 browser for additional options:

- **Copy to S3 Path...** — Copy to another S3 location
- **Move to S3 Path...** — Move to another S3 location
- **Copy to Local Filesystem...** — Download to the local JupyterLab filesystem
- **Delete from S3** — Delete the selected file or folder (folders are deleted recursively)

## Development

### Development Installation

> **Note:** You will need NodeJS >= 18 to build the extension package.

The `jlpm` command is JupyterLab's pinned version of [yarn](https://yarnpkg.com/), but you may also use `yarn` or `npm` as an alternative.

To install the development environment:

```bash
# Clone the repository and navigate to the project folder
git clone https://github.com/aristide/jupyterlab-minio.git
cd jupyterlab-minio

# Set up a virtual environment
virtualenv .venv
source .venv/bin/activate

# Install the package in development mode
pip install -e ".[test]"

# Link the development version of the extension with JupyterLab
jupyter labextension develop . --overwrite

# Install the server extension config (not deployed automatically in dev mode)
export JUPYTER_SYS_CONFIG=$(python -c "import sysconfig, os; print(os.path.join(sysconfig.get_path('data'), 'etc', 'jupyter'))")
cp jupyter-config/server-config/jupyterlab-minio.json "$JUPYTER_SYS_CONFIG/jupyter_server_config.d/"

# Enable the server extension
jupyter server extension enable jupyterlab-minio

# Build the extension TypeScript source files
jlpm build
```

To continuously watch the source directory and rebuild the extension on changes, run:

```bash
# Watch the source directory in one terminal
jlpm watch

# In another terminal, run JupyterLab in debug mode
jupyter lab --debug
```

To ensure source maps are generated for easier debugging:

```bash
jlpm build:lib && jlpm build:labextension:dev
```

### Development Uninstallation

```bash
# Disable the server extension in development mode
jupyter server extension disable jupyterlab-minio

# Uninstall the package
pip uninstall jupyterlab-minio
```

In development mode, you may also need to remove the symlink created by `jupyter labextension develop`. To find its location, use `jupyter labextension list` to locate the `labextensions` folder, then remove the `jupyterlab-minio` symlink within it.

### Testing the Extension

#### Server Tests

To install test dependencies and execute server tests:

```bash
pip install -e ".[test]"
jupyter labextension develop . --overwrite
pytest -vv -r ap --cov jupyterlab-minio
```

#### Frontend Tests

To execute frontend tests using [Jest](https://jestjs.io/):

```bash
jlpm
jlpm test
```

#### Integration Tests

This extension uses [Playwright](https://playwright.dev/docs/intro/) with the JupyterLab helper [Galata](https://github.com/jupyterlab/jupyterlab/tree/master/galata) for integration tests.

Refer to the [ui-tests README](./ui-tests/README.md) for further details.

## Running the Devcontainer in Visual Studio Code

1. **Install Docker**: Ensure Docker is installed and running on your machine. You can download it from [Docker's official site](https://www.docker.com/products/docker-desktop).

2. **Install Visual Studio Code**: Download and install [Visual Studio Code](https://code.visualstudio.com/).

3. **Install the Dev Containers Extension**:
   - In Visual Studio Code, go to the Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X` on Mac).
   - Search for and install the "Dev Containers" extension by Microsoft.

4. **Open the Project in a Devcontainer**:
   - Open the `jupyterlab-minio` project folder in Visual Studio Code.
   - You should see a prompt to reopen the folder in a devcontainer. Click "Reopen in Container." If you don't see the prompt, use the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P` on Mac), type "Dev Containers: Reopen in Container," and select it.

5. **Wait for the Container to Build**:
   - VS Code will build the devcontainer using the `.devcontainer/Dockerfile` or `.devcontainer/devcontainer.json` configuration. This setup may take a few minutes as it installs dependencies and configures the environment.

6. **Access the Development Environment**:
   - Once the container is running, you can access the terminal (`Ctrl+\`` or `Cmd+\``on Mac) and use the VS Code editor as usual. The devcontainer has all necessary tools pre-installed for working on`jupyterlab-minio`.

7. **Run the Extension**:
   - To run and test the extension in JupyterLab, use the development commands from above, such as `jlpm watch` and `jupyter lab --debug --ServerApp.token='' --ip=0.0.0.0 --notebook-dir=notebooks`.

This setup allows you to develop in a consistent, isolated environment that replicates the project dependencies and configurations, making collaboration easier.
