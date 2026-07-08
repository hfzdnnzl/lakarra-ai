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
  content_id?: string | null;
  error?: string | null;
  error_type?: string | null;
}

// --- CMS (Phase 2.5) -------------------------------------------------------

export interface ContentScene {
  id: string;
  sequence_number: number;
  start_time: number;
  end_time: number;
  scene_description: string;
  camera_direction: string;
  on_screen_text: string;
  voiceover?: string | null;
  sound_effect?: string | null;
}

export interface ContentSummary {
  id: string;
  title: string;
  category: string;
  status: string;
  confidence_score: number;
  created_at: string;
  updated_at: string;
}

export interface ContentDetail {
  id: string;
  title: string;
  category: string;
  business_goal: string;
  target_audience: string;
  product: string;
  constraints: string[];
  performance_notes?: string | null;
  hook: string;
  duration: number;
  caption: string;
  hashtags: string[];
  cta: string;
  posting_time: string;
  confidence_score: number;
  music_suggestion?: string | null;
  status: string;
  active_version: number;
  created_at: string;
  updated_at: string;
  scenes: ContentScene[];
}

export interface ContentVersion {
  id: string;
  version_number: number;
  hook: string;
  is_active: boolean;
  created_at: string;
  snapshot: Record<string, unknown>;
}

export interface Feedback {
  id: string;
  message: string;
  created_by: string;
  created_at: string;
}

export interface PaginatedContents {
  items: ContentSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const CONTENT_STATUSES = [
  "draft",
  "review",
  "approved",
  "filming",
  "editing",
  "scheduled",
  "posted",
  "analyzed",
  "promoted",
  "archived",
] as const;

export const CONTENT_CATEGORIES = [
  "aesthetic",
  "educational",
  "product_comparison",
  "pov",
  "testimonial",
  "storytelling",
  "behind_the_scenes",
  "trend_adaptation",
] as const;

export interface ContentAsset {
  id: string;
  content_id: string;
  mime_type: string;
  file_size: number;
  original_filename: string;
  created_at: string;
}

export interface FidelityReview {
  overall_match_score: number;
  hook_match: string;
  scene_notes: string[];
  voiceover_usage: string;
  cta_present: boolean;
  suggestions: string[];
  summary: string;
}

export interface PerformanceReview {
  hook_strength: number;
  emotional_triggers: string[];
  pattern_match: string;
  compared_to_past_posts: string[];
  posting_recommendation: string;
  confidence: number;
  summary: string;
}

export interface ContentReview {
  id: string;
  content_id: string;
  asset_id: string | null;
  review_type: "fidelity" | "performance";
  agent: string;
  payload: FidelityReview | PerformanceReview;
  created_at: string;
}

export interface ReviewRunResponse {
  success: boolean;
  fidelity?: FidelityReview | null;
  performance?: PerformanceReview | null;
  error?: string | null;
  error_type?: string | null;
}
