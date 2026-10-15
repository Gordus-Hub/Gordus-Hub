FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG ANDROID_CMDLINE_TOOLS_REVISION=15859902
ARG ANDROID_CMDLINE_TOOLS_SHA256=4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583

ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates curl git openjdk-21-jdk-headless unzip \
       libasound2t64 libdbus-1-3 libegl1 libexpat1 libfontconfig1 libfreetype6 \
       libgcc-s1 libgbm1 libgl1 libglu1-mesa libncurses6 libnss3 libopengl0 \
       libpng16-16t64 libpulse0 libstdc++6 libvulkan1 zlib1g \
       libx11-6 libx11-xcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
       libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
       libxcb-xkb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
       libxi6 libxinerama1 libxkbcommon-x11-0 libxkbcommon0 libxkbfile1 \
       libxrandr2 libxrender1 libxres1 libxshmfence1 libxss1 libxtst6 libxv1 libxxf86vm1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" /tmp/android-cli \
    && curl --fail --location --silent --show-error \
       "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_CMDLINE_TOOLS_REVISION}_latest.zip" \
       --output /tmp/android-cli.zip \
    && printf "%s  %s\n" "$ANDROID_CMDLINE_TOOLS_SHA256" /tmp/android-cli.zip | sha256sum --check --status \
    && unzip -q /tmp/android-cli.zip -d /tmp/android-cli \
    && mkdir -p "${ANDROID_HOME}/cmdline-tools/latest" \
    && cp -a /tmp/android-cli/cmdline-tools/. "${ANDROID_HOME}/cmdline-tools/latest/" \
    && rm -rf /tmp/android-cli /tmp/android-cli.zip \
    && chmod -R a+rX "${ANDROID_HOME}"

COPY scripts/install-android-sdks.sh /usr/local/bin/install-android-sdks
RUN chmod 0755 /usr/local/bin/install-android-sdks

WORKDIR /workspace
CMD ["bash"]
