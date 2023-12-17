# CHANGELOG

## 🚀 0.2.3 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: ensure entrypoint stop on failures
- **entrypoint**: use POSIX tests to check `env_file` presence

<!-- End of file -->

## 🚀 0.2.2 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: failsafe `env_file` loading with an explicit warning if not loaded
- **entrypoint**: do not fail if envfile is not present

<!-- End of file -->

## 🚀 0.2.1 (2023-12-17)

### 🐛 Bug fixes

- **entrypoint**: use a `sh`-supported source syntax (eg. '.')

<!-- End of file -->

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

<!-- End of file -->

## 🚀 0.1.0 (2023-12-14)

### 💫 New features

- Initial import

### 📖 Documentation

- **changelog**: prepare for first release
- **README**: small post-import fixes

<!-- End of file -->
