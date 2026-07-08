import { Badge } from "@/components/ui/badge";

type Variant = "default" | "muted" | "success" | "warning" | "destructive";

const STATUS_VARIANT: Record<string, Variant> = {
  draft: "muted",
  review: "warning",
  approved: "success",
  filming: "default",
  editing: "default",
  scheduled: "warning",
  posted: "success",
  analyzed: "default",
  promoted: "success",
  archived: "muted",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={STATUS_VARIANT[status] ?? "muted"}>{status}</Badge>;
}
