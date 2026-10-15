#!/usr/bin/env bash
set -Eeuo pipefail

: "${ANDROID_HOME:=/opt/android-sdk}"
export ANDROID_HOME
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
if [[ ! -x "$SDKMANAGER" ]]; then
  echo "ERROR: sdkmanager not found at $SDKMANAGER" >&2
  exit 1
fi

# Android 17 (API 37) is currently distributed through the preview channel.
# --channel=3 makes preview packages eligible while keeping package IDs explicit.
yes | "$SDKMANAGER" --sdk_root="$ANDROID_HOME" --channel=3 --licenses >/dev/null

"$SDKMANAGER" --sdk_root="$ANDROID_HOME" --channel=3 --install \
  "platform-tools" \
  "platforms;android-36" \
  "platforms;android-37" \
  "build-tools;36.0.0" \
  "build-tools;37.0.0" \
  "emulator" \
  "system-images;android-36;google_apis;x86_64" \
  "system-images;android-37;google_apis;x86_64"

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

printf '\nAndroid SDK installation verified.\n'
printf 'Debian release: '
. /etc/os-release
printf '%s (%s)\n' "$PRETTY_NAME" "${VERSION_CODENAME:-unknown}"
printf 'Installed Android platform APIs: 36 and 37\n'
