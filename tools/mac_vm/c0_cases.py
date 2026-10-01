"""Developer-selected fixed tasks; expected values never enter the action response."""
from dataclasses import dataclass
from types import MappingProxyType

@dataclass(frozen=True)
class CalculatorCase:
    expression: str
    actions: tuple
    expected: str
    bundle: str = 'com.apple.calculator'
    app_name: str = 'Calculator'
    title: str = 'Calculator'
    executable: str = '/System/Applications/Calculator.app/Contents/MacOS/Calculator'

def case(left, operator, right, expected):
    symbol = {'Add': '+', 'Subtract': '−', 'Multiply': '×'}[operator]
    return CalculatorCase(f'{left}{symbol}{right}',
                          ('All Clear', *left, operator, *right, 'Equals'), expected)

CALCULATORS = MappingProxyType({
    'add27_16': case('27', 'Add', '16', '43'),
    'add8_9': case('8', 'Add', '9', '17'),
    'add125_75': case('125', 'Add', '75', '200'),
    'sub90_17': case('90', 'Subtract', '17', '73'),
    'sub50_28': case('50', 'Subtract', '28', '22'),
    'sub101_1': case('101', 'Subtract', '1', '100'),
    'mul12_34': case('12', 'Multiply', '34', '408'),
    'mul7_8': case('7', 'Multiply', '8', '56'),
    'mul15_6': case('15', 'Multiply', '6', '90'),
})

@dataclass(frozen=True)
class UICase:
    mode: str
    title: str
    expected: str
    fields: tuple
    buttons: tuple
    bundle: str = 'org.cuagent.fixtures'
    app_name: str = 'CUAgentFixtures'
    executable: str = '/Users/mvpagent/Applications/CUAgentFixtures.app/Contents/MacOS/CUAgentFixtures'

UI_CASES = MappingProxyType({
    'form': UICase('form','CUAgent Form','Submitted: cedar-42 | local form test',
                   (('Code','cedar-42'),('Note','local form test')),('Submit',)),
    'scroll': UICase('scroll','CUAgent Scroll','harbor-729',(),()),
    'document': UICase('document','CUAgent Document','CUAgent C0 document harbor-729.',
                       (('Document Body','CUAgent C0 document harbor-729.'),),('Save Document','Save')),
})
TASKS = MappingProxyType({**CALCULATORS, **UI_CASES})
