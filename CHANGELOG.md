# CHANGELOG

## 🚀 0.6.0 (2024-09-23)

### 🚨 Breaking changes

- **pdm**: move to `pdm>=2.19` API


## 🚀 0.5.1 (2024-06-26)

### 🐛 Bug fixes

- **pdm**: `pdm>=2.15` changed `InstallManager` and `Synchronizer` signatures

### 📖 Documentation

- **README**: update plugin install instructions (fix [#8](https://github.com/noirbizarre/pdm-dockerize/issues/8))


## 🚀 0.5.0 (2024-04-12)

### 🚨 Breaking changes

- **pdm**: support and requires `pdm>=2.14`

### 📖 Documentation

- **CHANGELOG**: fix bad CHANGELOG formatting
- **README**: document the base principle in README

### 📦 Build

- update the build dependencies, update to ruff 0.3+ and lock


## 🚀 0.4.0 (2024-04-04)

### 🚨 Breaking changes

- **pdm**: now depends on `pdm>=2.13`

### 💫 New features

- **env**: allow to source/export some docker-only environment variables or dotenv files
- **shellcheck**: all generated scripts are passing `shellcheck` validation

### 📦 Build

- **deps**: update dev dependencies

## 🚀 0.3.1 (2023-12-22)

### 🐛 Bug fixes

- **entrypoint**: run from the app dir and use absolute `$PATH` and `$PYTHONPATH`

## 🚀 0.3.0 (2023-12-21)

### 💫 New features

- **PYTHONPATH**: support src-layout and non-root packages for `pdm.backend`-based projects

### 📖 Documentation

- **README**: add some details

### 📦 Build

- update some tooling

## 🚀 0.2.4 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: remove the `-o pipefail` option which is not cross-platform

## 🚀 0.2.3 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: ensure entrypoint stop on failures
- **entrypoint**: use POSIX tests to check `env_file` presence

## 🚀 0.2.2 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: failsafe `env_file` loading with an explicit warning if not loaded
- **entrypoint**: do not fail if envfile is not present

## 🚀 0.2.1 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: use a `sh`-supported source syntax (eg. '.')

## 🚀 0.2.0 (2023-12-17)

### 💫 New features

- **entrypoint**: support parameters passthrough and parameters extrapolation
- python executables needs to be selected using the same filter syntax than scripts

### 🐛 Bug fixes

- **entrypoint**: ensure parameters are given to the resulting command
- **entrypoint**: properly handle whitespace depending on the script kind
- **entrypoint**: support pre and post scripts
- **entrypoint**: take global options into account
- **entrypoint**: use a `sh`-compatible function syntax for `usage`
- **entrypoint**: ensure the entrypoint is executable
- **entrypoint**: export missing environment variables
- **pdm**: support PDM>=2.11
- **pyproject**: add the missing Python 3.12 support classifier
- **python**: minimum Python version is now 3.8.1 to align with Syrupy

### 📖 Documentation

- **README**: Fix the `Dockerfile` snippet

## 🚀 0.1.0 (2023-12-14)

### 💫 New features

- Initial import

### 📖 Documentation

- **changelog**: prepare for first release
- **README**: small post-import fixes