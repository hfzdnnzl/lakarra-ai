import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { cn } from "@/lib/utils";
import type { ContentSummary } from "@/types";

function formatDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const isToday = d.toDateString() === today.toDateString();
  if (isToday) return "Today";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function ContentCard({ content }: { content: ContentSummary }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base">{content.title}</CardTitle>
          <StatusBadge status={content.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="muted">{content.category}</Badge>
          <span>confidence {(content.confidence_score * 100).toFixed(0)}%</span>
          <span>· {formatDate(content.created_at)}</span>
        </div>
        <Link
          href={`/content/${content.id}`}
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          View Details
        </Link>
      </CardContent>
    </Card>
  );
}
