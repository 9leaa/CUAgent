import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sessionStarter} from '../harness/desktop-session-command.mjs';
import {startCalcSession,startHandoffSession,startDesktopSession} from '../harness/desktop-session.mjs';

for(const kind of ['calc-selection','calc-input'])test(`CLI routes ${kind} to strict Calc starter`,()=>{
  assert.equal(sessionStarter(kind),startCalcSession);
});
test('CLI keeps legacy starters separate',()=>{
  assert.equal(sessionStarter('project-handoff'),startHandoffSession);
  assert.equal(sessionStarter(undefined),startDesktopSession);
});
