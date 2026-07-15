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

// --- Analytics (Phase 3) -----------------------------------------------------

export type ContentType = "VIDEO" | "IMAGE" | "CAROUSEL";

export interface AccountOverview {
  tiktok_handle?: string | null;
  account_configured: boolean;
  live_data_error?: string | null;
  account_health_score: number;
  total_videos: number;
  total_views: number;
  avg_engagement_rate: number;
  recent_videos: Array<{
    video_id: string;
    title: string;
    views: number;
    category: string;
    publish_date: string;
  }>;
  best_performers: Array<{
    video_id: string;
    title: string;
    views: number;
    engagement_rate?: number;
  }>;
  worst_performers: Array<{
    video_id: string;
    title: string;
    views: number;
  }>;
  posting_heatmap: Record<string, number>;
  performance_trends: Array<{
    video_id: string;
    title?: string;
    views: number;
    publish_date: string;
  }>;
  growth_trends: Array<Record<string, unknown>>;
}

export interface AnalysisRecord {
  id: string;
  version: number;
  subject_id: string;
  agent: string;
  provider: string;
  model: string;
  prompt_version: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ContentAnalysisRecord extends AnalysisRecord {
  video_id: string;
}

export interface CompetitorAnalysisRecord extends AnalysisRecord {
  handle: string;
}

export interface TrendReportRecord extends AnalysisRecord {
  period: string;
}

export interface ReviewReportRecord extends AnalysisRecord {
  content_id: string;
  decision: string | null;
  decision_comment: string | null;
  decided_by: string | null;
  decided_at: string | null;
}

export interface CompetitorOverview {
  competitors: Array<{
    handle: string;
    follower_count: number;
    average_views: number;
    engagement_rate: number;
    posting_frequency: string;
  }>;
  latest_analyses: CompetitorAnalysisRecord[];
}

export interface ReviewQueueItem {
  content_id: string;
  title: string;
  category: string;
  status: string;
  confidence_score: number;
  latest_review: ReviewReportRecord | null;
  created_at: string;
  updated_at: string;
}

export interface HistoricalAnalytics {
  content_analyses: ContentAnalysisRecord[];
  competitor_analyses: CompetitorAnalysisRecord[];
  trend_reports: TrendReportRecord[];
  review_reports: ReviewReportRecord[];
  pattern_analyses: AnalysisRecord[];
  metrics_snapshots: AnalyticsSnapshot[];
}

export interface AnalysisResponse {
  success: boolean;
  data?: Record<string, unknown> | null;
  analysis_id?: string | null;
  version?: number | null;
  error?: string | null;
  error_type?: string | null;
  skipped?: boolean;
  skip_reason?: string | null;
}

export interface VideoMetrics {
  video_id: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
  reach?: number | null;
  watch_time?: number | null;
  average_watch_duration?: number | null;
  completion_rate?: number | null;
  photos_viewed?: number | null;
  /** @deprecated Not available on TikTok; kept for backward compat. */
  profile_visits?: number | null;
  followers_gained?: number | null;
  /** @deprecated Not available on TikTok; kept for backward compat. */
  link_clicks?: number | null;
  user_notes?: string | null;
  publish_date?: string | null;
  publish_time?: string | null;
  required_complete: boolean;
  missing_required: string[];
  metrics_priority: string;
}

export interface Evidence {
  source: string;
  description: string;
}

export interface Recommendation {
  text: string;
  evidence: Evidence[];
}

export interface ExecutiveSummary {
  overall_verdict: string;
  confidence: string;
  primary_reason_for_performance: string;
  biggest_strength: string;
  biggest_weakness: string;
  first_priority_action: string;
}

export interface DimensionSummary {
  label: string;
  rating: string;
  score: number;
  confidence: string;
  explanation: string;
}

export interface SceneAnalysis {
  start_timestamp: string;
  end_timestamp: string;
  purpose: string;
  effectiveness: string;
  score: number;
  confidence: string;
  explanation: string;
  recommendations: Recommendation[];
}

export interface RootCause {
  factor: string;
  estimated_impact: string;
  confidence: string;
  explanation: string;
  evidence: Evidence[];
}

export interface PerformanceSignal {
  name: string;
  value: number | null;
  unit: string;
  available: boolean;
  evidence?: Evidence | null;
}

export interface AnalysisInputs {
  metrics: VideoMetrics;
  signals: PerformanceSignal[];
  unavailable_signals: string[];
}

export interface ContentAnalysisSummary {
  content_type: ContentType;
  executive_summary: ExecutiveSummary;
  content_ratings: DimensionSummary[];
  scenes: SceneAnalysis[];
  top_root_causes: RootCause[];
  immediate_improvements: Recommendation[];
  experiments: Recommendation[];
  future_content_ideas: Recommendation[];
  performance_summary: string;
  analysis_inputs?: AnalysisInputs;
  analysis_mode: "full" | "metrics_only";
  visual_provider?: string | null;
}

/** @deprecated Use ContentAnalysisSummary */
export type VideoAnalysisSummary = ContentAnalysisSummary;

export interface VideoUploadInfo {
  id: string;
  original_filename: string;
  mime_type: string;
  position: number;
}

export interface ContentCatalogItem {
  video_id: string;
  content_type: ContentType;
  title: string;
  url: string;
  caption: string;
  publish_date: string;
  publish_time?: string;
  duration: number;
  thumbnail: string;
  is_analyzed: boolean;
  analysis_version: number | null;
  analysis_id: string | null;
  analysis?: ContentAnalysisSummary | null;
  has_media_upload?: boolean;
  has_video_upload?: boolean;
  upload_filename?: string | null;
  uploads?: VideoUploadInfo[];
  metrics: VideoMetrics;
  metrics_priority: string;
  old_analysis_count?: number;
}

/** @deprecated Use ContentCatalogItem */
export type VideoCatalogItem = ContentCatalogItem;

export interface MetricsReadiness {
  ready: boolean;
  total_videos: number;
  complete_videos: number;
  incomplete_videos: Array<{
    video_id: string;
    title: string;
    missing_required: string[];
  }>;
  required_fields: string[];
  optional_fields: string[];
  optional_recommended_for: string[];
}

export interface PaginationInfo {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  sort_by: string;
  sort_order: string;
}

export interface ContentAnalyticsPage {
  overview: AccountOverview;
  readiness: MetricsReadiness;
  videos: VideoCatalogItem[];
  required_field_labels: Record<string, string>;
  optional_field_labels: Record<string, string>;
  video_optional_field_labels: Record<string, string>;
  image_optional_field_labels: Record<string, string>;
  carousel_optional_field_labels: Record<string, string>;
  pagination?: PaginationInfo | null;
}

export interface AnalyzeAllResponse {
  analyzed: AnalysisResponse[];
  skipped_video_ids: string[];
  errors: Array<{ video_id: string; error?: string; error_type?: string }>;
}

export interface AccountSettings {
  tiktok_handle: string | null;
  configured: boolean;
  source: "database" | "environment" | "none";
}
