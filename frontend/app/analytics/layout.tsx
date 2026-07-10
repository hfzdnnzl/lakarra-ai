import { AnalyticsShell } from "@/components/analytics/AnalyticsShell";

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return <AnalyticsShell>{children}</AnalyticsShell>;
}
