#!/usr/bin/env bash

APT_LIB_DIR="/app/.apt/usr/lib/x86_64-linux-gnu"
PULSE_LIB_DIR="/app/.apt/usr/lib/x86_64-linux-gnu/pulseaudio"

export LD_LIBRARY_PATH="${APT_LIB_DIR}:${PULSE_LIB_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"