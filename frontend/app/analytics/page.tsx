"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { AnalyticsSnapshot } from "@/types";

export default function AnalyticsPage() {
  const [snapshots, setSnapshots] = useState<AnalyticsSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .analytics()
      .then(setSnapshots)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <>
      <PageHeader title="Analytics" description="Business metrics collected across agents." />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {snapshots.length === 0 && !error ? (
        <EmptyState message="No analytics captured yet. This will populate as agents record metrics." />
      ) : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {snapshots.map((s) => (
            <Card key={s.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {s.metric}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold">{s.value}</div>
                {s.dimension ? (
                  <div className="text-xs text-muted-foreground">{s.dimension}</div>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
