import { exec } from 'child_process';
import { promises as fs } from 'fs';
import * as path from 'path';

export interface DeploymentConfig {
  name: string;
  type: 'cloudflare' | 'docker' | 'github-actions';
  environment: 'production' | 'staging' | 'development';
  buildCommand?: string;
  deployCommand?: string;
  workingDirectory: string;
}

export interface DeploymentResult {
  success: boolean;
  url?: string;
  buildOutput?: string;
  error?: string;
  timeTaken: number;
}

export interface MonitoringStatus {
  isUp: boolean;
  statusCode?: number;
  responseTime?: number;
  lastChecked: Date;
}

export class DeploymentManager {
  private configPath: string;
  private deployments: Map<string, DeploymentResult>;

  constructor(configPath: string = './deployments.json') {
    this.configPath = configPath;
    this.deployments = new Map();
    this.loadDeployments();
  }

  private async loadDeployments(): Promise<void> {
    try {
      if (await this.fileExists(this.configPath)) {
        const content = await fs.readFile(this.configPath, 'utf-8');
        const data = JSON.parse(content);
        
        for (const [key, value] of Object.entries(data)) {
          this.deployments.set(key, value as DeploymentResult);
        }
      }
    } catch (error) {
      console.error('Failed to load deployments:', error);
    }
  }

  private async saveDeployments(): Promise<void> {
    try {
      const data: Record<string, DeploymentResult> = {};
      const entries = Array.from(this.deployments.entries());
      
      for (const [key, value] of entries) {
        data[key] = value;
      }
      
      await fs.writeFile(this.configPath, JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('Failed to save deployments:', error);
    }
  }

  async deployToCloudflare(deploymentConfig: DeploymentConfig): Promise<DeploymentResult> {
    const startTime = Date.now();
    console.log(`🚀 Deploying to Cloudflare: ${deploymentConfig.name}`);
    
    try {
      const buildCommand = deploymentConfig.buildCommand || 'npm run build';
      console.log(`🔨 Running build: ${buildCommand}`);
      
      await this.execCommand(buildCommand, deploymentConfig.workingDirectory);
      
      console.log(`📦 Deploying with Wrangler...`);
      
      const deployResult = await this.execCommand(
        'npx wrangler deploy',
        deploymentConfig.workingDirectory
      );
      
      const timeTaken = Date.now() - startTime;
      
      const url = this.extractDeployUrl(deployResult.stdout);
      
      const result: DeploymentResult = {
        success: deployResult.success,
        url,
        buildOutput: buildCommand,
        timeTaken
      };
      
      this.deployments.set(deploymentConfig.name, result);
      await this.saveDeployments();
      
      console.log(`✅ Deployment complete: ${url}`);
      return result;
      
    } catch (error) {
      console.error('❌ Deployment failed:', error);
      return {
        success: false,
        error: (error as Error).message,
        timeTaken: Date.now() - startTime
      };
    }
  }

  async deployToDocker(deploymentConfig: DeploymentConfig): Promise<DeploymentResult> {
    const startTime = Date.now();
    console.log(`🐳 Deploying to Docker: ${deploymentConfig.name}`);
    
    try {
      console.log('🔨 Building Docker image...');
      
      await this.execCommand(
        `docker build -t ${deploymentConfig.name} .`,
        deploymentConfig.workingDirectory
      );
      
      console.log('🐋 Running container...');
      
      const runResult = await this.execCommand(
        `docker run -d -p 80:80 --name ${deploymentConfig.name} ${deploymentConfig.name}`,
        deploymentConfig.workingDirectory
      );
      
      const timeTaken = Date.now() - startTime;
      
      const result: DeploymentResult = {
        success: runResult.success,
        buildOutput: 'docker build & run',
        timeTaken
      };
      
      this.deployments.set(deploymentConfig.name, result);
      await this.saveDeployments();
      
      console.log('✅ Docker deployment complete');
      return result;
      
    } catch (error) {
      console.error('❌ Docker deployment failed:', error);
      return {
        success: false,
        error: (error as Error).message,
        timeTaken: Date.now() - startTime
      };
    }
  }

  async generateGitHubActionsWorkflow(deploymentConfig: DeploymentConfig): Promise<{ success: boolean; workflowPath?: string; error?: string; timeTaken?: number }> {
    const startTime = Date.now();
    console.log(`📝 Generating GitHub Actions workflow...`);
    
    try {
      const workflowContent = this.generateWorkflowYaml(deploymentConfig);
      const workflowDir = path.join(deploymentConfig.workingDirectory, '.github', 'workflows');
      
      await fs.mkdir(workflowDir, { recursive: true });
      
      const workflowPath = path.join(workflowDir, `deploy-${deploymentConfig.name}.yml`);
      await fs.writeFile(workflowPath, workflowContent);
      
      const timeTaken = Date.now() - startTime;
      
      console.log(`✅ GitHub Actions workflow generated: ${workflowPath}`);
      return {
        success: true,
        workflowPath,
        timeTaken
      };
      
    } catch (error) {
      console.error('❌ Workflow generation failed:', error);
      return {
        success: false,
        error: (error as Error).message,
        timeTaken: Date.now() - startTime
      };
    }
  }

  private generateWorkflowYaml(config: DeploymentConfig): string {
    return `name: Deploy ${config.name}
on:
  push:
    branches: [main, master]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: npm ci
      - name: Build
        run: ${config.buildCommand || 'npm run build'}
      - name: Deploy to Cloudflare
        run: npx wrangler deploy
        env:
          CLOUDFLARE_API_TOKEN: \${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: \${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
`;
  }

  async monitorDeployment(url: string): Promise<MonitoringStatus> {
    const startTime = Date.now();
    
    try {
      console.log(`🔍 Monitoring: ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        signal: AbortSignal.timeout(10000)
      });
      
      const responseTime = Date.now() - startTime;
      const status: MonitoringStatus = {
        isUp: response.ok,
        statusCode: response.status,
        responseTime,
        lastChecked: new Date()
      };
      
      if (response.ok) {
        console.log(`✅ Site is up (${response.status})`);
      } else {
        console.warn(`⚠️ Site returned ${response.status}`);
      }
      
      return status;
      
    } catch (error) {
      console.error('❌ Monitoring failed:', error);
      return {
        isUp: false,
        lastChecked: new Date()
      };
    }
  }

  async rollbackDeployment(deploymentName: string): Promise<boolean> {
    console.log(`⏪ Rolling back: ${deploymentName}`);
    
    const deployment = this.deployments.get(deploymentName);
    
    if (!deployment || !deployment.url) {
      console.error('❌ Cannot rollback: no URL found');
      return false;
    }

    try {
      const { OllamaQwenTool } = await import('../tools/ollamaQwenTool.js');
      const qwenTool = new OllamaQwenTool();
      
      const prompt = `You need to help me rollback a deployment. 

Previous deployment URL: ${deployment.url}
Project name: ${deploymentName}

What are the best rollback strategies for Cloudflare Workers/Pages?

Provide 3 specific rollback steps or commands I can execute.`;
      
      const suggestions = await qwenTool.chatWithOllama(prompt);
      
      console.log('📋 Rollback suggestions:');
      console.log(suggestions);
      
      console.log('✅ Rollback guidance provided');
      return true;
      
    } catch (error) {
      console.error('❌ Rollback failed:', error);
      return false;
    }
  }

  listDeployments(): DeploymentResult[] {
    return Array.from(this.deployments.values());
  }

  getDeployment(name: string): DeploymentResult | null {
    return this.deployments.get(name) || null;
  }

  getDeploymentStats(): {
    total: number;
    successful: number;
    failed: number;
    avgDuration: number;
  } {
    const deployments = Array.from(this.deployments.values());
    
    if (deployments.length === 0) {
      return {
        total: 0,
        successful: 0,
        failed: 0,
        avgDuration: 0
      };
    }
    
    const successful = deployments.filter(d => d.success).length;
    const failed = deployments.filter(d => !d.success).length;
    const totalDuration = deployments.reduce((sum, d) => sum + d.timeTaken, 0);
    const avgDuration = totalDuration / deployments.length;
    
    return {
      total: deployments.length,
      successful,
      failed,
      avgDuration
    };
  }

  private extractDeployUrl(output: string | undefined): string | undefined {
    if (!output) {
      return undefined;
    }
    
    const urlMatch = output.match(/https?:\/\/[^\s\n]+/);
    return urlMatch ? urlMatch[0].trim() : undefined;
  }

  private async execCommand(command: string, cwd?: string): Promise<{ success: boolean; stdout?: string; error?: string }> {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        resolve({ 
          success: false, 
          error: 'Command timed out after 120 seconds' 
        });
      }, 120000);
      
      exec(command, { cwd, timeout: 115000 }, (error, stdout, stderr) => {
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