#!/bin/sh
# Builds Signalsmith Stretch behind its C door next to this file:
# libsstretch.dylib on macOS (clang++), libsstretch.so on Linux (g++).
# For the machine's own architecture, like the rest of the build.
# Windows: build_sstretch.bat. No -ffast-math: Signalsmith's README warns of
# an Apple Clang 16 miscompile with it.
set -e
cd "$(dirname "$0")"
case "$(uname -s)" in
  Darwin)
    ${CXX:-clang++} -std=c++11 -O2 -shared -fPIC -fvisibility=hidden \
      -mmacosx-version-min=11.0 -o libsstretch.dylib sstretch.cpp
    echo "libsstretch.dylib built" ;;
  *)
    ${CXX:-g++} -std=c++11 -O2 -shared -fPIC -fvisibility=hidden \
      -static-libstdc++ -static-libgcc -o libsstretch.so sstretch.cpp
    echo "libsstretch.so built" ;;
esac
