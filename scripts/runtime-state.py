"""Manage only the dedicated market-data branch; never rewrite source history."""
import argparse
from pathlib import Path
import subprocess
import sqlite3

ALLOWED={'market.sqlite','market.json','notifications-state.json','notifications.json','README.md'}


def run(*args,cwd=None,check=True):
    return subprocess.run(args,cwd=cwd,check=check,text=True,capture_output=True)


def restore(path):
    if Path(path).exists():raise ValueError('Runtime worktree already exists')
    result=run('git','ls-remote','--exit-code','--heads','origin','market-data',check=False)
    if result.returncode==0:
        run('git','fetch','origin','market-data')
        run('git','worktree','add','-B','market-data',path,'FETCH_HEAD')
    elif result.returncode==2:
        run('git','worktree','add','--detach',path)
        run('git','switch','--orphan','market-data',cwd=path)
    else:
        raise RuntimeError('Unable to inspect durable branch; refusing an empty replacement')
    (Path(path)/'README.md').write_text('# Market observations\n\nPublic prices and hashed notification cooldowns only. No portfolio or email credentials.\n')


def persist(path):
    root=Path(path)
    if not (root/'.git').exists():raise ValueError('Missing runtime worktree')
    if run('git','branch','--show-current',cwd=path).stdout.strip()!='market-data':raise ValueError('Wrong runtime branch')
    db=root/'market.sqlite'
    if db.exists():
        with sqlite3.connect(db) as conn:conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    # Stage an explicit allowlist. Never add arbitrary runner files or signals.
    names=[name for name in sorted(ALLOWED) if (root/name).exists()]
    if not names:raise ValueError('No runtime data')
    run('git','add','--',*names,cwd=path)
    if run('git','diff','--cached','--quiet',cwd=path,check=False).returncode:
        run('git','-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit','-m','data: collect market observations and alert state',cwd=path)
    # Retry any already committed state after an earlier transport failure too.
    run('git','push','origin','HEAD:refs/heads/market-data',cwd=path) # No force push.


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['restore','persist']);p.add_argument('path',default='runtime',nargs='?')
    a=p.parse_args()
    try:(restore if a.action=='restore' else persist)(a.path)
    except subprocess.CalledProcessError as e:raise SystemExit(f'Git runtime operation failed (exit {e.returncode}); state not discarded.')
