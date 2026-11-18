"""Inspect the saved batch plan without reconstructing it from the batch size."""


def batch_members(job):
    if hasattr(job, '_batch_members'):
        return job._batch_members
    groups = {}
    assigned = set()
    for batch, ids in enumerate(job.metadata.get('planned_batch_tasks', [])):
        groups[batch] = list(dict.fromkeys(ids))
        assigned.update(ids)
    estimated = False
    for task_id in sorted(set(job.tasks) | set(job.results) | set(job.task_batches)):
        if task_id in assigned:
            continue
        batch = job.task_batches.get(task_id)
        if batch is None:
            batch = task_id // job.batch_size
            estimated = True
        groups.setdefault(batch, []).append(task_id)
    job._batch_members = (groups, estimated)
    return job._batch_members


def batch_summaries(job, allocations, page, per_page):
    groups, estimated = batch_members(job)
    ids = sorted(groups)
    rows = []
    for batch in ids[page * per_page:(page + 1) * per_page]:
        members = groups[batch]
        finished = sum(bool(job.results.get(task) and job.results[task].complete) for task in members)
        record = allocations.get(batch)
        if members and finished == len(members):
            state = 'Finished'
        elif record:
            state = record.state.replace('_', ' ').capitalize()
        elif batch in job.submitted_batches or any(task in job.results for task in members):
            state = 'Unfinished'
        else:
            state = 'Not submitted'
        solvers = sorted({job.tasks[task].solver for task in members if task in job.tasks})
        rows.append(dict(id=batch, total=len(members), finished=finished, state=state,
                         solvers=solvers, slurm_id=record.display_id if record else '',
                         node=record.location if record and record.state.upper() in {'RUNNING', 'COMPLETING'} else ''))
    return dict(batches=rows, total=len(ids), membership_estimated=estimated)
