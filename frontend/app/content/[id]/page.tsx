"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Loader2, RefreshCw } from "lucide-react";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/StatusBadge";
import { ContentViewer } from "@/components/ContentViewer";
import { VersionHistory } from "@/components/VersionHistory";
import { FeedbackPanel } from "@/components/FeedbackPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { ReviewPanel } from "@/components/ReviewPanel";
import { CONTENT_STATUSES } from "@/types";
import type {
  ContentAsset,
  ContentDetail,
  ContentReview,
  ContentVersion,
  Feedback,
} from "@/types";

const selectClass =
  "h-9 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function ContentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [content, setContent] = useState<ContentDetail | null>(null);
  const [versions, setVersions] = useState<ContentVersion[]>([]);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [assets, setAssets] = useState<ContentAsset[]>([]);
  const [reviews, setReviews] = useState<ContentReview[]>([]);
  const [performanceNotes, setPerformanceNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyVersion, setBusyVersion] = useState<number | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  const load = useCallback(async () => {
    try {
      const [detail, vers, fb, assetList, reviewList] = await Promise.all([
        api.contentDetail(id),
        api.contentVersions(id),
        api.contentFeedback(id),
        api.contentAssets(id),
        api.contentReviews(id),
      ]);
      setContent(detail);
      setVersions(vers);
      setFeedback(fb);
      setAssets(assetList);
      setReviews(reviewList);
      setPerformanceNotes(detail.performance_notes ?? "");
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const changeStatus = async (status: string) => {
    await api.updateContentStatus(id, status);
    await load();
  };

  const activate = async (version: number) => {
    setBusyVersion(version);
    try {
      await api.activateVersion(id, version);
      await load();
    } finally {
      setBusyVersion(null);
    }
  };

  const regenerate = async () => {
    if (!content) return;
    setRegenerating(true);
    try {
      const response = await api.generateContent({
        business_goal: content.business_goal,
        target_audience: content.target_audience,
        product: content.product,
        constraints: content.constraints ?? [],
        content_id: id,
      });
      if (!response.success) {
        setError(response.error ?? "Regeneration failed.");
        return;
      }
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRegenerating(false);
    }
  };

  const submitFeedback = async (message: string) => {
    setSubmittingFeedback(true);
    try {
      await api.addFeedback(id, message);
      await load();
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const savePerformanceNotes = async () => {
    setSavingNotes(true);
    try {
      await api.updatePerformanceNotes(id, performanceNotes);
      await load();
    } finally {
      setSavingNotes(false);
    }
  };

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!content) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  return (
    <>
      <PageHeader
        title={content.title}
        description={`Version ${content.active_version} · ${content.category}`}
        action={
          <div className="flex items-center gap-2">
            <Link href="/content-library" className="text-sm text-muted-foreground hover:underline">
              ← Library
            </Link>
            <Button onClick={regenerate} disabled={regenerating}>
              {regenerating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Regenerate (new version)
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Overview</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <Field label="Goal" value={content.business_goal} />
              <Field label="Audience" value={content.target_audience} />
              <Field label="Product" value={content.product} />
              <Field
                label="Constraints"
                value={
                  content.constraints?.length
                    ? content.constraints.join("; ")
                    : "(none)"
                }
              />
              <Field label="Category" value={content.category} />
              <Field label="Confidence" value={`${(content.confidence_score * 100).toFixed(0)}%`} />
              <Field label="Created" value={new Date(content.created_at).toLocaleString()} />
              <div>
                <div className="text-muted-foreground">Status</div>
                <div className="mt-1 flex items-center gap-2">
                  <StatusBadge status={content.status} />
                  <select
                    className={selectClass}
                    value={content.status}
                    onChange={(e) => changeStatus(e.target.value)}
                  >
                    {CONTENT_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Content Output</CardTitle>
            </CardHeader>
            <CardContent>
              <ContentViewer content={content} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Upload & Review</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <UploadPanel contentId={id} assets={assets} onUploaded={load} />
              <ReviewPanel
                contentId={id}
                assets={assets}
                reviews={reviews}
                onReviewed={load}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Performance notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="perf-notes">Notes after posting (for future analysis)</Label>
                <Textarea
                  id="perf-notes"
                  value={performanceNotes}
                  onChange={(e) => setPerformanceNotes(e.target.value)}
                  placeholder="e.g. 12k views, strong saves, hook worked well..."
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={savingNotes}
                onClick={savePerformanceNotes}
              >
                {savingNotes ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save notes
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Version History <Badge variant="muted">{versions.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <VersionHistory
                versions={versions}
                onActivate={activate}
                busyVersion={busyVersion}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Feedback</CardTitle>
            </CardHeader>
            <CardContent>
              <FeedbackPanel
                feedback={feedback}
                onSubmit={submitFeedback}
                submitting={submittingFeedback}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-muted-foreground">{label}</div>
      <div className="font-medium">{value}</div>
    </div>
  );
}
