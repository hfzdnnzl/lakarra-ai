"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play } from "lucide-react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { AccountOverview, ContentAnalysisRecord } from "@/types";

export default function ContentAnalyticsPage() {
  const [overview, setOverview] = useState<AccountOverview | null>(null);
  const [analyses, setAnalyses] = useState<ContentAnalysisRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.analyticsContent();
      setOverview(data.overview);
      setAnalyses(data.analyses);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyzeAll = async () => {
    setBusy(true);
    try {
      await api.analyzeAllVideos();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Content Analytics"
        description="TikTok video performance, engagement, and quality analysis."
        action={
          <Button onClick={analyzeAll} disabled={busy} size="sm">
            {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Analyze All Videos
          </Button>
        }
      />
      <AnalyticsNav />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {overview ? (
        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Account Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">
                {(overview.account_health_score * 100).toFixed(0)}%
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Growth Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">
                {overview.growth_trends[0]?.followers
                  ? `${Number(overview.growth_trends[0].followers).toLocaleString()} followers`
                  : "—"}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Posting Heatmap</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{Object.keys(overview.posting_heatmap).length} slots</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground">Saved Analyses</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{analyses.length}</div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <h2 className="mb-4 text-lg font-semibold">Video Analyses</h2>
      {analyses.length === 0 ? (
        <p className="text-muted-foreground">
          No video analyses yet. Click &quot;Analyze All Videos&quot; to run the Content Analyst.
        </p>
      ) : (
        <div className="space-y-4">
          {analyses.map((a) => {
            const payload = a.payload as {
              video?: { title?: string; video_id?: string; content_category?: string };
              performance?: { views?: number; likes?: number };
              engagement?: { engagement_rate?: number };
              quality_scores?: { overall_content_health?: { score?: number } };
              summary?: string;
            };
            return (
              <Card key={a.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      {payload.video?.title ?? a.video_id}
                    </CardTitle>
                    <Badge variant="muted">v{a.version}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex flex-wrap gap-4 text-muted-foreground">
                    <span>{payload.performance?.views?.toLocaleString() ?? "—"} views</span>
                    <span>
                      {payload.engagement?.engagement_rate
                        ? `${(payload.engagement.engagement_rate * 100).toFixed(1)}% engagement`
                        : null}
                    </span>
                    <span>
                      Health:{" "}
                      {payload.quality_scores?.overall_content_health?.score
                        ? `${(payload.quality_scores.overall_content_health.score * 100).toFixed(0)}%`
                        : "—"}
                    </span>
                    <Badge>{payload.video?.content_category}</Badge>
                  </div>
                  <p>{payload.summary}</p>
                  <div className="text-xs text-muted-foreground">
                    {new Date(a.created_at).toLocaleString()} · {a.provider}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
