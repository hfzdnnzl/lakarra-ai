"use client";

import { useState } from "react";
import { Loader2, RefreshCw, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { VideoCatalogItem } from "@/types";

type Props = {
  video: VideoCatalogItem;
  requiredLabels: Record<string, string>;
  optionalLabels: Record<string, string>;
  onUpdated: () => void;
};

export function VideoAnalyticsCard({
  video,
  requiredLabels,
  optionalLabels,
  onUpdated,
}: Props) {
  const [form, setForm] = useState({ ...video.metrics });
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setNum = (field: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      [field]: value === "" ? null : Number(value),
    }));
  };

  const saveMetrics = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.updateVideoMetrics(video.video_id, {
        views: form.views ?? undefined,
        likes: form.likes ?? undefined,
        comments: form.comments ?? undefined,
        shares: form.shares ?? undefined,
        saves: form.saves ?? undefined,
        reach: form.reach ?? undefined,
        watch_time: form.watch_time ?? undefined,
        average_watch_duration: form.average_watch_duration ?? undefined,
        completion_rate: form.completion_rate ?? undefined,
        profile_visits: form.profile_visits ?? undefined,
        followers_gained: form.followers_gained ?? undefined,
        link_clicks: form.link_clicks ?? undefined,
        user_notes: form.user_notes ?? undefined,
      });
      onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const runAnalysis = async (force: boolean) => {
    setAnalyzing(true);
    setError(null);
    try {
      await api.analyzeVideoById(video.video_id, force);
      onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const showOptional = video.metrics_priority === "high";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base">{video.title}</CardTitle>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>{video.publish_date || "—"}</span>
              <span>{video.duration}s</span>
              {video.is_analyzed ? (
                <Badge variant="success">Analyzed v{video.analysis_version}</Badge>
              ) : (
                <Badge variant="warning">Not analyzed</Badge>
              )}
              {video.metrics_priority === "high" ? (
                <Badge variant="muted">Best/worst — optional metrics recommended</Badge>
              ) : null}
              {video.metrics.required_complete ? (
                <Badge variant="success">Required metrics complete</Badge>
              ) : (
                <Badge variant="destructive">Required metrics incomplete</Badge>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {!video.is_analyzed ? (
              <Button
                size="sm"
                variant="outline"
                disabled={analyzing || !video.metrics.required_complete}
                onClick={() => runAnalysis(false)}
              >
                {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : "Analyze"}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="outline"
                disabled={analyzing || !video.metrics.required_complete}
                onClick={() => runAnalysis(true)}
              >
                {analyzing ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-1 h-4 w-4" />
                )}
                Re-analyze
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-700">
            {error}
          </div>
        ) : null}

        {video.analysis_summary ? (
          <p className="rounded-md bg-muted px-3 py-2 text-muted-foreground">{video.analysis_summary}</p>
        ) : null}

        <div>
          <div className="mb-2 font-medium">Required metrics (from TikTok Studio)</div>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {Object.entries(requiredLabels).map(([field, label]) => (
              <div key={field} className="space-y-1">
                <Label htmlFor={`${video.video_id}-${field}`}>{label}</Label>
                <Input
                  id={`${video.video_id}-${field}`}
                  type="number"
                  min={0}
                  value={form[field as keyof typeof form] ?? ""}
                  onChange={(e) => setNum(field, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>

        {showOptional ? (
          <div>
            <div className="mb-2 font-medium text-muted-foreground">
              Optional metrics (recommended for this best/worst performer)
            </div>
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              {Object.entries(optionalLabels).map(([field, label]) => (
                <div key={field} className="space-y-1">
                  <Label htmlFor={`${video.video_id}-${field}-opt`}>{label}</Label>
                  <Input
                    id={`${video.video_id}-${field}-opt`}
                    type="number"
                    min={0}
                    step={field === "completion_rate" ? "0.01" : "1"}
                    value={form[field as keyof typeof form] ?? ""}
                    onChange={(e) => setNum(field, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="space-y-1">
          <Label htmlFor={`${video.video_id}-notes`}>Notes</Label>
          <Textarea
            id={`${video.video_id}-notes`}
            rows={2}
            value={form.user_notes ?? ""}
            onChange={(e) => setForm((prev) => ({ ...prev, user_notes: e.target.value }))}
            placeholder="Context from TikTok Studio, promotions, etc."
          />
        </div>

        <Button size="sm" onClick={saveMetrics} disabled={saving}>
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save metrics
        </Button>
      </CardContent>
    </Card>
  );
}
