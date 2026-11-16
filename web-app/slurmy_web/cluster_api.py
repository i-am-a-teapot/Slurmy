"""Adapt SLURM's versioned REST response to the existing cluster view."""
import shlex
import subprocess
import time

import slurm_api
from ssh_transport import connection_options


def fetch_status(host, partition, node=None):
    from .cluster import parse_status, REMOTE_STATUS_SCRIPT
    all_nodes = slurm_api.read(host, 'nodes')['nodes']
    partitions = slurm_api.read(host, 'partitions')['partitions']
    selected = [n for n in all_nodes if partition == 'all' or partition in n.get('partitions', [])]
    if partition != 'all' and not any(p['name'] == partition for p in partitions):
        raise ValueError('Unknown SLURM partition.')
    jobs = [j for j in slurm_api.active_jobs(host) if partition == 'all' or partition in j.get('partition', '').split(',')]
    if node:
        jobs = [j for j in jobs if any(n.get('nodename') == node for n in (j.get('job_resources') or {}).get('allocated_nodes', []))]
    sections = ['PARTITIONS', *[p['name'] for p in partitions], 'NODES']
    for n in selected if not node else []:
        siblings = max(1, slurm_api.number(n.get('threads'), 1))
        cpus = slurm_api.number(n.get('cpus'))
        allocated = slurm_api.number(n.get('alloc_cpus'))
        idle = slurm_api.number(n.get('alloc_idle_cpus'))
        sections.append('|'.join(map(str, [n['name'], '+'.join(n.get('state', [])), cpus,
            f'{allocated}/{idle}/{max(0,cpus-allocated-idle)}/{cpus}', n.get('real_memory', 0), siblings])))
    topology = {n['name']: n for n in all_nodes}
    sections += ['TOPOLOGY', *[f"{n['name']}|{n['threads']}|{n['cores']}" for n in all_nodes], 'ALLOCATIONS']
    hostlists = {}
    queue = []
    for j in jobs:
        identifier = slurm_api.job_id(j)
        sections.append('JobId='+identifier)
        resources = j.get('job_resources') or {}
        names = []
        for allocated in resources.get('allocated_nodes', []):
            name = allocated['nodename']; names.append(name)
            n = topology.get(name)
            if not n: continue
            siblings, per_socket = int(n['threads']), int(n['cores'])
            cpus = []
            for socket, details in allocated.get('sockets', {}).items():
                for core, state in details.get('cores', {}).items():
                    if state != 'allocated': continue
                    physical = int(socket)*per_socket+int(core)
                    cpus.extend(range(physical*siblings, (physical+1)*siblings))
            if cpus: sections.append(' Nodes='+name+' CPU_IDs='+','.join(map(str, cpus)))
        expression = j.get('nodes') or ''
        if expression: hostlists[expression] = ','.join(names) or expression
        row = [identifier, j.get('user_name', ''), j.get('name', ''), '+'.join(j.get('job_state', [])),
               str(slurm_api.number(j.get('node_count'))), str(slurm_api.number(j.get('cpus'))),
               slurm_api.elapsed(j), str(slurm_api.number(j.get('time_limit'))*60), expression,
               j.get('state_reason', ''), j.get('current_working_directory', ''), j.get('comment') or '']
        queue.append('|'.join(str(value).replace('|', ' ').replace('\n', ' ') for value in row))
    sections += ['JOBS', *queue, 'IDENTITY', slurm_api.credentials(host)['user'], 'HOSTS']
    sections += [expression+'|'+names for expression,names in hostlists.items()]
    if node and any(j.get('user_name') == slurm_api.credentials(host)['user'] and '/slurmy/jobs/' in j.get('current_working_directory', '') for j in jobs):
        # The REST API cannot expose private solver progress files. Read these
        # only when expanding a node; no scheduler commands are run over SSH.
        script = 'set -euo pipefail\njobs='+shlex.quote('\n'.join(queue))+'\n'+REMOTE_STATUS_SCRIPT.split("printf 'CALLS\\n'",1)[1]
        result = subprocess.run(['ssh', *connection_options(), '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                                 '--', host, 'bash', '-s'], input=script, text=True, capture_output=True, timeout=20)
        if result.returncode: raise RuntimeError('Could not read private solver progress files over SSH.')
        sections += ['CALLS', result.stdout]
    else:
        sections += ['CALLS', 'METADATA']
    value = parse_status(host, partition, '\n'.join(sections))
    # Do not label a five-second API cache hit as a newly fetched response.
    config = slurm_api.settings(host)
    observations = [entry[0] for key,entry in slurm_api._reads.items()
                    if key[:3] == (host, config['url'], config['version']) and key[3] in {'nodes','jobs'}]
    if observations:
        value['updated'] = time.time() - max(0, time.monotonic()-min(observations))
    value['transport'] = 'REST API'
    return value
