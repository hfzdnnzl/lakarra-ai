"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Pencil,
  RefreshCw,
  Save,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import {
  formatMetricDisplay,
  hasSavedMetrics,
  hmsToSeconds,
  percentToRatio,
  ratioToPercent,
  secondsToHms,
} from "@/lib/metric-format";
import { videoDisplayLabel } from "@/lib/video-label";
import { cn } from "@/lib/utils";
import type { VideoCatalogItem, VideoMetrics } from "@/types";

type Props = {
  video: VideoCatalogItem;
  requiredLabels: Record<string, string>;
  optionalLabels: Record<string, string>;
  onUpdated: () => void;
  expandAll?: boolean;
};

function cloneMetrics(metrics: VideoMetrics) {
  return { ...metrics };
}

export function VideoAnalyticsCard({
  video,
  requiredLabels,
  optionalLabels,
  onUpdated,
  expandAll,
}: Props) {
  const label = videoDisplayLabel(video);
  const [expanded, setExpanded] = useState(
    expandAll ?? !video.metrics.required_complete,
  );
  const [editing, setEditing] = useState(() => !hasSavedMetrics(video.metrics));
  const [form, setForm] = useState(() => cloneMetrics(video.metrics));
  const [watchTimeDisplay, setWatchTimeDisplay] = useState(() =>
    secondsToHms(video.metrics.watch_time),
  );
  const [completionDisplay, setCompletionDisplay] = useState(() =>
    ratioToPercent(video.metrics.completion_rate),
  );
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setForm(cloneMetrics(video.metrics));
    setWatchTimeDisplay(secondsToHms(video.metrics.watch_time));
    setCompletionDisplay(ratioToPercent(video.metrics.completion_rate));
  }, [video.metrics]);

  useEffect(() => {
    resetForm();
    setEditing(!hasSavedMetrics(video.metrics));
  }, [video.metrics, video.video_id, resetForm]);

  useEffect(() => {
    setExpanded(expandAll ?? !video.metrics.required_complete);
  }, [expandAll, video.metrics.required_complete]);

  const setNum = (field: string, value: string) => {
    setForm((prev) => ({
      ...prev,
      [field]: value === "" ? null : Number(value),
    }));
  };

  const cancelEdit = () => {
    resetForm();
    setEditing(false);
    setError(null);
  };

  const saveMetrics = async () => {
    setSaving(true);
    setError(null);
    const watchTimeSeconds = hmsToSeconds(watchTimeDisplay);
    if (watchTimeDisplay.trim() && watchTimeSeconds === null) {
      setError("Total watch time must be in hh:mm:ss format (e.g. 1:23:45).");
      setSaving(false);
      return;
    }
    const completionRatio = percentToRatio(completionDisplay);
    if (completionDisplay.trim() && completionRatio === null) {
      setError("Completion rate must be a valid percentage (e.g. 45 or 45%).");
      setSaving(false);
      return;
    }
    try {
      await api.updateVideoMetrics(video.video_id, {
        views: form.views ?? undefined,
        likes: form.likes ?? undefined,
        comments: form.comments ?? undefined,
        shares: form.shares ?? undefined,
        saves: form.saves ?? undefined,
        reach: form.reach ?? undefined,
        watch_time: watchTimeSeconds ?? undefined,
        average_watch_duration: form.average_watch_duration ?? undefined,
        completion_rate: completionRatio ?? undefined,
        profile_visits: form.profile_visits ?? undefined,
        followers_gained: form.followers_gained ?? undefined,
        link_clicks: form.link_clicks ?? undefined,
        user_notes: form.user_notes ?? undefined,
      });
      setEditing(false);
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

  const renderOptionalField = (field: string, labelText: string, readOnly: boolean) => {
    if (field === "watch_time") {
      return (
        <div key={field} className="space-y-1">
          <Label htmlFor={`${video.video_id}-${field}-opt`}>{labelText}</Label>
          {readOnly ? (
            <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">
              {formatMetricDisplay(field, form.watch_time ?? null)}
            </p>
          ) : (
            <Input
              id={`${video.video_id}-${field}-opt`}
              type="text"
              inputMode="numeric"
              placeholder="0:05:30"
              value={watchTimeDisplay}
              onChange={(e) => setWatchTimeDisplay(e.target.value)}
            />
          )}
        </div>
      );
    }
    if (field === "completion_rate") {
      return (
        <div key={field} className="space-y-1">
          <Label htmlFor={`${video.video_id}-${field}-opt`}>{labelText}</Label>
          {readOnly ? (
            <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">
              {formatMetricDisplay(field, form.completion_rate ?? null)}
            </p>
          ) : (
            <div className="relative">
              <Input
                id={`${video.video_id}-${field}-opt`}
                type="text"
                inputMode="decimal"
                placeholder="45"
                className="pr-8"
                value={completionDisplay}
                onChange={(e) => setCompletionDisplay(e.target.value)}
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                %
              </span>
            </div>
          )}
        </div>
      );
    }
    return (
      <div key={field} className="space-y-1">
        <Label htmlFor={`${video.video_id}-${field}-opt`}>{labelText}</Label>
        {readOnly ? (
          <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">
            {formatMetricDisplay(field, form[field as keyof VideoMetrics] as number | null)}
          </p>
        ) : (
          <Input
            id={`${video.video_id}-${field}-opt`}
            type="number"
            min={0}
            step="1"
            value={form[field as keyof typeof form] ?? ""}
            onChange={(e) => setNum(field, e.target.value)}
          />
        )}
      </div>
    );
  };

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-0.5 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-expanded={expanded}
            aria-label={expanded ? "Collapse metrics" : "Expand metrics"}
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          <div className="min-w-0 flex-1">
            <CardTitle className="line-clamp-2 text-base leading-snug">{label}</CardTitle>
            <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>{video.publish_date || "No date"}</span>
              {video.duration ? <span>{video.duration}s</span> : null}
              {video.is_analyzed ? (
                <Badge variant="success">Analyzed v{video.analysis_version}</Badge>
              ) : (
                <Badge variant="warning">Not analyzed</Badge>
              )}
              {video.metrics.required_complete ? (
                <Badge variant="success">Metrics complete</Badge>
              ) : (
                <Badge variant="destructive">Metrics needed</Badge>
              )}
            </div>
            {!expanded && hasSavedMetrics(video.metrics) ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {formatMetricDisplay("views", video.metrics.views)} views ·{" "}
                {formatMetricDisplay("likes", video.metrics.likes)} likes
              </p>
            ) : null}
          </div>

          <div className="flex shrink-0 gap-2">
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

      {expanded ? (
        <CardContent className={cn("space-y-4 border-t pt-4 text-sm")}>
          {error ? (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-700">
              {error}
            </div>
          ) : null}

          {video.analysis_summary ? (
            <p className="rounded-md bg-muted px-3 py-2 text-muted-foreground">
              {video.analysis_summary}
            </p>
          ) : null}

          {video.caption && video.caption !== label ? (
            <p className="line-clamp-3 text-xs text-muted-foreground">{video.caption}</p>
          ) : null}

          <div className="flex items-center justify-between gap-2">
            <div className="font-medium">Metrics</div>
            {!editing && hasSavedMetrics(form) ? (
              <Button type="button" size="sm" variant="outline" onClick={() => setEditing(true)}>
                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                Edit
              </Button>
            ) : null}
          </div>

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Required · TikTok Studio
            </div>
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              {Object.entries(requiredLabels).map(([field, fieldLabel]) => (
                <div key={field} className="space-y-1">
                  <Label htmlFor={`${video.video_id}-${field}`}>{fieldLabel}</Label>
                  {editing ? (
                    <Input
                      id={`${video.video_id}-${field}`}
                      type="number"
                      min={0}
                      value={form[field as keyof typeof form] ?? ""}
                      onChange={(e) => setNum(field, e.target.value)}
                    />
                  ) : (
                    <p className="rounded-md bg-muted/60 px-3 py-2 text-sm font-medium">
                      {formatMetricDisplay(field, form[field as keyof VideoMetrics] as number | null)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Optional · TikTok Studio
            </div>
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
              {Object.entries(optionalLabels).map(([field, fieldLabel]) =>
                renderOptionalField(field, fieldLabel, !editing),
              )}
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor={`${video.video_id}-notes`}>Notes</Label>
            {editing ? (
              <Textarea
                id={`${video.video_id}-notes`}
                rows={2}
                value={form.user_notes ?? ""}
                onChange={(e) => setForm((prev) => ({ ...prev, user_notes: e.target.value }))}
                placeholder="Context from TikTok Studio, promotions, etc."
              />
            ) : (
              <p className="min-h-[2.5rem] rounded-md bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
                {form.user_notes?.trim() || "—"}
              </p>
            )}
          </div>

          {editing ? (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={saveMetrics} disabled={saving}>
                {saving ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Save metrics
              </Button>
              {hasSavedMetrics(video.metrics) ? (
                <Button type="button" size="sm" variant="outline" onClick={cancelEdit}>
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
