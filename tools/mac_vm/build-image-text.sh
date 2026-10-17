#!/bin/sh
# Build offline image recognition only. Does not launch apps or grant permissions.
set -eu
if [ "$#" -ne 1 ]; then
    echo 'usage: build-image-text.sh OUTPUT_PATH' >&2
    exit 2
fi
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
xcrun clang -arch arm64 -mmacosx-version-min=15.0 \
    -isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX15.5.sdk \
    -fobjc-arc -Wall -Wextra -Werror \
    -framework Foundation -framework Vision -framework ImageIO -framework CoreGraphics \
    "$source_dir/native_image_text.m" -o "$1"
/usr/bin/codesign --force --sign - "$1"
