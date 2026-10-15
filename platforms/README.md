# Platform environments: Debian 13, Android 16 and Android 17

This directory documents the repository's reproducible development environment. It does not replace or modify the host operating system or flash a physical phone.

## What is provisioned

- **Debian 13 (trixie):** a containerized Linux user space, based on `debian:13-slim`.
- **Android 16 / API 36:** SDK platform, Build-Tools 36.0.0, and the Google APIs x86_64 emulator system image.
- **Android 17 / API 37:** preview SDK platform package `platforms/android-37.0`, plus Build-Tools 37.0.0. CI requires the platform JAR and Build-Tools to exist. Google's Android 17 setup guide documents the preview platform and Build-Tools 37, but does not promise an x86_64 emulator image; the automation does not falsely require or claim an Android 17 system image.
- **Android command-line tooling:** checksum-verified command-line-tools archive, Android CLI, Platform-Tools, and Emulator.

Official references:
- Debian 13 (trixie) release notes and installer: https://www.debian.org/releases/trixie/
- Android 16 SDK setup (API 36): https://developer.android.com/about/versions/16/setup-sdk
- Android 17 SDK setup (API 37): https://developer.android.com/about/versions/17/setup-sdk

## Use it

Open this repository in a Dev Container that supports Docker. The container is built from `.devcontainer/Dockerfile`; after the workspace is created, `scripts/install-android-sdks.sh` accepts SDK licenses, installs the SDK platforms, build tools and supported emulator images, then validates the expected files.

To run the setup manually inside the container:

```bash
bash scripts/install-android-sdks.sh
```

To build and validate it locally with Docker:

```bash
docker build --pull -t gordus-hub-platform-env:test -f .devcontainer/Dockerfile .
docker run --rm gordus-hub-platform-env:test bash -lc 'bash /usr/local/bin/install-android-sdks'
```

GitHub Actions performs the same build and SDK package verification in `.github/workflows/platform-environments.yml`. The workflow checks Debian's `VERSION_ID=13` and `VERSION_CODENAME=trixie`, Android 16 platform plus emulator image, and Android 17 API 37.0 platform plus Build-Tools.

## Scope and limitations

- The repository stores setup code and configuration, **not** multi-gigabyte operating-system or emulator binaries.
- Debian runs in a container; it is not installed onto the GitHub repository or the host machine.
- Android API packages and emulator images are downloaded from Google's SDK repositories at setup time.
- This automated workflow verifies Debian version, installed platform JARs and build tools. It does not yet boot an emulator or certify an app's compatibility; there is no Android application source in this repository to test.
- Android 17/API 37 is a preview in the current official setup documentation. It must not be represented as a stable production runtime without rechecking Google's release status.
