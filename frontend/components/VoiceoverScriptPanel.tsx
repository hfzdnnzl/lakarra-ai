"use client";

import { useMemo, useState } from "react";
import { Copy, Mic } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface VoiceoverLine {
  start: number;
  end: number;
  text: string;
}

interface VoiceoverScriptPanelProps {
  lines: VoiceoverLine[];
  className?: string;
}

function formatScript(lines: VoiceoverLine[]): string {
  return lines.map((line) => `[${line.start}–${line.end}s] ${line.text}`).join("\n\n");
}

function speakingSeconds(lines: VoiceoverLine[]): number {
  return lines.reduce((total, line) => total + Math.max(0, line.end - line.start), 0);
}

export function VoiceoverScriptPanel({ lines, className }: VoiceoverScriptPanelProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const script = useMemo(() => formatScript(lines), [lines]);
  const duration = useMemo(() => speakingSeconds(lines), [lines]);

  if (lines.length === 0) return null;

  const copy = async () => {
    await navigator.clipboard.writeText(script);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={className}>
      <Button type="button" variant="outline" size="sm" onClick={() => setOpen((v) => !v)}>
        <Mic className="h-4 w-4" />
        Voiceover script
      </Button>

      {open ? (
        <div className="mt-3 rounded-lg border border-border bg-muted/40 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="text-sm text-muted-foreground">
              {lines.length} line{lines.length === 1 ? "" : "s"} · ~{duration}s speaking time
            </div>
            <Button type="button" variant="outline" size="sm" onClick={copy}>
              <Copy className="h-4 w-4" />
              {copied ? "Copied" : "Copy script"}
            </Button>
          </div>
          <div className="space-y-4 text-base leading-relaxed">
            {lines.map((line) => (
              <p key={`${line.start}-${line.end}-${line.text}`}>
                <span className="font-mono text-sm text-muted-foreground">
                  [{line.start}–{line.end}s]
                </span>{" "}
                {line.text}
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function voiceoverFromTimeline(
  timeline: { start: number; end: number; voiceover?: string | null }[],
): VoiceoverLine[] {
  return timeline
    .filter((scene) => scene.voiceover && scene.voiceover.trim())
    .map((scene) => ({
      start: scene.start,
      end: scene.end,
      text: scene.voiceover!.trim(),
    }));
}

export function voiceoverFromScenes(
  scenes: {
    start_time: number;
    end_time: number;
    voiceover?: string | null;
  }[],
): VoiceoverLine[] {
  return scenes
    .filter((scene) => scene.voiceover && scene.voiceover.trim())
    .map((scene) => ({
      start: scene.start_time,
      end: scene.end_time,
      text: scene.voiceover!.trim(),
    }));
}
