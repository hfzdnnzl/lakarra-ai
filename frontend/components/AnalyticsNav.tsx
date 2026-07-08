"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FileText,
  GitCompare,
  LayoutDashboard,
  ListChecks,
  TrendingUp,
} from "lucide-react";

import { cn } from "@/lib/utils";

const tabs = [
  { href: "/analytics", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/analytics/content", label: "Content Analytics", icon: BarChart3 },
  { href: "/analytics/competitors", label: "Competitors", icon: GitCompare },
  { href: "/analytics/trends", label: "Trend Reports", icon: TrendingUp },
  { href: "/analytics/review-queue", label: "Review Queue", icon: ListChecks },
  { href: "/analytics/reports", label: "Historical Reports", icon: FileText },
];

export function AnalyticsNav() {
  const pathname = usePathname();

  return (
    <nav className="mb-8 flex flex-wrap gap-2 border-b border-border pb-4">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = tab.exact ? pathname === tab.href : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
