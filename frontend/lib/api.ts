const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
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
  content: () => request<import("@/types").ContentIdea[]>("/content"),
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
    body: import("@/types").ContentGenerateRequest,
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
};
