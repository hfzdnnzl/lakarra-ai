"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ContentVersion } from "@/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VersionHistory({
  versions,
  onActivate,
  busyVersion,
}: {
  versions: ContentVersion[];
  onActivate: (version: number) => void;
  busyVersion: number | null;
}) {
  if (versions.length === 0) {
    return <p className="text-sm text-muted-foreground">No versions yet.</p>;
  }
  return (
    <div className="space-y-3">
      {versions
        .slice()
        .sort((a, b) => b.version_number - a.version_number)
        .map((v) => (
          <div key={v.id} className="rounded-md border border-border p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold">v{v.version_number}</span>
                {v.is_active ? <Badge variant="success">active</Badge> : null}
              </div>
              <span className="text-xs text-muted-foreground">{formatDate(v.created_at)}</span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Hook: <span className="text-foreground">{v.hook}</span>
            </p>
            {!v.is_active ? (
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => onActivate(v.version_number)}
                disabled={busyVersion === v.version_number}
              >
                Set active / restore
              </Button>
            ) : null}
          </div>
        ))}
    </div>
  );
}
