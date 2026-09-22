from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/runtime-state.py'


def git(*args,cwd):
    return subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True,check=True).stdout.strip()


class DurableBranchTests(unittest.TestCase):
    def test_retry_pushes_committed_state_after_remote_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);remote=base/'remote.git';repo=base/'repo';repo.mkdir()
            git('init','--bare',str(remote),cwd=temp);git('init','-b','main',cwd=repo)
            git('config','user.name','Test',cwd=repo);git('config','user.email','test@example.invalid',cwd=repo)
            (repo/'README.md').write_text('Source only');git('add','.',cwd=repo);git('commit','-m','init',cwd=repo)
            git('remote','add','origin',str(remote),cwd=repo);git('push','-u','origin','main',cwd=repo)
            def run(action,check=True):return subprocess.run(['python',str(SCRIPT),action,'runtime'],cwd=repo,check=check,capture_output=True)
            run('restore');(repo/'runtime/market.json').write_text('{"history":[1]}')
            hook=remote/'hooks/pre-receive';hook.write_text('#!/bin/sh\nexit 1\n');hook.chmod(0o755)
            self.assertNotEqual(run('persist',check=False).returncode,0)
            committed=git('rev-parse','HEAD',cwd=repo/'runtime')
            self.assertEqual(git('status','--porcelain',cwd=repo/'runtime'),'')
            hook.unlink();run('persist')
            self.assertEqual(committed,git('rev-parse','market-data',cwd=remote))

    def test_first_run_and_restore_preserve_history_and_ignore_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);remote=base/'remote.git';repo=base/'repo';repo.mkdir()
            git('init','--bare',str(remote),cwd=temp);git('init','-b','main',cwd=repo)
            git('config','user.name','Test',cwd=repo);git('config','user.email','test@example.invalid',cwd=repo)
            (repo/'README.md').write_text('Source only');git('add','.',cwd=repo);git('commit','-m','init',cwd=repo)
            git('remote','add','origin',str(remote),cwd=repo);git('push','-u','origin','main',cwd=repo)
            source_sha=git('rev-parse','HEAD',cwd=repo)
            def run(action):return subprocess.run(['python',str(SCRIPT),action,'runtime'],cwd=repo,check=True,capture_output=True)
            run('restore');(repo/'runtime/market.json').write_text('{"history":[1]}')
            (repo/'runtime/secret.txt').write_text('THIS MUST NOT BE PUSHED');run('persist')
            files=git('ls-tree','--name-only','market-data',cwd=repo)
            self.assertIn('market.json',files);self.assertNotIn('secret.txt',files)
            self.assertEqual(source_sha,git('rev-parse','HEAD',cwd=repo))
            git('worktree','remove','--force','runtime',cwd=repo);run('restore')
            self.assertEqual((repo/'runtime/market.json').read_text(),'{"history":[1]}')
            run('persist');self.assertEqual(source_sha,git('rev-parse','HEAD',cwd=repo))


if __name__=='__main__':unittest.main()
