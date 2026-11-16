#!/usr/bin/env bash
# Continue only unfinished calls in the same Slurmy job.
set -euo pipefail
[[ "${1:-}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || exit 2
job="$HOME/slurmy/jobs/$1"
[[ -d "$job" && ! -L "$job" && -f "$job/.stopped" ]] || { echo 'Stop the job before resuming it.' >&2; exit 2; }
[[ -f "$job/submission_context.sh" && -f "$job/remote_submit.sh" ]] || { echo 'This job predates resumable submissions.' >&2; exit 2; }
snapshot=$(squeue -h -r -u "$USER" -o '%Z') || { echo 'Cannot confirm SLURM queue state.' >&2; exit 1; }
if grep -Fxq -- "$job" <<< "$snapshot"; then
    echo 'SLURM still has active allocations for this job.' >&2; exit 1
fi
flock -n "$job/.submit-controller.lock" true || { echo 'The submission controller is still active.' >&2; exit 1; }
cd "$job"
source ./submission_context.sh
rm -- .stopped
# Return the saved context to the local driver; never detach on the head node.
python3 - "$1" "$SAVED_PARTITION" "$SAVED_MAX_OUTSTANDING" "$SAVED_JOB_PREFIX" "$SAVED_JOB_NAME_B64" 1 "${SAVED_RESERVATION:--}" <<'SLURMY_RESUME'
import json,sys
print('SLURMY_RESUME_ARGS '+json.dumps(sys.argv[1:]))
SLURMY_RESUME
