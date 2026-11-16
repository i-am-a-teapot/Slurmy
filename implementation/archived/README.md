# Archived Submission Controllers

These launchers are kept for review and regression tests. Current submissions
and Resume use `local_dispatch.py` and do not install or start them.

The compute-node design in `submission_controller.py` did not try to evade
head-node logout cleanup. It submitted a normal SLURM batch job requesting one
core, 256 MiB and ten minutes. SLURM started Python on a compute node, outside the
SSH login session. That Python process reserved a successor controller job before
submitting solver batches. When the submission window filled, it made the
successor depend on the current controller and a worker completing, then exited.
SLURM later started the successor, which continued from saved submission records.
This released the controller’s allocation while waiting and allowed dedicated
whole-node workers to run.

Live tests verified continuation through a one-task worker window and Stop/Resume
with dedicated-node workers. This required permission to invoke scheduler commands
from compute nodes and at least three available account submission slots: current
controller, queued successor, and one worker. Those extra controller jobs counted
toward the same account cap. It did not require nohup, tmux, a persistent SSH
connection, or administrator privileges. Further use should be reviewed with the
cluster administrators; it is disabled in the current workflow.

The archived shell launchers additionally contain an older connected/detached
head-node experiment using `nohup setsid`. It is a separate, historical approach
and cannot defeat login-session cgroup cleanup. It is not used by the app.
