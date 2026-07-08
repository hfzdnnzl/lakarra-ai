export interface AgentInfo {
  name: string;
  role: string;
  description: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  assigned_agent: string | null;
  created_at: string;
}

export interface Report {
  id: string;
  agent: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ContentIdea {
  id: string;
  title: string;
  hook: string;
  caption: string;
  hashtags: string[];
  status: string;
  created_at: string;
}

export interface Approval {
  id: string;
  workflow: string;
  subject: string;
  status: string;
  requested_by: string | null;
  decided_by: string | null;
  created_at: string;
}

export interface AnalyticsSnapshot {
  id: string;
  metric: string;
  value: number;
  dimension: string | null;
  created_at: string;
}

export interface LogEntry {
  id: string;
  level: string;
  source: string;
  message: string;
  created_at: string;
}

export interface WorkflowDefinition {
  name: string;
  description: string;
  steps: string[];
  requires_approval: boolean;
}

export interface WorkflowRun {
  id: string;
  workflow: string;
  status: string;
  steps: { agent: string; status: string }[];
  created_at: string;
}

export interface TimelineScene {
  start: number;
  end: number;
  scene: string;
  camera: string;
  text: string;
  voiceover?: string | null;
  sound_effect?: string | null;
}

export interface GeneratedContent {
  title: string;
  category: string;
  target_audience: string;
  hook: string;
  duration: number;
  timeline: TimelineScene[];
  music_suggestion?: string | null;
  caption: string;
  hashtags: string[];
  cta: string;
  posting_time: string;
  confidence: number;
}

export interface ContentGenerateRequest {
  business_goal: string;
  target_audience: string;
  product: string;
  constraints: string[];
}

export interface ContentGenerateResponse {
  success: boolean;
  data?: GeneratedContent | null;
  error?: string | null;
  error_type?: string | null;
}
