const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let message = `API ${path} failed: ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        const parts = body.detail
          .map((item) => {
            if (typeof item === "string") return item;
            if (item && typeof item === "object" && "msg" in item) {
              return String((item as { msg?: string }).msg ?? "");
            }
            return "";
          })
          .filter(Boolean);
        if (parts.length > 0) message = parts.join("; ");
      }
    } catch {
      // Keep the generic status message when the body is not JSON.
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: API_URL,
  health: () => request<Record<string, string>>("/health"),
  agents: () => request<import("@/types").AgentInfo[]>("/agents"),
  invokeAgent: (name: string) =>
    request(`/agents/${name}/invoke`, {
      method: "POST",
      body: JSON.stringify({ payload: {} }),
    }),
  tasks: () => request<import("@/types").Task[]>("/tasks"),
  reports: () => request<import("@/types").Report[]>("/reports"),
  approvals: () => request<import("@/types").Approval[]>("/approvals"),
  analytics: () => request<import("@/types").AnalyticsSnapshot[]>("/analytics"),
  logs: () => request<import("@/types").LogEntry[]>("/logs"),
  workflows: () => request<import("@/types").WorkflowDefinition[]>("/workflows"),
  workflowHistory: () => request<import("@/types").WorkflowRun[]>("/workflows/history"),
  runWorkflow: (name: string, threadId = "default") =>
    request(`/workflows/${name}/run`, {
      method: "POST",
      body: JSON.stringify({ payload: {}, thread_id: threadId }),
    }),
  approve: (id: string) => request(`/approvals/${id}/approve`, { method: "POST" }),
  reject: (id: string) => request(`/approvals/${id}/reject`, { method: "POST" }),
  generateContent: async (
    body: import("@/types").ContentGenerateRequest & { content_id?: string },
  ): Promise<import("@/types").ContentGenerateResponse> => {
    // Read the body even on non-2xx so we can surface a meaningful error message.
    const res = await fetch(`${API_URL}/content/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    try {
      return (await res.json()) as import("@/types").ContentGenerateResponse;
    } catch {
      return { success: false, error: `Request failed (HTTP ${res.status})` };
    }
  },

  // --- CMS (Phase 2.5) -----------------------------------------------------
  contentLibrary: (params: {
    page?: number;
    page_size?: number;
    search?: string;
    category?: string;
    status?: string;
    sort?: string;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<import("@/types").PaginatedContents>(`/content?${qs.toString()}`);
  },
  contentDetail: (id: string) => request<import("@/types").ContentDetail>(`/content/${id}`),
  contentVersions: (id: string) =>
    request<import("@/types").ContentVersion[]>(`/content/${id}/versions`),
  contentFeedback: (id: string) =>
    request<import("@/types").Feedback[]>(`/content/${id}/feedback`),
  updateContentStatus: (id: string, status: string, comment?: string) =>
    request<import("@/types").ContentDetail>(`/content/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, comment }),
    }),
  activateVersion: (id: string, version: number) =>
    request<import("@/types").ContentDetail>(`/content/${id}/versions/${version}/activate`, {
      method: "POST",
    }),
  addFeedback: (id: string, message: string) =>
    request<import("@/types").Feedback>(`/content/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  uploadContentAsset: async (contentId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/content/${contentId}/assets`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `Upload failed (${res.status})`);
    }
    return res.json() as Promise<import("@/types").ContentAsset>;
  },
  contentAssets: (id: string) =>
    request<import("@/types").ContentAsset[]>(`/content/${id}/assets`),
  contentAssetStreamUrl: (contentId: string, assetId: string) =>
    `${API_URL}/content/${contentId}/assets/${assetId}/stream`,
  runContentReview: (contentId: string, assetId: string) =>
    request<import("@/types").ReviewRunResponse>(
      `/content/${contentId}/review?asset_id=${encodeURIComponent(assetId)}`,
      { method: "POST" },
    ),
  contentReviews: (id: string) =>
    request<import("@/types").ContentReview[]>(`/content/${id}/reviews`),
  updatePerformanceNotes: (id: string, performance_notes: string) =>
    request<import("@/types").ContentDetail>(`/content/${id}/performance-notes`, {
      method: "PATCH",
      body: JSON.stringify({ performance_notes }),
    }),

  // --- Analytics (Phase 3) -------------------------------------------------
  analyticsAccountSettings: () =>
    request<import("@/types").AccountSettings>("/analytics/account/settings"),
  updateAnalyticsAccount: (tiktok_handle: string) =>
    request<import("@/types").AccountSettings>("/analytics/account/settings", {
      method: "PUT",
      body: JSON.stringify({ tiktok_handle }),
    }),
  analyticsOverview: () => request<import("@/types").AccountOverview>("/analytics/overview"),
  analyticsContent: () => request<import("@/types").ContentAnalyticsPage>("/analytics/content"),
  analyticsMetricsReadiness: () =>
    request<import("@/types").MetricsReadiness>("/analytics/metrics/readiness"),
  updateVideoMetrics: (video_id: string, body: Record<string, unknown>) =>
    request<import("@/types").VideoMetrics>(`/analytics/videos/${video_id}/metrics`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  analyzeContent: (
    post_id: string,
    options?: { contentId?: string; contentType?: "VIDEO" | "IMAGE" | "CAROUSEL"; force?: boolean },
  ) =>
    request<import("@/types").AnalysisResponse>(
      `/analytics/content/${post_id}/analyze?force=${options?.force ?? false}`,
      {
        method: "POST",
        body: JSON.stringify({
          content_id: options?.contentId,
          content_type: options?.contentType,
        }),
      },
    ),
  analyzeVideoById: (video_id: string, force = false) =>
    request<import("@/types").AnalysisResponse>(
      `/analytics/videos/${video_id}/analyze?force=${force}`,
      { method: "POST" },
    ),
  uploadAnalyticsVideo: async (video_id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/analytics/videos/${video_id}/upload`, {
      method: "POST",
      body: form,
      cache: "no-store",
    });
    if (!res.ok) {
      let message = `Upload failed: ${res.status}`;
      try {
        const body = (await res.json()) as { detail?: string };
        if (body.detail) message = body.detail;
      } catch {
        /* ignore */
      }
      throw new Error(message);
    }
    return res.json() as Promise<{
      video_id: string;
      original_filename: string;
      mime_type: string;
      file_size: number;
    }>;
  },
  analyticsVideoStreamUrl: (video_id: string) =>
    `${API_URL}/analytics/videos/${video_id}/upload/stream`,
  deleteAnalyticsVideoUpload: (video_id: string) =>
    request<void>(`/analytics/videos/${video_id}/upload`, { method: "DELETE" }),
  analyticsCompetitors: () => request<import("@/types").CompetitorOverview>("/analytics/competitors"),
  analyticsTrends: () =>
    request<{ reports: import("@/types").TrendReportRecord[] }>("/analytics/trends"),
  analyticsReviewQueue: () => request<import("@/types").ReviewQueueItem[]>("/analytics/review-queue"),
  analyticsHistorical: () => request<import("@/types").HistoricalAnalytics>("/analytics/historical"),
  analyzeAccount: () =>
    request<import("@/types").AnalysisResponse>("/analytics/account/analyze", { method: "POST" }),
  analyzeVideo: (video_id: string, content_id?: string) =>
    request<import("@/types").AnalysisResponse>("/analytics/videos/analyze", {
      method: "POST",
      body: JSON.stringify({ video_id, content_id }),
    }),
  analyzeAllVideos: () =>
    request<import("@/types").AnalyzeAllResponse>("/analytics/videos/analyze-all", {
      method: "POST",
    }),
  analyzeCompetitor: (handle: string) =>
    request<import("@/types").AnalysisResponse>("/analytics/competitors/analyze", {
      method: "POST",
      body: JSON.stringify({ handle }),
    }),
  reviewContentAnalytics: (content_id: string) =>
    request<import("@/types").AnalysisResponse>(`/analytics/content/${content_id}/review`, {
      method: "POST",
    }),
  generateTrendReport: (period = "30d") =>
    request<import("@/types").AnalysisResponse>("/analytics/trends/generate", {
      method: "POST",
      body: JSON.stringify({ period }),
    }),
  decideReview: (report_id: string, decision: string, comment?: string) =>
    request<import("@/types").AnalysisResponse>(`/analytics/reviews/${report_id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, comment }),
    }),
};
