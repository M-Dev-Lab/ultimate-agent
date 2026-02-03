/*
  Menu Manager for Telegram Bot
  Handles hierarchical menu navigation with breadcrumbs
 */

import { Markup } from 'telegraf';
import { readFileSync } from 'fs';
import { join } from 'path';

interface MenuButton {
  id: string;
  emoji: string;
  label: string;
  description: string;
  callback_data: string;
}

interface MenuConfig {
  id: string;
  title: string;
  parent: string;
  buttons: MenuButton[];
}

interface MenuStructure {
  version: string;
  last_updated: string;
  main_menu: {
    title: string;
    description: string;
    buttons: MenuButton[];
  };
  submenus: {
    [key: string]: MenuConfig;
  };
}

export class MenuManager {
  private configPath: string;
  private menuStructure: MenuStructure;
  private navigationHistory: Map<number, string[]> = new Map();

  constructor(configPath = 'config/menu_structure.json') {
    this.configPath = configPath;
    this.menuStructure = this.loadMenuStructure();
  }

  private loadMenuStructure(): MenuStructure {
    try {
      const configContent = readFileSync(this.configPath, 'utf-8');
      return JSON.parse(configContent) as MenuStructure;
    } catch (error) {
      console.error('Error loading menu structure:', error);
      throw error;
    }
  }

  getMainMenu() {
    const menuConfig = this.menuStructure.main_menu;
    const buttons = menuConfig.buttons;

    const keyboard: ReturnType<typeof Markup.inlineKeyboard> | null = Markup.inlineKeyboard(
      buttons.map(btn => [
        Markup.button.callback(`${btn.emoji} ${btn.label}`, btn.callback_data)
      ])
    );

    return keyboard;
  }

  getSubmenu(submenuId: string) {
    if (!(submenuId in this.menuStructure.submenus)) {
      return null;
    }

    const menuConfig = this.menuStructure.submenus[submenuId];
    const buttons = menuConfig.buttons;

    const keyboard: ReturnType<typeof Markup.inlineKeyboard> | null = Markup.inlineKeyboard(
      buttons.map(btn => [
        Markup.button.callback(`${btn.emoji} ${btn.label}`, btn.callback_data)
      ])
    );

    return keyboard;
  }

  getMenuText(menuId: string = 'main'): string {
    if (menuId === 'main') {
      const config = this.menuStructure.main_menu;
      return `${config.title}\n\n${config.description}`;
    } else if (menuId in this.menuStructure.submenus) {
      const config = this.menuStructure.submenus[menuId];
      return `${config.title}\n\nSelect an action:`;
    } else {
      return 'Menu not found';
    }
  }

  addBreadcrumb(userId: number, menuId: string): void {
    if (!this.navigationHistory.has(userId)) {
      this.navigationHistory.set(userId, []);
    }

    const history = this.navigationHistory.get(userId)!;
    history.push(menuId);

    // Keep only last 5 menus
    if (history.length > 5) {
      history.shift();
    }

    this.navigationHistory.set(userId, history);
  }

  getBreadcrumb(userId: number): string {
    if (!this.navigationHistory.has(userId) || this.navigationHistory.get(userId)!.length === 0) {
      return 'Main';
    }

    const history = this.navigationHistory.get(userId)!;
    const breadcrumbParts: string[] = [];

    for (const menuId of history) {
      if (menuId === 'main') {
        breadcrumbParts.push('Main');
      } else if (menuId in this.menuStructure.submenus) {
        const title = this.menuStructure.submenus[menuId].title;
        // Remove emoji from title and " Menu" suffix, then capitalize first letter
        const cleanTitle = title.split(' ')[1]?.replace(' Menu', '') || menuId;
        // Capitalize first letter for better display
        const capitalizedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1).toLowerCase();
        breadcrumbParts.push(capitalizedTitle);
      }
    }

    return breadcrumbParts.slice(-3).join(' > '); // Last 3 levels
  }

  clearHistory(userId: number): void {
    this.navigationHistory.delete(userId);
  }
}

// Example usage:
if (import.meta.url === `file://${process.argv[1]}`) {
  const menu = new MenuManager();
  
  console.log('Main Menu:');
  console.log(menu.getMenuText('main'));
  console.log(menu.getMainMenu());
  
  console.log('\nCode Menu:');
  console.log(menu.getMenuText('code'));
  console.log(menu.getSubmenu('code'));
}