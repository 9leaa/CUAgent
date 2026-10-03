"""Freeze paired P4 inputs before dispatch. No model, account, or App actions."""
import argparse
import json
from pathlib import Path
import subprocess
from agent.daily_benchmark import freeze as freeze_baseline
from agent.daily_report import MODEL, dump, prepare, require, sha
from agent.efficiency import compare

PROJECT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def source_hashes():
    # Include implementation, adapters, independent acceptance and test sources.
    paths = sorted(p for folder in ('agent', 'backend') for p in (PROJECT / folder).rglob('*')
                   if p.is_file() and p.suffix in ('.py', '.mjs', '.ts', '.yml') and '__pycache__' not in p.parts)
    return {str(p.relative_to(PROJECT)): sha(p.read_bytes()) for p in paths}


def prompts():
    script = "import {reportPrompt,aggregateReportPrompt} from './agent/harness/daily-report-runner.mjs'; console.log(JSON.stringify({baseline:reportPrompt(),candidate:aggregateReportPrompt()}));"
    return json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], cwd=PROJECT, text=True))


def freeze(directory):
    root = Path(directory).absolute()
    require(not root.exists(), 'suite exists; never replace original trials')
    root.mkdir(mode=0o700, parents=True)
    sources = source_hashes()
    source_digest = sha(canonical(sources))
    text = prompts()
    freeze_baseline(root / 'baseline')
    baseline = json.loads((root / 'baseline/schedule.json').read_text())
    candidate_root = root / 'candidate'
    candidate_root.mkdir(mode=0o700)
    trials = []
    for case in baseline['trials']:
        index = case['index']
        original = Path(case['runDir'])
        candidate = candidate_root / f'{root.name}-candidate-{index:02d}'
        prepare(root / f'baseline/case-{index:02d}/spec.json', candidate, aggregate=True)
        pair = {}
        for arm, run in [('baseline', original), ('candidate', candidate)]:
            approval = json.loads((run / 'approval.json').read_text())
            oracle = json.loads((run / 'oracle.json').read_text())
            pair[arm] = {'index': index, 'arm': arm, 'taskId': approval['runId'],
                         'sessionId': approval['sessionId'], 'runDir': str(run), 'model': MODEL,
                         'inputs': {**oracle['inputs'], 'task.json': oracle['taskSha256']},
                         'oracleSha256': sha((run / 'oracle.json').read_bytes()),
                         'sourceSha256': source_digest, 'promptSha256': sha(text[arm]),
                         'toolsSha256': sha(canonical(approval['allowedTools'])),
                         'approvalSha256': sha((run / 'approval.json').read_bytes())}
        require(pair['baseline']['inputs'] == pair['candidate']['inputs'], 'pair input bytes differ')
        require(pair['baseline']['oracleSha256'] == pair['candidate']['oracleSha256'], 'pair expected output differs')
        trials.extend(pair[arm] for arm in (('baseline', 'candidate') if index % 2 else ('candidate', 'baseline')))
    manifest = {'version': 1, 'trials': trials, 'sourceFiles': sources, 'prompts': text}
    require(compare(manifest, [])['status'] == 'INCOMPLETE', 'frozen schedule invalid')
    dump(root / 'manifest.json', manifest)
    return {'trials': len(trials), 'manifestSha256': sha((root / 'manifest.json').read_bytes())}


def check(directory):
    root = Path(directory)
    manifest = json.loads((root / 'manifest.json').read_text())
    require(source_hashes() == manifest['sourceFiles'], 'source changed since freeze')
    require(prompts() == manifest['prompts'], 'prompts changed since freeze')
    require(sha(canonical(manifest['sourceFiles'])) == manifest['trials'][0]['sourceSha256'], 'source manifest mismatch')
    compare(manifest, [])
    for trial in manifest['trials']:
        run = Path(trial['runDir'])
        require(sha((run / 'approval.json').read_bytes()) == trial['approvalSha256'], 'approval changed')
        approval = json.loads((run / 'approval.json').read_text())
        require(approval['runId'] == trial['taskId'] and approval['sessionId'] == trial['sessionId'], 'original identity changed')
        require(sha(canonical(approval['allowedTools'])) == trial['toolsSha256'], 'tool approval changed')
        require(sha((run / 'oracle.json').read_bytes()) == trial['oracleSha256'], 'oracle changed')
        for path, digest in trial['inputs'].items():
            file = run / 'workspace' / path
            require(not file.is_symlink() and sha(file.read_bytes()) == digest, 'input changed')
    return {'status': 'FROZEN', 'trials': 40, 'manifestSha256': sha((root / 'manifest.json').read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'check'])
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps((freeze if args.command == 'freeze' else check)(args.directory)))
