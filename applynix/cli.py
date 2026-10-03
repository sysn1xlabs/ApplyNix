import argparse
import csv
import json
import os
import sys
from pathlib import Path
from .core import Store, analyze, prepare, export, STATUSES

def main(argv=None):
    parser = argparse.ArgumentParser(prog='applynix', description='Tailor. Review. Apply. Track. — sysn1xlabs')
    parser.add_argument('--home', type=Path, default=Path(os.environ.get('APPLYNIX_HOME', Path.home() / '.applynix')))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    for command in ('analyze', 'tailor'):
        p = sub.add_parser(command)
        p.add_argument('job', type=Path, help='UTF-8 job description file; URL fetching is not yet supported')
        p.add_argument('--profile', type=Path)
    p = sub.add_parser('batch')
    p.add_argument('csv', type=Path, help='CSV with a job_file column; paths are relative to the CSV')
    p.add_argument('--profile', type=Path)
    sub.add_parser('history')
    p = sub.add_parser('show'); p.add_argument('id')
    p = sub.add_parser('approve'); p.add_argument('id')
    p = sub.add_parser('status'); p.add_argument('id'); p.add_argument('status', choices=STATUSES); p.add_argument('--note', default='')
    p = sub.add_parser('serve'); p.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        args.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        if args.command == 'init':
            target = args.home / 'profile.json'
            if target.exists():
                raise ValueError('Profile exists; refusing to overwrite.')
            from importlib.resources import files
            target.write_text(files('applynix').joinpath('profile.example.json').read_text(encoding='utf-8'), encoding='utf-8')
            print(f'Example profile created at {target}. Replace fictional data before use.')
            return 0
        store = Store(args.home / 'history.sqlite3')
        if args.command == 'serve':
            from .web import serve
            serve(store, args.home, args.port)
        elif args.command in ('analyze', 'tailor', 'batch'):
            profile = json.loads((args.profile or args.home / 'profile.json').read_text(encoding='utf-8'))
            if args.command == 'batch':
                with args.csv.open(encoding='utf-8-sig', newline='') as file:
                    rows = list(csv.DictReader(file))
                if len(rows) > 50:
                    raise ValueError('Batch limit is 50 descriptions.')
                failures = 0
                for index, row in enumerate(rows, 1):
                    try:
                        path = args.csv.parent / row['job_file']
                        bundle = prepare(profile, path.read_text(encoding='utf-8'))
                        identity = store.save(bundle)
                        export(bundle, args.home / 'applications' / identity)
                        print(f'{index}: {identity} — {bundle["analysis"]["title"]} — prepared')
                    except (ValueError, OSError, KeyError) as exc:
                        failures += 1
                        print(f'{index}: FAILED — {exc}', file=sys.stderr)
                return 1 if failures else 0
            text = args.job.read_text(encoding='utf-8')
            if args.command == 'analyze':
                print(json.dumps(analyze(text, profile), indent=2))
            else:
                bundle = prepare(profile, text)
                identity = store.save(bundle)
                destination = args.home / 'applications' / identity
                export(bundle, destination)
                print(f'Draft {identity}\nExports: {destination}\nReview: applynix show {identity}\nApprove: applynix approve {identity}')
        elif args.command == 'history':
            print(json.dumps(store.list(), indent=2))
        elif args.command == 'show':
            record = store.get(args.id)
            print(json.dumps({'id': args.id, 'status': record['status'], 'analysis': record['bundle']['analysis'], 'changes': record['bundle']['changes'], 'events': store.events(args.id)}, indent=2))
            print(record['bundle']['resume'])
        elif args.command == 'approve':
            record = store.get(args.id)
            print(json.dumps(record['bundle']['analysis'], indent=2))
            print(record['bundle']['resume'])
            print('Changes:', json.dumps(record['bundle']['changes'], indent=2))
            confirmation = input(f'Type APPROVE {args.id} to approve this exact draft (no submission): ')
            if confirmation != f'APPROVE {args.id}':
                print('Cancelled.'); return 0
            store.status(args.id, 'READY', 'User reviewed and approved exact draft in CLI.')
            print('Approved. Submit manually on the employer site, then record status APPLIED with a receipt note.')
        elif args.command == 'status':
            if args.status == 'READY':
                raise ValueError('Use approve to review and approve a draft.')
            store.status(args.id, args.status, args.note)
            print('Status recorded.')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
