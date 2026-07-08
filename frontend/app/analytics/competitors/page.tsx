"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Search } from "lucide-react";

import { AnalyticsNav } from "@/components/AnalyticsNav";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { CompetitorAnalysisRecord, CompetitorOverview } from "@/types";

export default function CompetitorAnalyticsPage() {
  const [data, setData] = useState<CompetitorOverview | null>(null);
  const [handle, setHandle] = useState("paperlesspost");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await api.analyticsCompetitors());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyze = async (h: string) => {
    setBusy(true);
    try {
      await api.analyzeCompetitor(h);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const renderAnalysis = (a: CompetitorAnalysisRecord) => {
    const p = a.payload as {
      summary?: string;
      strengths?: string[];
      weaknesses?: string[];
      opportunities?: string[];
      threats?: string[];
      content_ideas?: string[];
    };
    return (
      <Card key={a.id}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">@{a.handle}</CardTitle>
            <Badge variant="muted">v{a.version}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>{p.summary}</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-1 font-medium text-emerald-700">Strengths</div>
              <ul className="list-inside list-disc text-muted-foreground">
                {p.strengths?.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div>
              <div className="mb-1 font-medium text-amber-700">Weaknesses</div>
              <ul className="list-inside list-disc text-muted-foreground">
                {p.weaknesses?.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div>
              <div className="mb-1 font-medium text-blue-700">Opportunities</div>
              <ul className="list-inside list-disc text-muted-foreground">
                {p.opportunities?.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
            <div>
              <div className="mb-1 font-medium text-red-700">Threats</div>
              <ul className="list-inside list-disc text-muted-foreground">
                {p.threats?.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
          </div>
          {p.content_ideas?.length ? (
            <div>
              <div className="mb-1 font-medium">Suggested Opportunities</div>
              <ul className="list-inside list-disc text-muted-foreground">
                {p.content_ideas.map((s) => <li key={s}>{s}</li>)}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>
    );
  };

  return (
    <>
      <PageHeader
        title="Competitor Analytics"
        description="SWOT analysis and market gap identification for competitor TikTok accounts."
      />
      <AnalyticsNav />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="mb-8 flex gap-2">
        <Input
          value={handle}
          onChange={(e) => setHandle(e.target.value)}
          placeholder="Competitor handle"
          className="max-w-xs"
        />
        <Button onClick={() => analyze(handle)} disabled={busy} size="sm">
          {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
          Analyze
        </Button>
      </div>

      {data ? (
        <>
          <h2 className="mb-4 text-lg font-semibold">Tracked Competitors</h2>
          <div className="mb-8 grid gap-4 md:grid-cols-2">
            {data.competitors.map((c) => (
              <Card key={c.handle}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">@{c.handle}</CardTitle>
                    <Button variant="outline" size="sm" onClick={() => analyze(c.handle)} disabled={busy}>
                      Analyze
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                  <span>{c.follower_count.toLocaleString()} followers</span>
                  <span>{c.average_views.toLocaleString()} avg views</span>
                  <span>{(c.engagement_rate * 100).toFixed(1)}% engagement</span>
                  <span>{c.posting_frequency}</span>
                </CardContent>
              </Card>
            ))}
          </div>

          <h2 className="mb-4 text-lg font-semibold">Latest Analyses</h2>
          {data.latest_analyses.length === 0 ? (
            <p className="text-muted-foreground">No competitor analyses yet.</p>
          ) : (
            <div className="space-y-4">{data.latest_analyses.map(renderAnalysis)}</div>
          )}
        </>
      ) : (
        <p className="text-muted-foreground">Loading…</p>
      )}
    </>
  );
}
