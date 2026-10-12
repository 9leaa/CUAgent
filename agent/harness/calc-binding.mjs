import assert from 'node:assert/strict';

export function calcInput(binding) {
  assert.ok(['calc-selection-v1','calc-input-v1','calc-save-v1'].includes(binding.protocol));
  const input=binding.protocol!=='calc-selection-v1';
  if (Object.hasOwn(binding,'activationApproved')) {
    assert.ok(input);
    assert.equal(binding.activationApproved,true);
  }
  if (input) {
    assert.equal(typeof binding.approvedText,'string');
    assert.ok(binding.approvedText.length>0 && Buffer.byteLength(binding.approvedText)<=256);
    assert.ok(['text','decimal'].includes(binding.approvedKind));
  }
  return input;
}

export function calcPreset(binding) {
  const input=calcInput(binding);
  return binding.protocol==='calc-save-v1'?'calc-save':input?'calc-input':'calc-selection';
}

export function calcReady(binding) {
  const input=calcInput(binding);
  return {protocol:binding.protocol,runId:binding.runId,sessionId:binding.sessionId,
    toolNames:[...(binding.activationApproved?['vm_calc_activate']:[]),...(input?['vm_calc_commit','vm_calc_focus','vm_calc_input']:[]),'vm_calc_observe',...(binding.protocol==='calc-save-v1'?['vm_calc_open_save']:[]),'vm_calc_select','vm_calc_stop'],
    ...(binding.activationApproved?{activationApproved:true}:{}),
    ...(input?{approvedText:binding.approvedText,approvedKind:binding.approvedKind}:{})};
}
