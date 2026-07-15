"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Pencil,
  PlayCircle,
  RefreshCw,
  RotateCcw,
  Save,
  Upload,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { VideoPreviewOverlay } from "@/components/VideoPreviewOverlay";
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
import type { ContentCatalogItem, VideoMetrics } from "@/types";

type Props = {
  video: ContentCatalogItem;
  requiredLabels: Record<string, string>;
  optionalLabels: Record<string, string>;
  onUpdated: () => void;
  expandAll?: boolean;
};

function cloneMetrics(metrics: VideoMetrics) {
  return { ...metrics };
}

function formatPostedAt(date: string, time?: string | null) {
  const d = date.trim();
  const t = time?.trim() ?? "";
  if (d && t) return `${d} ${t}`;
  if (d) return d;
  if (t) return t;
  return "No date";
}

function metricInputValue(metrics: VideoMetrics, field: string): string | number {
  const value = metrics[field as keyof VideoMetrics];
  return typeof value === "number" ? value : "";
}

function metricDisplayValue(metrics: VideoMetrics, field: string): number | null {
  const value = metrics[field as keyof VideoMetrics];
  return typeof value === "number" ? value : null;
}

function formatRating(rating: string) {
  return rating.charAt(0).toUpperCase() + rating.slice(1);
}

const analysisMetricFields = [
  "views",
  "likes",
  "comments",
  "shares",
  "saves",
  "reach",
  "watch_time",
  "average_watch_duration",
  "completion_rate",
  "photos_viewed",
  "followers_gained",
] as const;

function EvidenceList({ items }: { items: { source: string; description: string }[] }) {
  if (!items.length) return null;
  return (
    <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
      {items.map((item) => (
        <li key={`${item.source}-${item.description}`}>
          <span className="font-medium text-foreground/80">{item.source}:</span> {item.description}
        </li>
      ))}
    </ul>
  );
}

export function VideoAnalyticsCard({
  video,
  requiredLabels,
  optionalLabels,
  onUpdated,
  expandAll,
}: Props) {
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const label = videoDisplayLabel(video);
  const isImage = video.content_type === "IMAGE";
  const isCarousel = video.content_type === "CAROUSEL";
  const isImageOrCarousel = isImage || isCarousel;
  const hasUpload = video.has_media_upload ?? video.has_video_upload ?? false;
  const analysisInputs = video.analysis?.analysis_inputs;
  const analysisMetrics = analysisInputs?.metrics;
  const analysisSignals = Array.isArray(analysisInputs?.signals) ? analysisInputs.signals : [];
  const unavailableSignals = Array.isArray(analysisInputs?.unavailable_signals)
    ? analysisInputs.unavailable_signals
    : [];
  const [expanded, setExpanded] = useState(expandAll ?? false);
  const [editing, setEditing] = useState(() => !hasSavedMetrics(video.metrics));
  const [form, setForm] = useState(() => cloneMetrics(video.metrics));
  const [publishDateDisplay, setPublishDateDisplay] = useState(() => video.publish_date ?? "");
  const [publishTimeDisplay, setPublishTimeDisplay] = useState(
    () => video.publish_time ?? video.metrics.publish_time ?? "",
  );
  const [watchTimeDisplay, setWatchTimeDisplay] = useState(() =>
    secondsToHms(video.metrics.watch_time),
  );
  const [completionDisplay, setCompletionDisplay] = useState(() =>
    ratioToPercent(video.metrics.completion_rate),
  );
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [pruning, setPruning] = useState(false);
  const [showPruneConfirm, setShowPruneConfirm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setForm(cloneMetrics(video.metrics));
    setPublishDateDisplay(video.publish_date ?? "");
    setPublishTimeDisplay(video.publish_time ?? video.metrics.publish_time ?? "");
    setWatchTimeDisplay(secondsToHms(video.metrics.watch_time));
    setCompletionDisplay(ratioToPercent(video.metrics.completion_rate));
  }, [video.metrics, video.publish_date, video.publish_time]);

  useEffect(() => {
    resetForm();
    setEditing(!hasSavedMetrics(video.metrics));
  }, [video.metrics, video.video_id, resetForm]);

  useEffect(() => {
    setExpanded(expandAll ?? false);
  }, [expandAll]);

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
        publish_date: publishDateDisplay.trim() || null,
        publish_time: publishTimeDisplay.trim() || null,
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

  const uploadVideo = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      await api.uploadAnalyticsVideo(video.video_id, file);
      onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const uploadCarouselImages = async (files: FileList | File[]) => {
    setUploading(true);
    setError(null);
    try {
      await api.uploadAnalyticsCarouselImages(video.video_id, Array.from(files));
      onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const removeUpload = async (upload_id?: string) => {
    setUploading(true);
    setError(null);
    try {
      await api.deleteAnalyticsVideoUpload(video.video_id, upload_id);
      onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const pruneOldVersions = async () => {
    setPruning(true);
    setShowPruneConfirm(false);
    try {
      await api.pruneContentAnalyses(video.video_id);
      onUpdated();
    } catch (e) {
      // Silently handle — the parent loader will show the error if needed.
    } finally {
      setPruning(false);
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
            {formatMetricDisplay(field, metricDisplayValue(form, field))}
          </p>
        ) : (
          <Input
            id={`${video.video_id}-${field}-opt`}
            type="number"
            min={0}
            step="1"
            value={metricInputValue(form, field)}
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
              <span>{formatPostedAt(video.publish_date, video.publish_time)}</span>
              {video.duration ? <span>{video.duration}s</span> : null}
              {video.is_analyzed ? (
                <Badge variant="success">Analyzed v{video.analysis_version}</Badge>
              ) : (
                <Badge variant="warning">Not analyzed</Badge>
              )}
              {video.is_analyzed && video.analysis ? (
                video.analysis.analysis_mode === "full" ? (
                  <Badge variant="success">Full analysis</Badge>
                ) : (
                  <Badge variant="muted">Metrics only</Badge>
                )
              ) : null}
              {hasUpload ? (
                <Badge variant="outline">{isImageOrCarousel ? "Media uploaded" : "Video uploaded"}</Badge>
              ) : null}
              {isImage ? (
                <Badge variant="outline">Image post</Badge>
              ) : null}
              {isCarousel ? (
                <Badge variant="outline">Carousel post</Badge>
              ) : null}
              {video.analysis?.analysis_mode === "full" && video.analysis.visual_provider === "mock" ? (
                <Badge variant="warning">Demo visual analysis</Badge>
              ) : null}
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

          {video.is_analyzed && video.analysis ? (
            <>
              <div className="space-y-2 rounded-md border bg-muted/40 p-3">
                <div className="font-medium">Executive summary</div>
                <p className="text-muted-foreground">{video.analysis.executive_summary.overall_verdict}</p>
                <p className="text-sm">
                  <span className="font-medium text-foreground">Why: </span>
                  {video.analysis.executive_summary.primary_reason_for_performance}
                </p>
                <p className="text-sm">
                  <span className="font-medium text-emerald-800">Strength: </span>
                  {video.analysis.executive_summary.biggest_strength}
                </p>
                <p className="text-sm">
                  <span className="font-medium text-amber-800">Weakness: </span>
                  {video.analysis.executive_summary.biggest_weakness}
                </p>
                <p className="text-sm">
                  <span className="font-medium text-foreground">First action: </span>
                  {video.analysis.executive_summary.first_priority_action}
                </p>
              </div>

              {video.analysis.content_ratings.length > 0 ? (
                <div className="space-y-2 rounded-md border p-3">
                  <div className="font-medium">Content ratings</div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {video.analysis.content_ratings.map((rating) => (
                      <div key={rating.label} className="rounded-md bg-muted/50 px-3 py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium">{rating.label}</span>
                          <span className="text-sm tabular-nums">
                            {formatRating(rating.rating)} · {rating.score}/10
                          </span>
                        </div>
                        {rating.explanation ? (
                          <p className="mt-1 text-xs text-muted-foreground">{rating.explanation}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {video.analysis.scenes.length > 0 ? (
                <div className="space-y-2 rounded-md border p-3">
                  <div className="font-medium">Scene timeline</div>
                  <ul className="space-y-2 text-muted-foreground">
                    {video.analysis.scenes.map((scene) => (
                      <li key={`${scene.start_timestamp}-${scene.end_timestamp}`} className="rounded-md bg-muted/40 px-3 py-2">
                        <div className="font-medium text-foreground">
                          {scene.start_timestamp}–{scene.end_timestamp}: {scene.purpose}
                        </div>
                        <p className="text-xs">
                          {formatRating(scene.effectiveness)} · {scene.score}/10 — {scene.explanation}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {video.analysis.top_root_causes.length > 0 ? (
                <div className="space-y-2 rounded-md border p-3">
                  <div className="font-medium">Root causes</div>
                  <ol className="list-inside list-decimal space-y-2 text-muted-foreground">
                    {video.analysis.top_root_causes.map((cause) => (
                      <li key={cause.factor}>
                        <span className="font-medium text-foreground">{cause.factor}</span>
                        <span className="text-xs uppercase text-muted-foreground">
                          {" "}
                          · {cause.estimated_impact} impact · {cause.confidence} confidence
                        </span>
                        <p className="text-sm">{cause.explanation}</p>
                        <EvidenceList items={cause.evidence} />
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}

              {video.analysis.immediate_improvements.length > 0 ? (
                <div className="space-y-2 rounded-md border border-emerald-200 bg-emerald-50/60 p-3">
                  <div className="font-medium text-emerald-900">Immediate improvements</div>
                  <ul className="space-y-2 text-emerald-900/90">
                    {video.analysis.immediate_improvements.map((item) => (
                      <li key={item.text}>
                        {item.text}
                        <EvidenceList items={item.evidence} />
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {video.analysis.experiments.length > 0 ? (
                <div className="space-y-2 rounded-md border p-3">
                  <div className="font-medium">Experiments to try</div>
                  <ul className="space-y-2 text-muted-foreground">
                    {video.analysis.experiments.map((item) => (
                      <li key={item.text}>
                        {item.text}
                        <EvidenceList items={item.evidence} />
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {video.analysis.future_content_ideas.length > 0 ? (
                <div className="space-y-2 rounded-md border p-3">
                  <div className="font-medium">Future content ideas</div>
                  <ul className="space-y-2 text-muted-foreground">
                    {video.analysis.future_content_ideas.map((item) => (
                      <li key={item.text}>
                        {item.text}
                        <EvidenceList items={item.evidence} />
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {video.analysis.performance_summary ? (
                <details className="rounded-md border p-3">
                  <summary className="cursor-pointer font-medium">Performance facts</summary>
                  <p className="mt-2 text-sm text-muted-foreground">{video.analysis.performance_summary}</p>
                </details>
              ) : null}

              <details className="rounded-md border p-3">
                <summary className="cursor-pointer font-medium">Analysis inputs</summary>
                {analysisInputs ? (
                  <div className="mt-3 space-y-3">
                    <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                      {analysisMetricFields.map((field) => (
                        <div key={field} className="rounded-md bg-muted/40 px-3 py-2">
                          <div className="text-xs text-muted-foreground">{field.replaceAll("_", " ")}</div>
                          <div className="text-sm font-medium">
                            {formatMetricDisplay(field, analysisMetrics?.[field] ?? null)}
                          </div>
                        </div>
                      ))}
                    </div>
                    {analysisSignals.length > 0 ? (
                      <div>
                        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Derived signals
                        </div>
                        <ul className="space-y-2 text-sm">
                          {analysisSignals.map((signal) => (
                            <li key={signal.name}>
                              <span className="font-medium">{signal.name.replaceAll("_", " ")}</span>
                              {signal.value !== null ? `: ${signal.value}` : ": unavailable"}
                              {signal.evidence?.description ? (
                                <p className="text-xs text-muted-foreground">{signal.evidence.description}</p>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {unavailableSignals.length > 0 ? (
                      <p className="text-xs text-muted-foreground">
                        Unavailable: {unavailableSignals.join(", ")}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Detailed analysis inputs are unavailable for this older analysis. Re-analyze
                    the post to capture them.
                  </p>
                )}
              </details>

              {/* Reset old analysis versions */}
              <div className="rounded-md border border-border p-3">
                {showPruneConfirm ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Delete all previous analysis versions for this video, keeping only the latest one?
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={pruning}
                        onClick={pruneOldVersions}
                      >
                        {pruning ? (
                          <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                        ) : null}
                        Delete old versions
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowPruneConfirm(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    {video.old_analysis_count && video.old_analysis_count > 0 ? (
                      <span className="text-xs text-muted-foreground">
                        {video.old_analysis_count} old version{video.old_analysis_count > 1 ? "s" : ""}
                      </span>
                    ) : null}
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!video.old_analysis_count || video.old_analysis_count === 0}
                      onClick={() => setShowPruneConfirm(true)}
                    >
                      <RotateCcw className="mr-1.5 h-4 w-4" />
                      Reset old analyses
                    </Button>
                  </div>
                )}
              </div>
            </>
          ) : null}

          <div className="space-y-2 rounded-md border p-3">
            <div className="font-medium">{isImageOrCarousel ? "Media for analysis" : "Video for analysis"}</div>
            <p className="text-xs text-muted-foreground">
              {isImage
                ? "Upload the posted TikTok image here for full visual analysis."
                : isCarousel
                  ? "Upload all the posted TikTok carousel images here for full visual analysis."
                  : "Upload the posted TikTok video here for full visual analysis."}
            </p>
            <input
              ref={uploadInputRef}
              type="file"
              multiple={isCarousel}
              accept={
                isImageOrCarousel
                  ? "image/jpeg,image/png,image/webp"
                  : "video/mp4,video/quicktime,video/webm,image/jpeg,image/png,image/webp"
              }
              className="hidden"
              onChange={(e) => {
                const files = e.target.files;
                if (!files || files.length === 0) return;
                if (isCarousel && files.length > 1) {
                  void uploadCarouselImages(files);
                } else if (isCarousel) {
                  void uploadVideo(files[0]);
                } else {
                  const file = files[0];
                  if (file) void uploadVideo(file);
                }
                e.target.value = "";
              }}
            />
            {hasUpload && video.uploads && video.uploads.length > 0 ? (
              <div className="space-y-2">
                {video.uploads.map((upload) => (
                  <div key={upload.id} className="flex flex-wrap items-center gap-2 rounded-md bg-muted/40 px-3 py-2">
                    <span className="min-w-0 flex-1 truncate text-sm">{upload.original_filename}</span>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setPreviewOpen(true)}
                    >
                      <PlayCircle className="mr-1.5 h-4 w-4" />
                      Preview
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={uploading}
                      onClick={() => void removeUpload(upload.id)}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                {isCarousel ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={uploading}
                    onClick={() => uploadInputRef.current?.click()}
                  >
                    {uploading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="mr-2 h-4 w-4" />
                    )}
                    Add more images
                  </Button>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={uploading}
                    onClick={() => uploadInputRef.current?.click()}
                  >
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Replace"}
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={uploading}
                  onClick={() => uploadInputRef.current?.click()}
                >
                  {uploading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="mr-2 h-4 w-4" />
                  )}
                  Upload {isCarousel ? "images" : isImage ? "image" : "video"} for analysis
                </Button>
                <p className="text-xs text-muted-foreground">
                  {isImage
                    ? "JPEG, PNG, or WebP up to 50 MB."
                    : isCarousel
                      ? "JPEG, PNG, or WebP up to 50 MB. Select multiple images at once."
                      : "MP4, MOV, WebM, or image formats up to 50 MB."}
                </p>
              </div>
            )}
          </div>

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
              Posted
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor={`${video.video_id}-publish-date`}>Date posted</Label>
                {editing ? (
                  <Input
                    id={`${video.video_id}-publish-date`}
                    type="date"
                    value={publishDateDisplay}
                    onChange={(e) => setPublishDateDisplay(e.target.value)}
                  />
                ) : (
                  <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">
                    {publishDateDisplay || "—"}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor={`${video.video_id}-publish-time`}>Time posted</Label>
                {editing ? (
                  <Input
                    id={`${video.video_id}-publish-time`}
                    type="time"
                    value={publishTimeDisplay}
                    onChange={(e) => setPublishTimeDisplay(e.target.value)}
                  />
                ) : (
                  <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">
                    {publishTimeDisplay || "—"}
                  </p>
                )}
              </div>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Override TikTok auto-detected date and time from TikTok Studio if needed.
            </p>
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
                      value={metricInputValue(form, field)}
                      onChange={(e) => setNum(field, e.target.value)}
                    />
                  ) : (
                    <p className="rounded-md bg-muted/60 px-3 py-2 text-sm font-medium">
                      {formatMetricDisplay(field, metricDisplayValue(form, field))}
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

      {previewOpen && hasUpload ? (
        <VideoPreviewOverlay
          src={api.analyticsVideoStreamUrl(video.video_id)}
          title={video.upload_filename ?? label}
          kind={isImageOrCarousel ? "image" : "video"}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </Card>
  );
}
