#!/usr/bin/env node

/*
  Validation script for menu system implementation
  Run this to check all components are in place
*/

import { existsSync } from 'fs';

function validateImplementation(): void {
  console.log('🔍 Validating implementation...\n');

  const checks: { [key: string]: boolean } = {
    'Menu structure file exists': existsSync('config/menu_structure.json'),
    'MenuManager class exists': existsSync('src/menu_manager.ts'),
    'SmartResponse class exists': existsSync('src/smart_response.ts'),
    'MenuManager tests exist': existsSync('tests/test_menu_manager.ts'),
    'SmartResponse tests exist': existsSync('tests/test_smart_response.ts'),
    'Integration guide exists': existsSync('INTEGRATION_GUIDE.ts.md'),
    'Test plan exists': existsSync('TEST_PLAN.ts.md'),
    'Pre-flight audit exists': existsSync('PRE_FLIGHT_AUDIT.md'),
    'Research document exists': existsSync('RESEARCH.md'),
  };

  let allPassed = true;

  for (const [check, passed] of Object.entries(checks)) {
    const status = passed ? '✅' : '❌';
    console.log(`${status} ${check}`);

    if (!passed) {
      allPassed = false;
    }
  }

  console.log('\n' + '='.repeat(50));

  if (allPassed) {
    console.log('🎉 Implementation complete! Ready to deploy.\n');
    console.log('Next steps:');
    console.log('1. Review INTEGRATION_GUIDE.ts.md');
    console.log('2. Run test files independently');
    console.log('3. Integrate into src/channels/telegram.ts');
    console.log('4. Test with TEST_PLAN.ts.md');
  } else {
    console.log('\n⚠️  Some checks failed. Review above.\n');
    console.log('Required files:');
    for (const [check, passed] of Object.entries(checks)) {
      if (!passed) {
        console.log(`  • ${check}`);
      }
    }
  }

  console.log('\n' + '='.repeat(50));
}

validateImplementation();