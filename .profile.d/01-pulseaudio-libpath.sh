#!/usr/bin/env bash

# Make sure binaries installed via heroku-buildpack-apt can find their shared
# libraries (e.g. ffmpeg -> libpulsecommon / libblas) at runtime.
#
# Heroku sources `.profile.d/*.sh` on dyno startup for all process types
# (including `worker`).

APT_LIB_BASE="/app/.apt/usr/lib/x86_64-linux-gnu"

extra_paths=()
for p in \
  "${APT_LIB_BASE}" \
  "${APT_LIB_BASE}/atlas" \
  "${APT_LIB_BASE}/pulseaudio"
do
  if [ -d "$p" ]; then
    extra_paths+=("$p")
  fi
done

if [ "${#extra_paths[@]}" -gt 0 ]; then
  joined=""
  for p in "${extra_paths[@]}"; do
    joined="${joined}${joined:+:}${p}"
  done
  export LD_LIBRARY_PATH="${joined}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi
