#!/usr/bin/env bash
# Remote build recipe used by slurmy-build.py.
set -euo pipefail

: "${SLURMY_BUILD_WORK:?slurmy-build.py must set SLURMY_BUILD_WORK}"
: "${SLURMY_BUILD_OUTPUT:?slurmy-build.py must set SLURMY_BUILD_OUTPUT}"

BUILD_TMP=$(mktemp -d "${TMPDIR:-/tmp}/slurmy-runsolver-build.XXXXXXXX")
trap 'rm -rf -- "$BUILD_TMP"' EXIT

# Source supplied by Geoff, src_claude_0.tgz (0 means unlimited).
# Bundled beside this recipe so builds and portable workflows need no download.
SOURCE="$SLURMY_BUILD_WORK/source"
[[ -f "$SOURCE/runsolver.cc" ]] || SOURCE="$SLURMY_BUILD_WORK"
[[ -f "$SOURCE/runsolver.cc" ]] || {
    echo 'Missing bundled runsolver source; use implementation/build/runsolver as the build source directory.' >&2
    exit 1
}
for command in make g++ install timeout; do
    command -v "$command" >/dev/null || { echo "Missing build command: $command" >&2; exit 1; }
done
cp -R -- "$SOURCE" "$BUILD_TMP/source"
VERSION=3.4.1

# The non-NUMA form avoids dependence on a cluster-specific libnuma installation.
make -C "$BUILD_TMP/source" clean
make -C "$BUILD_TMP/source" -j"${SLURM_CPUS_PER_TASK:-1}" \
    CFLAGS="-fpermissive -std=c++11 -Dtmpdebug -Wall -DVERSION=\\\"$VERSION\\\" -DSVNVERSION=\\\"4412\\\" -DWSIZE=64" \
    LDFLAGS="-Wl,--build-id" \
    LIBS= \
    runsolver

install -m 0755 -- "$BUILD_TMP/source/runsolver" \
    "$SLURMY_BUILD_OUTPUT/runsolver"
# In-place build drivers copy the work tree over the output tree afterwards.
install -m 0755 -- "$BUILD_TMP/source/runsolver" "$SLURMY_BUILD_WORK/runsolver"
runner_help=$("$SLURMY_BUILD_OUTPUT/runsolver" 2>&1 || true)
grep -q -- '--rss-swap-limit' <<< "$runner_help" || {
    echo "Built runsolver failed its feature check." >&2
    exit 1
}

# Exercise the timestamp/EOF option parser, not only its help text. In the
# supplied source --add-eof once fell through into the next switch handler.
timeout --signal=TERM --kill-after=2 10 "$SLURMY_BUILD_OUTPUT/runsolver" \
    --cpu-limit 0 --wall-clock-limit 5 --rss-swap-limit 100 \
    --timestamp --add-eof --watcher-data "$BUILD_TMP/eof-watcher" \
    --var "$BUILD_TMP/eof-var" --solver-data "$BUILD_TMP/eof-output" \
    /bin/sh -c 'printf "%% SZS status Theorem\n"' > "$BUILD_TMP/eof-controller" 2>&1 || {
    cat "$BUILD_TMP/eof-controller" >&2
    echo 'Built runsolver failed its timestamp/EOF smoke test.' >&2
    exit 1
}
tail -n 1 "$BUILD_TMP/eof-output" | grep -Eq '^[0-9]+([.][0-9]+)?/[0-9]+([.][0-9]+)?[[:space:]]+EOF$' || {
    echo 'Built runsolver did not emit a native timestamped EOF.' >&2
    exit 1
}
