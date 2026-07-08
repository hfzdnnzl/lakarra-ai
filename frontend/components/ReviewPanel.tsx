"use client";

import { useState } from "react";
import { Loader2, ScanSearch } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  ContentAsset,
  ContentReview,
  FidelityReview,
  PerformanceReview,
  ReviewRunResponse,
} from "@/types";

interface ReviewPanelProps {
  contentId: string;
  assets: ContentAsset[];
  reviews: ContentReview[];
  onReviewed: () => Promise<void>;
}

function FidelityCard({ review }: { review: FidelityReview }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge>Plan fidelity</Badge>
        <span className="text-muted-foreground">
          Match {(review.overall_match_score * 100).toFixed(0)}%
        </span>
      </div>
      <p>{review.summary}</p>
      <p>
        <span className="text-muted-foreground">Hook: </span>
        {review.hook_match}
      </p>
      <p>
        <span className="text-muted-foreground">Voiceover: </span>
        {review.voiceover_usage}
      </p>
      {review.scene_notes.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5">
          {review.scene_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
      {review.suggestions.length > 0 ? (
        <div>
          <div className="text-muted-foreground">Suggestions</div>
          <ul className="list-disc space-y-1 pl-5">
            {review.suggestions.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function PerformanceCard({ review }: { review: PerformanceReview }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant="muted">Performance outlook</Badge>
        <span className="text-muted-foreground">
          Hook {(review.hook_strength * 100).toFixed(0)}% · confidence{" "}
          {(review.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <p>{review.summary}</p>
      <p>
        <span className="text-muted-foreground">Pattern: </span>
        {review.pattern_match}
      </p>
      <p>
        <span className="text-muted-foreground">Post when: </span>
        {review.posting_recommendation}
      </p>
      {review.compared_to_past_posts.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5">
          {review.compared_to_past_posts.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ReviewPanel({ contentId, assets, reviews, onReviewed }: ReviewPanelProps) {
  const [running, setRunning] = useState(false);
  const [latest, setLatest] = useState<ReviewRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const latestAsset = assets[0];
  const historicalFidelity = reviews.find((r) => r.review_type === "fidelity");
  const historicalPerformance = reviews.find((r) => r.review_type === "performance");

  const run = async () => {
    if (!latestAsset) return;
    setRunning(true);
    setError(null);
    try {
      const result = await api.runContentReview(contentId, latestAsset.id);
      if (!result.success) {
        setError(result.error ?? "Review failed");
        return;
      }
      setLatest(result);
      await onReviewed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const fidelity = latest?.fidelity ?? (historicalFidelity?.payload as FidelityReview | undefined);
  const performance =
    latest?.performance ?? (historicalPerformance?.payload as PerformanceReview | undefined);

  return (
    <div className="space-y-4">
      <Button
        type="button"
        className="w-full"
        disabled={running || !latestAsset}
        onClick={run}
      >
        {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanSearch className="h-4 w-4" />}
        Run AI review
      </Button>
      {!latestAsset ? (
        <p className="text-xs text-muted-foreground">Upload a video first to run review.</p>
      ) : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {fidelity ? <FidelityCard review={fidelity} /> : null}
      {performance ? <PerformanceCard review={performance} /> : null}
    </div>
  );
}
