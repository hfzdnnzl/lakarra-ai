"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Loader2, MessageSquare, X } from "lucide-react";
import Link from "next/link";

import { PageHeader, EmptyState } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { ReviewQueueItem } from "@/types";

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setItems(await api.analyticsReviewQueue());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runReview = async (contentId: string) => {
    setBusyId(contentId);
    try {
      await api.reviewContentAnalytics(contentId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const decide = async (reportId: string, decision: string, contentId: string) => {
    setBusyId(contentId);
    try {
      await api.decideReview(reportId, decision, comments[contentId]);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Review Queue"
        description="Content Creator outputs awaiting Content Analyst review."
      />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState message="No content awaiting review. Items in 'review' or 'approved' status appear here." />
      ) : (
        <div className="space-y-4">
          {items.map((item) => {
            const review = item.latest_review;
            const payload = review?.payload as {
              approval_recommendation?: string;
              confidence_score?: number;
              strengths?: string[];
              weaknesses?: string[];
              suggestions?: string[];
              hook_strength?: { score?: number; explanation?: string };
            } | undefined;

            return (
              <Card key={item.content_id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base">
                        <Link href={`/content/${item.content_id}`} className="hover:underline">
                          {item.title}
                        </Link>
                      </CardTitle>
                      <div className="mt-1 flex gap-2">
                        <Badge variant="muted">{item.category}</Badge>
                        <Badge>{item.status}</Badge>
                        <span className="text-sm text-muted-foreground">
                          Confidence: {(item.confidence_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    {!review ? (
                      <Button
                        size="sm"
                        onClick={() => runReview(item.content_id)}
                        disabled={busyId === item.content_id}
                      >
                        {busyId === item.content_id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : null}
                        Run Review
                      </Button>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {review && payload ? (
                    <>
                      <div className="flex flex-wrap gap-4">
                        <span>
                          Recommendation:{" "}
                          <Badge
                            variant={
                              payload.approval_recommendation === "approve"
                                ? "success"
                                : payload.approval_recommendation === "reject"
                                  ? "destructive"
                                  : "warning"
                            }
                          >
                            {payload.approval_recommendation}
                          </Badge>
                        </span>
                        <span>
                          Analyst confidence:{" "}
                          {payload.confidence_score
                            ? `${(payload.confidence_score * 100).toFixed(0)}%`
                            : "—"}
                        </span>
                        <span>
                          Hook:{" "}
                          {payload.hook_strength?.score
                            ? `${(payload.hook_strength.score * 100).toFixed(0)}%`
                            : "—"}
                        </span>
                      </div>
                      {payload.strengths?.length ? (
                        <div>
                          <div className="font-medium">Strengths</div>
                          <ul className="list-inside list-disc text-muted-foreground">
                            {payload.strengths.map((s) => <li key={s}>{s}</li>)}
                          </ul>
                        </div>
                      ) : null}
                      {payload.weaknesses?.length ? (
                        <div>
                          <div className="font-medium">Weaknesses</div>
                          <ul className="list-inside list-disc text-muted-foreground">
                            {payload.weaknesses.map((s) => <li key={s}>{s}</li>)}
                          </ul>
                        </div>
                      ) : null}
                      {payload.suggestions?.length ? (
                        <div>
                          <div className="font-medium">Suggestions</div>
                          <ul className="list-inside list-disc text-muted-foreground">
                            {payload.suggestions.map((s) => <li key={s}>{s}</li>)}
                          </ul>
                        </div>
                      ) : null}

                      {!review.decision ? (
                        <div className="space-y-2 border-t pt-3">
                          <Textarea
                            placeholder="Optional comment…"
                            value={comments[item.content_id] ?? ""}
                            onChange={(e) =>
                              setComments((prev) => ({
                                ...prev,
                                [item.content_id]: e.target.value,
                              }))
                            }
                            rows={2}
                          />
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="success"
                              disabled={busyId === item.content_id}
                              onClick={() => decide(review.id, "approve", item.content_id)}
                            >
                              <Check className="mr-1 h-4 w-4" /> Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busyId === item.content_id}
                              onClick={() =>
                                decide(review.id, "request_revision", item.content_id)
                              }
                            >
                              <MessageSquare className="mr-1 h-4 w-4" /> Request Revision
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={busyId === item.content_id}
                              onClick={() => decide(review.id, "reject", item.content_id)}
                            >
                              <X className="mr-1 h-4 w-4" /> Reject
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="text-muted-foreground">
                          Decision: <Badge>{review.decision}</Badge>
                          {review.decision_comment ? ` — ${review.decision_comment}` : null}
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-muted-foreground">No analyst review yet.</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
