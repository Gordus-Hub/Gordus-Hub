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
       libasound2t64 libgcc-s1 libgl1 libncurses6 libnss3 libpng16-16t64 libpulse0 \\
       libstdc++6 libx11-6 libxcb1 libxcomposite1 libxcursor1 libxi6 \
       libxrender1 libxtst6 zlib1g \
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
