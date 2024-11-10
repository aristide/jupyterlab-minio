# jupyterlab-minio

[![Github Actions Status](https://github.com/aristide/jupyterlab-minio/workflows/Build/badge.svg)](https://github.com/aristide/jupyterlab-minio/actions/workflows/build.yml)
[![PyPI version](https://badge.fury.io/py/jupyterlab-minio.svg)](https://badge.fury.io/py/jupyterlab-minio)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/jupyterlab-minio/jupyterlab-minio/master?urlpath=lab)

JupyterLab extension for browsing Minio object storage.

This extension is composed of a Python package named `jupyterlab-minio`.

![Jupyter Minio](https://raw.githubusercontent.com/aristide/jupyterlab-minio/master/minio-browser-screenshot.gif)

## Installation

This extension works on JupyterLab 3 only.

To install:

```bash
pip install jupyterlab-minio
```

You may also need to run:

```bash
jupyter server extension enable jupyterlab-minio
```

to make sure the server extension is enabled. Then, restart (stop and start) JupyterLab.

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

## Development

### Development Installation

> **Note:** You will need NodeJS to build the extension package.

The `jlpm` command is JupyterLab's pinned version of [yarn](https://yarnpkg.com/), but you may also use `yarn` or `npm` as an alternative.

To install the development environment:

```bash
# Clone the repository and navigate to the project folder
git clone https://github.com/aristide/jupyterlab-minio.git
cd jupyterlab-minio

# Set up a virtual environment
virtualenv .venv
source .venv/bin/activate

# Install required packages for development
pip install jupyter_packaging~=0.10

# Install the package in development mode
pip install -e .

# Link the development version of the extension with JupyterLab
jupyter labextension develop . --overwrite

# Enable the server extension manually in development mode
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
jupyter lab build --minimize=False
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

3. **Install the Remote - Containers Extension**:

   - In Visual Studio Code, go to the Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X` on Mac).
   - Search for and install the "Remote - Containers" extension by Microsoft.

4. **Open the Project in a Devcontainer**:

   - Open the `jupyterlab-minio` project folder in Visual Studio Code.
   - You should see a prompt to reopen the folder in a devcontainer. Click "Reopen in Container." If you don’t see the prompt, use the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P` on Mac), type "Remote-Containers: Reopen in Container," and select it.

5. **Wait for the Container to Build**:

   - VS Code will build the devcontainer using the `.devcontainer/Dockerfile` or `.devcontainer/devcontainer.json` configuration. This setup may take a few minutes as it installs dependencies and configures the environment.

6. **Access the Development Environment**:

   - Once the container is running, you can access the terminal (` Ctrl+`` or  `Cmd+``on Mac) and use the VS Code editor as usual. The devcontainer has all necessary tools pre-installed for working on`jupyterlab-minio`.

7. **Run the Extension**:
   - To run and test the extension in JupyterLab, use the development commands from above, such as `jlpm watch` and `jupyter lab --debug --ServerApp.token='' --ip=0.0.0.0 --notebook-dir=notebooks`.

This setup allows you to develop in a consistent, isolated environment that replicates the project dependencies and configurations, making collaboration easier.
