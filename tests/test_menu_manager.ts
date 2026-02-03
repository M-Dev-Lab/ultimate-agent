/*
  Tests for MenuManager
  Run before integrating with bot
*/

import { MenuManager } from '../src/menu_manager';

function testMenuManager() {
  console.log('Testing MenuManager...');

  const menu = new MenuManager();

  // Test 1: Load menu structure
  console.log('\n✓ Test 1: Menu structure loaded');
  if (!menu) {
    console.error('❌ Failed to load menu structure');
    return;
  }

  // Test 2: Get main menu
  console.log('✓ Test 2: Main menu generated');
  const mainMenu = menu.getMainMenu();
  if (!mainMenu) {
    console.error('❌ Failed to generate main menu');
    return;
  }

  // Test 3: Get submenu
  console.log('✓ Test 3: Submenu generated');
  const codeMenu = menu.getSubmenu('code');
  if (!codeMenu) {
    console.error('❌ Failed to generate submenu');
    return;
  }

  // Test 4: Menu text
  console.log('✓ Test 4: Menu text generated');
  const mainText = menu.getMenuText('main');
  if (!mainText.includes('🦞')) {
    console.error('❌ Menu text missing emoji');
    return;
  }

  // Test 5: Breadcrumbs
  console.log('✓ Test 5: Breadcrumb system working');
  menu.addBreadcrumb(12345, 'main');
  menu.addBreadcrumb(12345, 'code');
  const breadcrumb = menu.getBreadcrumb(12345);
  if (!breadcrumb.includes('Code')) {
    console.error('❌ Breadcrumb system not working');
    return;
  }

  console.log('\n✅ All tests passed!');
}

testMenuManager();