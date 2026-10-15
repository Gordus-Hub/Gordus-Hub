#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANDROID_HOME:=/opt/android-sdk}"
export ANDROID_HOME
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

ANDROID_CLI="$ANDROID_HOME/cmdline-tools/latest/bin/android"
if [[ ! -x "$ANDROID_CLI" ]]; then
  echo "ERROR: Android CLI not found at $ANDROID_CLI" >&2
  exit 1
fi

# Run interactive license prompts non-interactively without masking the command's exit code.
run_with_yes() {
  set +o pipefail
  yes | "$@"
  local command_status=${PIPESTATUS[1]}
  set -o pipefail
  return "$command_status"
}

# Install released Android 16/API 36 packages from the stable channel.
run_with_yes "$ANDROID_CLI" --sdk="$ANDROID_HOME" sdk install \
  platform-tools \
  platforms/android-36 \
  build-tools/36.0.0 \
  emulator \
  system-images/android-36/google_apis/x86_64

# Android 17/API 37 is currently a preview; use the official Beta channel.
# Preview package identifiers can include the API minor-version suffix.
# Android 17 is documented as API 37; the SDK repository publishes its preview
# platform under platforms/android-37.0 (the API identity remains 37).
run_with_yes "$ANDROID_CLI" --sdk="$ANDROID_HOME" sdk install --canary \
  platforms/android-37.0 \
  build-tools/37.0.0

for api in 36 37; do
  test -s "$ANDROID_HOME/platforms/android-$api/android.jar" || {
    echo "ERROR: Android API $api platform is missing or incomplete." >&2
    exit 1
  }
  test -f "$ANDROID_HOME/system-images/android-$api/google_apis/x86_64/package.xml" || {
    echo "ERROR: Android API $api Google APIs x86_64 system image is missing." >&2
    exit 1
  }
done

for version in 36.0.0 37.0.0; do
  test -x "$ANDROID_HOME/build-tools/$version/aapt" || {
    echo "ERROR: Android Build-Tools $version is missing or incomplete." >&2
    exit 1
  }
done

"$ANDROID_HOME/platform-tools/adb" version
"$ANDROID_HOME/emulator/emulator" -version
"$ANDROID_CLI" --sdk="$ANDROID_HOME" --no-metrics -V

printf '\nAndroid SDK installation verified.\n'
printf 'Debian release: '
. /etc/os-release
printf '%s (%s)\n' "$PRETTY_NAME" "${VERSION_CODENAME:-unknown}"
printf 'Installed Android platform APIs: 36 and 37.0 (Android 17 preview). API level 37 verified.\n'
