"""Frozen C1 evaluation inputs, not model-visible expected answers.

This registry is separate from the completed C0 policy; importing it does not
grant tools or activate a task. The executor/verifier must opt in explicitly.
"""
from dataclasses import dataclass
from types import MappingProxyType

@dataclass(frozen=True)
class Application:
    bundle: str
    executable: str
    title: str

CALCULATOR = Application('com.apple.calculator',
    '/System/Applications/Calculator.app/Contents/MacOS/Calculator', 'Calculator')

def fixture(title):
    return Application('org.cuagent.fixtures',
        '/Users/mvpagent/Applications/CUAgentFixtures.app/Contents/MacOS/CUAgentFixtures', title)

@dataclass(frozen=True)
class C1Case:
    mode: str
    applications: tuple
    fields: tuple
    buttons: tuple
    expected: str
    required_effects: tuple
    prompt: str

C1_CASES = MappingProxyType({
    'cross_app': C1Case('cross_app', (CALCULATOR, fixture('CUAgent Transfer')),
        (('Value', 'observed-calculator-display'),), ('Submit',), 'Transferred 15',
        ('calculator:7+8', 'different-pid', 'transfer-submit'),
        '在 VM 计算器先 All Clear 清空，再用按钮完成 7+8，将操作后的新显示复制到已授权 Transfer 应用的 Value 字段并提交。'
        '禁止自算或共享剪贴板；根据真实观察选择两个应用。将实际最终状态写 result.txt 并读回。'),
    'popup': C1Case('popup', (fixture('CUAgent Popup'), fixture('CUAgent Confirmation')), (), ('Open Confirmation', 'Confirm'),
        'Confirmed cedar-42', ('popup-opened', 'owned-popup-confirmed'),
        '打开原生确认弹窗，重新观察后确认 cedar-42，核对新的 Confirmed 状态，写 result.txt 并读回。'),
    'window_change': C1Case('window_change', (fixture('CUAgent Source'), fixture('CUAgent Destination')),
        (('Code', 'cedar-42'),), ('Open Destination', 'Submit'), 'Submitted cedar-42',
        ('different-window-id', 'destination-submit'),
        '从 Source 打开 Destination 窗口；重新选择、观察目标窗口，填写 Code 为 cedar-42 并提交，写实际状态并读回。'),
    'input_correction': C1Case('input_correction', (fixture('CUAgent Correction'),),
        (('Code', 'cedar-42'),), ('Submit',), 'Submitted cedar-42',
        ('initial-value:cedra-42', 'corrected-value:cedar-42', 'submit'),
        '观察 Code 的错误预填内容，纠正为 cedar-42 后提交；核对真实字段和新状态，写实际状态并读回。'),
    'long_workflow': C1Case('long_workflow', (fixture('CUAgent Workflow'),),
        (('Code', 'cedar-42'), ('Marker', 'harbor-729')),
        ('Next', 'Review', 'Confirm Submission'), 'Submitted cedar-42 | harbor-729 | confirmed',
        ('stage:1', 'stage:2', 'stage:3', 'workflow-submit'),
        '逐步完成三页流程：Code 输入 cedar-42、Next；Marker 输入 harbor-729、Review；核对后 Confirm Submission。'
        '每次动作后新观察，写最终实际状态并读回。'),
    'reobserve_failure': C1Case('reobserve_failure', (fixture('CUAgent Recovery'),),
        (('Code', 'cedar-42'),), ('Submit',), 'Recovered cedar-42',
        ('one-controlled-stale-refusal', 'fresh-observation-after-refusal', 'submit'),
        '填写 Code 为 cedar-42 并提交。此任务包含一次预定无副作用的失效目标拒绝；失败后必须重新观察并使用新目标。'
        '不要盲重试旧快照，核对新状态，写实际状态并读回。'),
})

PHASES = ('baseline', 'after')
REPETITIONS = 3
RAW_BUDGET = 30

def schedule():
    """No execution: immutable, deterministic 36-attempt evaluation schedule."""
    return tuple((phase, case_id, repetition)
                 for phase in PHASES for case_id in C1_CASES
                 for repetition in range(1, REPETITIONS + 1))
