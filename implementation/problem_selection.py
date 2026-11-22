"""Apply explicit filename filtering without losing a user's requested order."""
from pathlib import PurePosixPath


def names(value):
    if isinstance(value,str):return list(dict.fromkeys(line.strip() for line in value.splitlines() if line.strip()))
    if isinstance(value,list) and all(isinstance(name,str) for name in value):return list(dict.fromkeys(value))
    raise ValueError('Problem filenames must be a list or one filename per line.')


def select(matches, selection=''):
    requested=names(selection)
    files=sorted(map(str,matches))
    if not requested:return files
    by_name={}
    for path in files:by_name.setdefault(PurePosixPath(path).name,[]).append(path)
    selected=[]
    for name in requested:
        if PurePosixPath(name).name!=name:raise ValueError('Use filenames, not paths, in the problem selection: '+name)
        found=by_name.get(name,[])
        if not found:raise ValueError('Selected problem filename was not found in this source: '+name)
        if len(found)!=1:raise ValueError('Selected filename is ambiguous; narrow the problem source: '+name)
        selected.append(found[0])
    return selected


def merge(sources,selections):
    choices=list(selections or [])
    if len(choices)>len(sources):raise ValueError('There are more problem selections than sources.')
    ordered=[]
    for index,matches in enumerate(sources):ordered.extend(select(matches,choices[index] if index<len(choices) else ''))
    unique=list(dict.fromkeys(ordered))
    return unique if any(names(choice) for choice in choices) else sorted(unique)
