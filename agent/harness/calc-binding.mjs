import assert from 'node:assert/strict';

export function calcInput(binding) {
  assert.ok(['calc-selection-v1','calc-input-v1'].includes(binding.protocol));
  const input=binding.protocol==='calc-input-v1';
  if (input) {
    assert.equal(typeof binding.approvedText,'string');
    assert.ok(binding.approvedText.length>0 && Buffer.byteLength(binding.approvedText)<=256);
    assert.ok(['text','decimal'].includes(binding.approvedKind));
  }
  return input;
}

export function calcReady(binding) {
  const input=calcInput(binding);
  return {protocol:binding.protocol,runId:binding.runId,sessionId:binding.sessionId,
    toolNames:[...(input?['vm_calc_commit','vm_calc_input']:[]),'vm_calc_observe','vm_calc_select','vm_calc_stop'],
    ...(input?{approvedText:binding.approvedText,approvedKind:binding.approvedKind}:{})};
}
