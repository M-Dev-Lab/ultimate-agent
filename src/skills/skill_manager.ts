import * as fs from 'fs/promises';
import * as path from 'path';
import { exec } from 'child_process';

export interface SkillMetadata {
  name: string;
  slug: string;
  category: string;
  description: string;
  installedAt?: Date;
  lastUsed?: Date;
  useCount: number;
  successRate?: number;
  clawhubVersion?: string;
  path: string;
}

export interface SkillInstallationResult {
  success: boolean;
  stdout?: string;
  error?: string;
}

export class SkillManager {
  private skillsDir: string;
  private registryDir: string;
  private dataDir: string;
  private installedSkills: Map<string, SkillMetadata>;
  private skillCache: Map<string, SkillMetadata>;

  constructor(skillsDir?: string) {
    const baseDir = skillsDir || path.join(process.cwd(), 'skills');
    this.skillsDir = baseDir;
    this.registryDir = path.join(baseDir, 'registry');
    this.dataDir = path.join(process.cwd(), 'data', 'skills');
    this.installedSkills = new Map<string, SkillMetadata>();
    this.skillCache = new Map<string, SkillMetadata>();
    
    this.initializeDirectories();
  }

  private async initializeDirectories(): Promise<void> {
    await fs.mkdir(this.skillsDir, { recursive: true });
    await fs.mkdir(this.registryDir, { recursive: true });
    await fs.mkdir(this.dataDir, { recursive: true });
  }

  async loadInstalledSkills(): Promise<void> {
    this.installedSkills.clear();
    
    try {
      const entries = await fs.readdir(this.skillsDir, { withFileTypes: true });
      
      for (const entry of entries) {
        if (entry.isDirectory()) {
          const skillPath = path.join(this.skillsDir, entry.name);
          const skillMdPath = path.join(skillPath, 'SKILL.md');
          
          if (await this.fileExists(skillMdPath)) {
            const metadata = await this.parseSkillMetadata(skillMdPath, entry.name);
            if (metadata) {
              this.installedSkills.set(metadata.slug, metadata);
              this.skillCache.set(metadata.slug, metadata);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error loading installed skills:', error);
    }
  }

  private async parseSkillMetadata(skillMdPath: string, skillName: string): Promise<SkillMetadata | null> {
    try {
      const content = await fs.readFile(skillMdPath, 'utf-8');
      const lines = content.split('\n');
      
      const metadata: Partial<SkillMetadata> = {
        name: skillName,
        slug: skillName.toLowerCase().replace(/\s+/g, '-'),
        path: path.dirname(skillMdPath),
        installedAt: new Date(),
        useCount: 0
      };
      
      let currentSection = '';
      
      for (const line of lines) {
        const trimmedLine = line.trim();
        
        if (trimmedLine.startsWith('#')) {
          currentSection = trimmedLine.replace('#', '').toLowerCase();
          continue;
        }
        
        if (!trimmedLine.includes(':') || !trimmedLine.includes('-')) {
          continue;
        }
        
        const parts = trimmedLine.split(':');
        const key = parts[0].trim().toLowerCase();
        const value = parts.slice(1).join(':').trim();
        
        switch (key) {
          case 'category':
            metadata.category = value;
            break;
          case 'description':
            metadata.description = value;
            break;
          case 'clawhub-version':
            metadata.clawhubVersion = value;
            break;
        }
      }
      
      return metadata as SkillMetadata;
    } catch (error) {
      console.error(`Error parsing ${skillMdPath}:`, error);
      return null;
    }
  }

  async installFromRegistry(skillSlug: string): Promise<SkillInstallationResult> {
    try {
      console.log(`📦 Installing skill: ${skillSlug}...`);
      
      const result = await this.execCommand(
        `npm install ${skillSlug}@latest --save`
      );
      
      if (result.success) {
        console.log(`✅ Skill ${skillSlug} installed successfully`);
        return { success: true, stdout: result.stdout };
      } else {
        return { 
          success: false, 
          stdout: result.stdout, 
          error: result.error 
        };
      }
    } catch (error) {
      console.error(`❌ Failed to install ${skillSlug}:`, error);
      return { 
        success: false, 
        error: (error as Error).message 
      };
    }
  }

  async installLocalSkill(skillPath: string, skillName: string): Promise<SkillInstallationResult> {
    try {
      const targetPath = path.join(this.skillsDir, skillName);
      
      await fs.mkdir(targetPath, { recursive: true });
      
      const sourceFiles = await fs.readdir(skillPath);
      
      for (const file of sourceFiles) {
        const sourceFilePath = path.join(skillPath, file);
        const targetFilePath = path.join(targetPath, file);
        const stat = await fs.stat(sourceFilePath);
        
        if (stat.isDirectory()) {
          await fs.mkdir(targetFilePath, { recursive: true });
          await this.copyDirectory(sourceFilePath, targetFilePath);
        } else {
          await fs.copyFile(sourceFilePath, targetFilePath);
        }
      }
      
      console.log(`✅ Local skill ${skillName} installed successfully`);
      return { success: true, stdout: `Installed ${skillName} from ${skillPath}` };
    } catch (error) {
      console.error(`❌ Failed to install local skill ${skillName}:`, error);
      return { 
        success: false, 
        error: (error as Error).message 
      };
    }
  }

  private async copyDirectory(source: string, target: string): Promise<void> {
    const entries = await fs.readdir(source, { withFileTypes: true });
    
    for (const entry of entries) {
      const srcPath = path.join(source, entry.name);
      const destPath = path.join(target, entry.name);
      const stat = await fs.stat(srcPath);
      
      if (stat.isDirectory()) {
        await fs.mkdir(destPath, { recursive: true });
        await this.copyDirectory(srcPath, destPath);
      } else {
        await fs.copyFile(srcPath, destPath);
      }
    }
  }

  async searchSkills(query: string): Promise<SkillMetadata[]> {
    const queryLower = query.toLowerCase();
    const results: SkillMetadata[] = [];
    
    for (const [slug, skill] of this.installedSkills.entries()) {
      const nameLower = skill.name.toLowerCase();
      const descLower = skill.description.toLowerCase();
      const categoryLower = skill.category.toLowerCase();
      
      if (nameLower.includes(queryLower) || 
          descLower.includes(queryLower) || 
          categoryLower.includes(queryLower)) {
        results.push(skill);
      }
    }
    
    return results;
  }

  listSkillsByCategory(): Record<string, string[]> {
    const categories: Record<string, string[]> = {};
    
    for (const skill of this.installedSkills.values()) {
      const category = skill.category || 'Uncategorized';
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(skill.name);
    }
    
    return categories;
  }

  getSkillInfo(skillSlug: string): SkillMetadata | null {
    return this.installedSkills.get(skillSlug.toLowerCase()) || null;
  }

  async trackSkillUsage(skillSlug: string, success: boolean): Promise<void> {
    const skill = this.installedSkills.get(skillSlug.toLowerCase());
    
    if (skill) {
      skill.useCount = (skill.useCount || 0) + 1;
      
      const currentRate = skill.successRate || 0.5;
      const newRate = currentRate * 0.9 + (success ? 0.1 : -0.1);
      skill.successRate = Math.max(0, Math.min(1, newRate));
      
      skill.lastUsed = new Date();
      this.installedSkills.set(skillSlug.toLowerCase(), skill);
      this.skillCache.set(skillSlug.toLowerCase(), skill);
      
      console.log(`📊 Skill tracked: ${skill.name} (success: ${success})`);
    }
  }

  async uninstallSkill(skillSlug: string): Promise<boolean> {
    const skill = this.installedSkills.get(skillSlug.toLowerCase());
    
    if (!skill) {
      return false;
    }
    
    try {
      await fs.rm(skill.path, { recursive: true, force: true });
      this.installedSkills.delete(skillSlug.toLowerCase());
      this.skillCache.delete(skillSlug.toLowerCase());
      
      console.log(`✅ Skill ${skill.name} uninstalled`);
      return true;
    } catch (error) {
      console.error(`❌ Failed to uninstall ${skillSlug}:`, error);
      return false;
    }
  }

  updateSkill(skillSlug: string): Promise<SkillInstallationResult> {
    return this.installFromRegistry(skillSlug);
  }

  private async execCommand(command: string, cwd?: string): Promise<SkillInstallationResult> {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ 
          success: false, 
          error: 'Command timed out after 60 seconds' 
        });
      }, 60000);
      
      exec(command, { cwd, timeout: 58000 }, (error, stdout, stderr) => {
        clearTimeout(timeout);
        
        if (error) {
          resolve({ 
            success: false, 
            error: error.message || stderr, 
            stdout 
          });
        } else {
          resolve({ 
            success: true, 
            stdout, 
            error: stderr 
          });
        }
      });
    });
  }

  private async fileExists(filePath: string): Promise<boolean> {
    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }
}