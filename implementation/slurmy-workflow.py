#!/usr/bin/env python3
"""Regenerate workflow files from a text-only workflow.json definition."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'web-app'))
from slurmy_web import workflows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('definition',type=Path)
    parser.add_argument('--host',default=os.environ.get('SLURMY_HOST','datalab'),help='SSH host for validation; never stored in the definition')
    parser.add_argument('--check',action='store_true',help='Validate without replacing generated files')
    args=parser.parse_args(argv)
    definition=args.definition.expanduser().resolve()
    data=json.loads(definition.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Workflow definition must be a JSON object.')
    data['host']=workflows.alias(args.host)
    data.setdefault('name',definition.parent.name)
    previous=workflows.BASE
    try:
        workflows.BASE=definition.parent
        if args.check:
            _,_,count=workflows.specification(data,definition.parent)
        else:
            _,count=workflows.save(data,definition.parent)
    finally:
        workflows.BASE=previous
    print(f'{"Validated" if args.check else "Regenerated"} workflow: {count} solver-problem pairs')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError) as error:raise SystemExit(str(error))
