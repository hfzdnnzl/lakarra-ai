"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import type { ContentScene } from "@/types";

function SceneRow({ scene, index }: { scene: ContentScene; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const rows: [string, string | null | undefined][] = [
    ["Scene", scene.scene_description],
    ["Camera", scene.camera_direction],
    ["On-screen text", scene.on_screen_text],
    ["Voiceover", scene.voiceover],
    ["Sound effect", scene.sound_effect],
  ];
  return (
    <div className="rounded-md border border-border">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="font-mono text-sm font-medium">
          {scene.start_time} – {scene.end_time} sec
        </span>
        <span className="truncate text-sm text-muted-foreground">{scene.scene_description}</span>
      </button>
      {open ? (
        <dl className="space-y-2 border-t border-border px-4 py-3 text-sm">
          {rows
            .filter(([, value]) => value)
            .map(([label, value]) => (
              <div key={label} className="grid grid-cols-[140px_1fr] gap-2">
                <dt className="text-muted-foreground">{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
        </dl>
      ) : null}
    </div>
  );
}

export function TimelineViewer({ scenes }: { scenes: ContentScene[] }) {
  if (scenes.length === 0) {
    return <p className="text-sm text-muted-foreground">No scenes.</p>;
  }
  return (
    <div className="space-y-2">
      {scenes
        .slice()
        .sort((a, b) => a.sequence_number - b.sequence_number)
        .map((scene, i) => (
          <SceneRow key={scene.id} scene={scene} index={i} />
        ))}
    </div>
  );
}
