"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { Approval } from "@/types";

const variant: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  approved: "success",
  pending: "warning",
  rejected: "destructive",
};

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setApprovals(await api.approvals());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (id: string, action: "approve" | "reject") => {
    setBusy(id);
    try {
      if (action === "approve") await api.approve(id);
      else await api.reject(id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Approval Queue"
        description="Workflows that require human approval: Pending → Approved / Rejected."
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {approvals.length === 0 && !error ? (
        <EmptyState message="No approvals in the queue. Run the content pipeline workflow to create one." />
      ) : (
        <div className="space-y-3">
          {approvals.map((a) => (
            <Card key={a.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{a.subject}</CardTitle>
                  <Badge variant={variant[a.status] ?? "muted"}>{a.status}</Badge>
                </div>
                <CardDescription>
                  workflow: <code>{a.workflow}</code> · requested by {a.requested_by ?? "—"}
                </CardDescription>
              </CardHeader>
              {a.status === "pending" ? (
                <CardContent className="flex gap-2">
                  <Button
                    variant="success"
                    size="sm"
                    onClick={() => decide(a.id, "approve")}
                    disabled={busy === a.id}
                  >
                    Approve
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => decide(a.id, "reject")}
                    disabled={busy === a.id}
                  >
                    Reject
                  </Button>
                </CardContent>
              ) : null}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
