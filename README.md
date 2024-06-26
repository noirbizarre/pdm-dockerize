# pdm-dockerize

[![CI](https://github.com/noirbizarre/pdm-dockerize/actions/workflows/ci.yml/badge.svg)](https://github.com/noirbizarre/pdm-dockerize/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/noirbizarre/pdm-dockerize/main.svg)](https://results.pre-commit.ci/latest/github/noirbizarre/pdm-dockerize/main)
[![PyPI](https://img.shields.io/pypi/v/pdm-dockerize)](https://pypi.org/project/pdm-dockerize/)
[![PyPI - License](https://img.shields.io/pypi/l/pdm-dockerize)](https://pypi.org/project/pdm-dockerize/)

Help generating docker image from PDM projects.

## Installation

Install `pdm-dockerize`:

### With `pipx`

If you installed `pdm` with `pipx` and want to have the command for all projects:

```console
pipx inject pdm pdm-dockerize
```

### With `pip`

If you manually installed `pdm` with `pip`, just install the extra dependency in the same environment:

```console
pip install pdm-dockerize
```

### With `pdm`

You can also install it as a standard `pdm` plugin.

Either globally:

```console
pdm self add pdm-dockerize
```

Either as a local plugin in your project:

```toml
[tool.pdm]
plugins = [
    "pdm-dockerize",
]
```

Then:

```coonsole
pdm install --plugins
```

## Usage

Just use `pdm dockerize` in your multistage build:

```dockerfile
# syntax=docker/dockerfile:1
ARG PY_VERSION=3.11

##
# Build stage: build and install dependencies
##
FROM python:${PY_VERSION} AS builder

ARG VERSION=0.dev
ENV PDM_BUILD_SCM_VERSION=${VERSION}

WORKDIR /project

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm pdm-dockerize

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=pdm.lock,target=pdm.lock \
    --mount=type=cache,target=$HOME/.cache,uid=$UUID \
    pdm dockerize --prod -v

##
# Run stage: create the final runtime container
##
FROM python:${PY_VERSION} AS runtime

WORKDIR /app

# Fetch built dependencies
COPY --from=builder /project/dist/docker /app
# Copy needed files from your project (filter using `.dockerignore`)
COPY  . /app

ENTRYPOINT ["/app/entrypoint"]
CMD ["your-default-command"]
```

### Selecting scripts

By default, the `dockerize` command will render a script without any command as it does not select any script by default.

You can select scripts with the `include` and `exclude` properties of the `tool.pdm.dockerize` section.
Those properties are optional, can be either a string or list of string.
Each string is a [`fnmatch` filter pattern](https://docs.python.org/3/library/fnmatch.html)

Dockerize first select script based on the include patterns and then filter-out those matching with any exclude pattern.

#### Include all scripts

```toml
[tool.pdm.dockerize]
include = "*"
```

#### Include some specific scripts

```toml
[tool.pdm.dockerize]
include = ["my-script", "my-other-script"]
```

#### Include all scripts excluding those matching `prefix-*`

```toml
[tool.pdm.dockerize]
include = "*"
exclude = "prefix-*"
```

#### Include all scripts matching a prefix but two

```toml
[tool.pdm.dockerize]
include = "prefix-*"
exclude = ["prefix-not-you", "prefix-you-neither"]
```

### Selecting binaries

By default, the `dockerize` command will not copy any python executable provided by your dependencies.
You can select binaries with the `include_bins` and `exclude_bins` properties of the `tool.pdm.dockerize` section.
Syntax and behavior are exactly the exact sames than `include`/`exclude` for script selection.

#### Include all python executables

```toml
[tool.pdm.dockerize]
include_bins = "*"
```

#### Include some specific executables

Most of the time, you will look like this

```toml
[tool.pdm.dockerize]
include = ["uvicorn"]
```

### Controlling environment

`pdm-dockerize` respects defined environment variables:
- scripts `env` variables are properly set
- shared `_.env` variables are properly set
- scripts `env_file` are properly loaded
- shared `_.env_file` are properly loaded

In addition, you can define some docker-only environment variables using the `tool.pdm.dockerize.env` table
or some docker-only `.env` files using `tool.pdm.dockerize.env_file`

#### Defining docker-only environment variables

Those environment variables will only be effective in the docker entrypoint.

```toml
[tool.pdm.dockerize.env]
VAR = "value"
```

#### Loading docker-only environment files

This file will only be loaded in the docker entrypoint.

```toml
[tool.pdm.dockerize]
env_file = "docker.env"
```

## Internals

This plugin works by providing by subclassing some `pdm.installers` classes to reuse the installation process:
- `DockerizeInstallManager`, a `pdm` `InstallManager` filtering binaries
- `DockerizeSynchronizer`, a `pdm` `Synchronizer` using a `DockerizeInstallManager` as `InstallManager`
- `FilteringDestination`, a `pdm` `InstallDestination` filtering binaries

This way, the dockerization is using the same installation process just tuned for docker and augmented with `pdm-dockerize` specifics.

## Contributing

Read the [dedicated contributing guidelines](./CONTRIBUTING.md).
