"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader, EmptyState } from "@/components/page-header";
import type { Task } from "@/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .tasks()
      .then(setTasks)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <>
      <PageHeader title="Tasks" description="Work items created and assigned by agents." />
      {error ? (
        <div className="mb-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {tasks.length === 0 && !error ? (
        <EmptyState message="No tasks yet. Run the morning workflow to generate assignments." />
      ) : (
        <div className="space-y-3">
          {tasks.map((t) => (
            <Card key={t.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <div className="font-medium">{t.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {t.assigned_agent ? `assigned to ${t.assigned_agent}` : "unassigned"}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Badge variant="muted">{t.priority}</Badge>
                  <Badge>{t.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
