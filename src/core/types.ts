export interface AgentMessage {
  channel: 'telegram';
  sender: string;
  content: string;
  timestamp: number;
  messageId?: string;
  metadata?: Record<string, any>;
}

export interface AgentResponse {
  content: string;
  channel: string;
  recipient: string;
  messageId?: string;
  metadata?: Record<string, any>;
}

export interface Session {
  id: string;
  userId: string;
  channel: string;
  workspace?: string;
  context: Record<string, any>;
  createdAt: number;
  lastActivity: number;
  isActive: boolean;
}

export interface QwenPatchPlan {
  goal: string;
  tasks: QwenTask[];
  estimatedTime: number;
  model: string;
}

export interface QwenTask {
  id: string;
  type: 'frontend' | 'backend' | 'mobile' | 'testing' | 'deployment';
  agent: string;
  goal: string;
  files: string[];
  dependencies?: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface OpenCodeConfig {
  provider: string;
  models: Record<string, any>;
  agents: Record<string, OpenCodeAgent>;
}

export interface OpenCodeAgent {
  prompt: string;
  model: string;
  tools?: string[];
}