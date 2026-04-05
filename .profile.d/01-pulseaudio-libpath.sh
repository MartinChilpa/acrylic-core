#!/usr/bin/env bash

# ffmpeg (installed via heroku-buildpack-apt) can be linked against PulseAudio.
# On Ubuntu Jammy the `libpulsecommon-15.99.so` library lives in a non-default
# directory, so we add it to the dynamic loader search path at runtime.
PULSE_LIB_DIR="/app/.apt/usr/lib/x86_64-linux-gnu/pulseaudio"

if [ -d "$PULSE_LIB_DIR" ]; then
  export LD_LIBRARY_PATH="${PULSE_LIB_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi
