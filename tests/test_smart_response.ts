/*
  Tests for SmartResponse system
*/

import { SmartResponse } from '../src/smart_response';

function testSmartResponse() {
  console.log('Testing SmartResponse system...');

  const sr = new SmartResponse();

  // Test hooks
  console.log('\n✓ Test 1: Personality hooks');
  const hook = sr.getPersonalityHook('build', true);
  const hasEmoji = ['🦞', '⚡', '🔥', '✅', '🚀'].some(e => hook.includes(e));
  if (!hasEmoji) {
    console.error('❌ Hook missing emoji');
    return;
  }

  // Test context notes
  console.log('✓ Test 2: Context notes');
  const note = sr.getContextNote('build', 'test input');
  if (typeof note !== 'string') {
    console.error('❌ Context note not string');
    return;
  }

  // Test suggestions
  console.log('✓ Test 3: Next step suggestions');
  const suggestions = sr.suggestNextSteps('build', true);
  if (!Array.isArray(suggestions)) {
    console.error('❌ Suggestions not array');
    return;
  }
  if (suggestions.length === 0 || suggestions.length > 4) {
    console.error('❌ Wrong number of suggestions');
    return;
  }

  // Test full response
  console.log('✓ Test 4: Full response generation');
  const { responseText, keyboard } = sr.buildResponse(
    'build',
    true,
    "Test result",
    "test input"
  );
  if (typeof responseText !== 'string' || responseText.length === 0) {
    console.error('❌ Response text invalid');
    return;
  }

  console.log('\n✅ All SmartResponse tests passed!');
}

testSmartResponse();