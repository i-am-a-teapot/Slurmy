"""Prepare immutable packaged TPTP axioms in one process, with atomic copies."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys


def prepare(job: Path):
    paths = json.loads((job / 'axiom-paths.json').read_text(encoding='utf-8'))
    root = job / 'rootfs'
    target_root = root / '.slurmy-tptp/Axioms'
    target_root.mkdir(parents=True, exist_ok=True)
    parents = set()
    print(f'Preparing custom TPTP axioms: {len(paths)} files', flush=True)
    for index, (source, relative) in enumerate(paths, 1):
        remote = source.startswith('tptp:')
        source_path, relative_path = PurePosixPath(source[5:] if remote else source), PurePosixPath(relative)
        if not source_path.is_absolute() or '..' in source_path.parts or relative_path.is_absolute() or '..' in relative_path.parts:
            raise ValueError('Invalid packaged axiom path.')
        if remote:
            source = Path(source_path)
            parts = source_path.parts
            if len(parts)<7 or parts[:4] != ('/','share','datasets','TPTP') or not parts[4].startswith('TPTP-') or parts[5] != 'Axioms':
                raise ValueError('Invalid shared axiom path.')
            collection = Path(*parts[:5]).resolve()
            if not source.resolve().is_relative_to(collection):
                raise ValueError('Shared axiom escapes its TPTP collection.')
        else:
            source = root / str(source_path).lstrip('/')
        target = target_root / relative_path
        if target.parent not in parents:
            target.parent.mkdir(parents=True, exist_ok=True)
            parents.add(target.parent)
        temporary = target.with_name(target.name + '.slurmy-copy-tmp')
        try:
            shutil.copyfile(source, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        if index % 500 == 0 or index == len(paths):
            print(f'Preparing custom TPTP axioms: {index}/{len(paths)}', flush=True)


if __name__ == '__main__':
    try:
        prepare(Path(os.environ['JOB_DIR']))
    except (OSError, ValueError, KeyError) as error:
        print(f'Custom TPTP axiom preparation failed: {error}', file=sys.stderr)
        raise SystemExit(1)
