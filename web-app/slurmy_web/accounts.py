"""Read the selected SSH user's SLURM account associations, with a short cache."""
import re
import subprocess
import threading
import time
from ssh_transport import connection_options

_cache = {}
_lock = threading.Lock()
TTL = 300


def memberships(host):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', host):
        raise ValueError('Invalid SSH host.')
    with _lock:
        now = time.monotonic()
        cached = _cache.get(host)
        if cached and now - cached[0] < TTL:
            return dict(cached[1], cached=True)
        try:
            result = subprocess.run(
                ['ssh', *connection_options(), '-T', '-o', 'BatchMode=yes', '-o',
                 'ConnectTimeout=10', '--', host,
                 'sacctmgr -nP show association where user="$(id -un)" format=Cluster,Account,User,Partition'],
                capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('Cannot check SLURM accounts. Check the cluster connection and retry.') from exc
        if result.returncode:
            raise ValueError('Cannot check SLURM accounts. Check the cluster connection and retry.')
        accounts = sorted({fields[1] for line in result.stdout.splitlines()
                           if len(fields := line.split('|')) >= 3
                           and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', fields[1])})
        if not accounts:
            raise ValueError('SLURM returned no account associations. Retry or contact your cluster administrator.')
        value = dict(accounts=accounts, preferred=choose(accounts), checked_at=time.time(), cached=False)
        _cache[host] = (time.monotonic(), value)
        return dict(value)


def choose(accounts, requested=None):
    """Preserve available explicit choices; otherwise prefer a non-default account."""
    if requested in accounts:
        return requested
    if requested == '' and 'default' in accounts:
        return ''
    if 'cpuopt' in accounts:
        return 'cpuopt'
    return next((account for account in sorted(accounts) if account != 'default'), '')
