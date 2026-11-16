#!/usr/bin/env bash
# One finite wave only. The laptop owns retries and waits between waves.
set -euo pipefail
[[ "${1:-}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || exit 2
job="$HOME/slurmy/jobs/$1"
[[ -d "$job" && ! -L "$job" && -f "$job/remote_submit.sh" ]] || exit 2
cd "$job"
# RPC uses fd 3 directly and bypasses this log, keeping request data private.
exec > >(tee -a "$job/submission-controller.log") 2>&1
exec 8> .dispatch-launch.lock
flock -n 8 || { echo 'Another submission wave is active.' >&2; exit 1; }
[[ ! -f .stopped ]] || { echo 'Job is stopped. Use Resume to continue.' >&2; exit 1; }
echo "Slurmy job ID: $1"
export SLURMY_MANAGED_CONTROLLER=1
export SLURMY_CONTROLLER_DEADLINE=$(( $(date +%s) + 60 ))
# No detached process, nohup, tmux, or compute-node controller is launched.
exec env -u BASH_ENV -u ENV bash --noprofile --norc ./remote_submit.sh "$@"
