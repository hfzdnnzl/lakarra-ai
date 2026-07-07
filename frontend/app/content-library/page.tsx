"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ContentCard } from "@/components/ContentCard";
import { PageHeader, EmptyState } from "@/components/page-header";
import { CONTENT_CATEGORIES, CONTENT_STATUSES } from "@/types";
import type { ContentSummary } from "@/types";

const PAGE_SIZE = 6;
const selectClass =
  "h-9 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function ContentLibraryPage() {
  const [items, setItems] = useState<ContentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.contentLibrary({
        page,
        page_size: PAGE_SIZE,
        search,
        category,
        status,
        sort,
      });
      setItems(res.items);
      setTotal(res.total);
      setPages(res.pages || 1);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [page, search, category, status, sort]);

  useEffect(() => {
    load();
  }, [load]);

  // Reset to first page when filters change.
  useEffect(() => {
    setPage(1);
  }, [search, category, status, sort]);

  return (
    <>
      <PageHeader
        title="Content Library"
        description={`All generated content — ${total} item(s).`}
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search title, goal, hook…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <select className={selectClass} value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {CONTENT_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select className={selectClass} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {CONTENT_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select className={selectClass} value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="-created_at">Newest first</option>
          <option value="created_at">Oldest first</option>
          <option value="-updated_at">Recently updated</option>
        </select>
      </div>

      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {items.length === 0 && !error ? (
        <EmptyState message="No content found. Generate one from the Content Creator page." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => (
            <ContentCard key={c.id} content={c} />
          ))}
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Page {page} of {pages}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page >= pages}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}
