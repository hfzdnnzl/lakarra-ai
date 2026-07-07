"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Loader2, RefreshCw } from "lucide-react";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/StatusBadge";
import { ContentViewer } from "@/components/ContentViewer";
import { VersionHistory } from "@/components/VersionHistory";
import { FeedbackPanel } from "@/components/FeedbackPanel";
import { CONTENT_STATUSES } from "@/types";
import type { ContentDetail, ContentVersion, Feedback } from "@/types";

const selectClass =
  "h-9 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function ContentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [content, setContent] = useState<ContentDetail | null>(null);
  const [versions, setVersions] = useState<ContentVersion[]>([]);
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyVersion, setBusyVersion] = useState<number | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  const load = useCallback(async () => {
    try {
      const [detail, vers, fb] = await Promise.all([
        api.contentDetail(id),
        api.contentVersions(id),
        api.contentFeedback(id),
      ]);
      setContent(detail);
      setVersions(vers);
      setFeedback(fb);
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
      await api.generateContent({
        business_goal: content.business_goal,
        target_audience: content.target_audience,
        product: content.product,
        constraints: [],
        content_id: id,
      });
      await load();
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
