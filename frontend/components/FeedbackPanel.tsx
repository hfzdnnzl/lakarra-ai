"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Feedback } from "@/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function FeedbackPanel({
  feedback,
  onSubmit,
  submitting,
}: {
  feedback: Feedback[];
  onSubmit: (message: string) => Promise<void> | void;
  submitting: boolean;
}) {
  const [message, setMessage] = useState("");

  const submit = async () => {
    if (!message.trim()) return;
    await onSubmit(message.trim());
    setMessage("");
  };

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="e.g. Hook is too weak; need more emotional angle"
        />
        <Button size="sm" onClick={submit} disabled={submitting || !message.trim()}>
          Add feedback
        </Button>
      </div>

      {feedback.length === 0 ? (
        <p className="text-sm text-muted-foreground">No feedback yet.</p>
      ) : (
        <ul className="space-y-2">
          {feedback.map((f) => (
            <li key={f.id} className="rounded-md border border-border px-3 py-2 text-sm">
              <p>{f.message}</p>
              <div className="mt-1 text-xs text-muted-foreground">
                {f.created_by} · {formatDate(f.created_at)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
