"""Live CPU-capacity estimate for the workflow builder's batch-size default."""
from ssh_transport import connection_options

import subprocess

from slurmy import boolean, positive
from . import workflows


class Topology(list):
    def __init__(self, values, active_tasks=None):
        super().__init__(values)
        self.active_tasks = active_tasks


def partition_nodes(host, partition):
    host, partition = workflows.alias(host), workflows.alias(partition)
    import slurm_api
    if slurm_api.enabled(host):
        user = slurm_api.credentials(host)['user']
        active = sum(j.get('user_name') == user for j in slurm_api.submission_queue(host))
        return Topology(slurm_api.partition_nodes(host, partition), active)
    try:
        result = subprocess.run(
            ['ssh', *connection_options(), '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '--', host,
             f"set -o pipefail; sinfo -p {partition} -N -h -o '%N|%X|%Y|%Z' && "
             "if count=$(squeue -h -r -u \"$USER\" -o '%i' | awk 'NF {n++} END {print n+0}'); then printf '@QUEUE|%s\\n' \"$count\"; fi"],
            text=True, capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f'Cannot inspect partition topology: {exc}') from exc
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Cannot inspect partition topology.')
    nodes = {}
    active_tasks = None
    for line in result.stdout.splitlines():
        if line.startswith('@QUEUE|'):
            value = line.split('|', 1)[1]
            if value.isdecimal(): active_tasks = int(value)
            continue
        fields = line.strip().split('|')
        if len(fields) != 4 or any(not field.isdecimal() or int(field) < 1 for field in fields[1:]):
            raise ValueError('The cluster returned incomplete node topology.')
        nodes[fields[0]] = dict(sockets=int(fields[1]), cores_per_socket=int(fields[2]),
                                threads_per_core=int(fields[3]))
    if not nodes:
        raise ValueError('No compute nodes found in the selected partition.')
    return Topology(nodes.values(), active_tasks)


def estimate(configurations, total_pairs, maximum_outstanding, nodes):
    if total_pairs < 1:
        raise ValueError('No solver-problem pairs match the selected sources.')
    capacities = []
    breakdowns = []
    for configuration in configurations:
        all_cores = str(configuration.get('cores', '')).lower() == 'all'
        cores = 1 if all_cores else positive(str(configuration.get('cores', '')), 'solver cores')
        threads = positive(str(configuration.get('threads_per_core') or 1), 'threads per core')
        dedicated_node = boolean(str(configuration.get('exclusive_node') or ''), 'dedicated node')
        dedicated_socket = boolean(str(configuration.get('exclusive_cpu') or ''), 'dedicated CPU')
        if all_cores and not dedicated_socket:
            raise ValueError('All cores requires dedicated whole CPU sockets.')
        slots = 0
        from collections import Counter
        formulas = Counter()
        for node in nodes:
            sockets, per_socket = node['sockets'], node['cores_per_socket']
            if all_cores:
                cores = per_socket * (sockets if dedicated_node else 1)
            if cores > sockets * per_socket or threads > node['threads_per_core']:
                continue
            if dedicated_node:
                per_node = 1
                formula = '1 batch/compute node (dedicated whole compute node)'
            elif dedicated_socket:
                needed = (cores + per_socket - 1) // per_socket
                per_node = sockets // needed
                formula = f"floor({sockets} CPU {'socket' if sockets == 1 else 'sockets'}/compute node ÷ ceil({cores} physical {'core' if cores == 1 else 'cores'}/batch ÷ {per_socket} physical cores/CPU socket))"
            else:
                per_node = sockets * per_socket // cores
                formula = f"floor(({sockets} CPU {'socket' if sockets == 1 else 'sockets'}/compute node × {per_socket} physical cores/CPU socket) ÷ {cores} physical {'core' if cores == 1 else 'cores'}/batch)"
            slots += per_node
            formulas[(formula, per_node)] += 1
        if not slots:
            name = configuration.get('solver_name') or 'A solver configuration'
            raise ValueError(f'{name} cannot run on any node in this partition.')
        capacities.append(slots)
        breakdowns.append([dict(nodes=count, formula=formula, per_node=per_node) for (formula,per_node),count in formulas.items()])
    if not capacities:
        raise ValueError('Add at least one solver configuration.')
    hardware = min(capacities)
    parallelism = min(hardware, positive(str(maximum_outstanding), 'maximum submitted SLURM tasks'), 50)
    assumed_hardware = max(1, hardware // 2)
    assumed_parallelism = min(assumed_hardware, positive(str(maximum_outstanding), 'maximum submitted SLURM tasks'), 50)
    return dict(batch_size=max(1, (total_pairs + assumed_parallelism - 1) // assumed_parallelism),
                assumed_hardware_parallelism=assumed_hardware, assumed_parallelism=assumed_parallelism,
                total_pairs=total_pairs, node_count=len(nodes), hardware_parallelism=hardware,
                maximum_parallelism=parallelism, configuration_parallelism=capacities, capacity_breakdown=breakdowns)


def suggest(data):
    host, partition = workflows.alias(data.get('host')), workflows.alias(data.get('partition'))
    mode = data.get('mode')
    if mode == 'jobpairs':
        configurations = workflows.imported_rows(workflows.existing(data.get('jobpairs')), check_paths=False)
        count = len(configurations)
        group_counts = [1]*len(configurations)
    elif mode in {'interactive', 'configurations'}:
        configurations = (data.get('configurations') if mode == 'interactive' else
                          workflows.imported_rows(workflows.existing(data.get('configurations_file')), True, False))
        if not isinstance(configurations, list) or not configurations:
            raise ValueError('Add at least one solver configuration.')
        problems = set()
        for value in data.get('globs', []):
            _, matches = workflows.problem_glob(value, materialize=False, host=host)
            problems.update(matches)
        count = len(configurations) * len(problems)
        group_counts = [len(problems)]*len(configurations)
    else:
        raise ValueError('Choose how to define solver-problem pairs.')
    nodes = partition_nodes(host, partition)
    result = estimate(configurations, count, data.get('max_outstanding', 50), nodes)
    balance = result['batch_size']
    options = (data.get('pair_order') or 'solver-major', data.get('max_outstanding', 50), nodes,
               getattr(nodes, 'active_tasks', None))
    fit = submission_fit(configurations, group_counts, data.get('batch_size') or balance, *options)
    selected = max(balance, fit['recommended_batch_size'] or 1)
    suggestion = submission_fit(configurations, group_counts, selected, *options)
    result.update(fit)
    result.update(batch_size=selected, balance_batch_size=balance,
                  fit_batch_size=fit['recommended_batch_size'],
                  suggested_batches=suggestion['estimated_batches'],
                  suggested_fits=suggestion['estimated_batches'] <= suggestion['submission_budget'])
    # One recommendation is used by the field, explanation and submission warning.
    result.update(configuration_count=len(configurations), problem_count=None if mode=='jobpairs' else len(problems),
                  configuration_names=[str(c.get('solver_name') or f'Solver {i+1}') for i,c in enumerate(configurations)],
                  workflow_submit_limit=int(data.get('max_outstanding', 50)))
    result['recommended_batch_size'] = selected if fit['recommended_batch_size'] else None
    result['recommended_batches'] = suggestion['estimated_batches'] if fit['recommended_batch_size'] else None
    return result


def submission_fit(configurations, counts, batch_size, pair_order, maximum_outstanding, nodes, active_tasks=None):
    """Count the same homogeneous batches the core planner creates."""
    from collections import Counter
    from pathlib import Path
    import shlex
    from slurmy import memory_bytes
    groups = Counter()
    for configuration, count in zip(configurations, counts):
        core_text = str(configuration.get('cores') or '1')
        dedicated_cpu = boolean(str(configuration.get('exclusive_cpu') or ''), 'dedicated CPU')
        dedicated_node = boolean(str(configuration.get('exclusive_node') or ''), 'dedicated node')
        if core_text.lower() == 'all':
            topology = {(n['sockets'], n['cores_per_socket']) for n in nodes}
            if len(topology) != 1: raise ValueError('All cores requires homogeneous socket/core topology.')
            sockets, per_socket = topology.pop()
            cores = per_socket*(sockets if dedicated_node else 1)
        else: cores = positive(core_text, 'solver cores')
        cpus = str(configuration.get('cpus') or 'auto')
        allocation = (cores, int(configuration.get('threads_per_core') or 1),
                      0 if cpus.lower() == 'auto' else int(cpus), dedicated_cpu, dedicated_node)
        key = allocation
        if pair_order == 'solver-major':
            command = configuration.get('command') or ''
            key += (configuration.get('solver_name') or (Path(shlex.split(command)[0]).name if command else ''),
                    configuration.get('solver_directory', ''), command,
                    int(configuration.get('wc_limit', 1)), int(configuration.get('cpu_limit', 1)),
                    memory_bytes(str(configuration.get('mem_limit', '1MiB'))),
                    *(boolean(str(configuration.get(field) or ''), field) for field in ('omit_cpu_limit','omit_wc_limit','omit_mem_limit')))
        groups[key] += count
    size = positive(str(batch_size), 'solver-problem pairs per batch')
    free = max(0, 50-active_tasks) if active_tasks is not None else 50
    budget = min(50, free, positive(str(maximum_outstanding), 'maximum submitted SLURM tasks'))
    def count_batches(size): return sum((count+size-1)//size for count in groups.values())
    batches = count_batches(size)
    recommendation = None
    if len(groups) <= budget:
        low, high = 1, max(groups.values(), default=1)
        while low < high:
            middle = (low+high)//2
            if count_batches(middle) <= budget: high = middle
            else: low = middle+1
        recommendation = low
    return dict(estimated_batches=batches, submission_budget=budget, account_submit_limit=50,
                minimum_batches=len(groups), group_pair_counts=list(groups.values()), account_active_tasks=active_tasks, account_free_slots=free,
                recommended_batch_size=recommendation,
                recommended_batches=count_batches(recommendation) if recommendation else None)
