"use client";

import { useState } from "react";
import { Loader2, Sparkles, ChevronDown, ChevronRight } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import type { GeneratedContent, TimelineScene } from "@/types";

function SceneRow({ scene, index }: { scene: TimelineScene; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const rows: [string, string | null | undefined][] = [
    ["Scene", scene.scene],
    ["Camera", scene.camera],
    ["On-screen text", scene.text],
    ["Voiceover", scene.voiceover],
    ["Sound effect", scene.sound_effect],
  ];
  return (
    <div className="rounded-md border border-border">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-muted"
      >
        <div className="flex items-center gap-3">
          {open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          <span className="font-mono text-sm font-medium">
            {scene.start} – {scene.end} sec
          </span>
          <span className="text-sm text-muted-foreground">{scene.scene}</span>
        </div>
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

function Result({ data }: { data: GeneratedContent }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>{data.title}</CardTitle>
            <CardDescription className="mt-1">{data.hook}</CardDescription>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <Badge>{data.category}</Badge>
            <span className="text-xs text-muted-foreground">
              confidence {(data.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div>
            <div className="text-muted-foreground">Duration</div>
            <div className="font-medium">{data.duration}s</div>
          </div>
          <div>
            <div className="text-muted-foreground">Posting time</div>
            <div className="font-medium">{data.posting_time}</div>
          </div>
          <div className="col-span-2">
            <div className="text-muted-foreground">Target audience</div>
            <div className="font-medium">{data.target_audience}</div>
          </div>
        </div>

        <div>
          <div className="mb-2 text-sm font-semibold">Timeline</div>
          <div className="space-y-2">
            {data.timeline.map((scene, i) => (
              <SceneRow key={`${scene.start}-${scene.end}-${i}`} scene={scene} index={i} />
            ))}
          </div>
        </div>

        {data.music_suggestion ? (
          <div className="text-sm">
            <span className="text-muted-foreground">Music: </span>
            {data.music_suggestion}
          </div>
        ) : null}

        <div className="text-sm">
          <div className="text-muted-foreground">Caption</div>
          <p>{data.caption}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {data.hashtags.map((h) => (
            <Badge key={h} variant="muted">
              {h}
            </Badge>
          ))}
        </div>

        <div className="rounded-md bg-accent px-3 py-2 text-sm text-accent-foreground">
          <span className="font-medium">CTA: </span>
          {data.cta}
        </div>
      </CardContent>
    </Card>
  );
}

export default function ContentCreatorPage() {
  const [businessGoal, setBusinessGoal] = useState("Increase engagement");
  const [targetAudience, setTargetAudience] = useState("Malaysian couples aged 23-35");
  const [product, setProduct] = useState("Digital Wedding Invitation");
  const [constraints, setConstraints] = useState("Simple aesthetic\nLess than 15 seconds");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.generateContent({
        business_goal: businessGoal,
        target_audience: targetAudience,
        product,
        constraints: constraints
          .split("\n")
          .map((c) => c.trim())
          .filter(Boolean),
      });
      if (res.success && res.data) {
        setResult(res.data);
      } else {
        setError(`${res.error_type ?? "error"}: ${res.error ?? "Generation failed"}`);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Content Creator"
        description="Turn a business brief into a complete, structured TikTok content plan."
      />

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Brief</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="goal">Business Goal</Label>
              <Textarea
                id="goal"
                value={businessGoal}
                onChange={(e) => setBusinessGoal(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="audience">Target Audience</Label>
              <Input
                id="audience"
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="product">Product</Label>
              <Input id="product" value={product} onChange={(e) => setProduct(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="constraints">Constraints (one per line)</Label>
              <Textarea
                id="constraints"
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
              />
            </div>
            <Button onClick={generate} disabled={loading || !businessGoal.trim()} className="w-full">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate
            </Button>
          </CardContent>
        </Card>

        <div>
          {error ? (
            <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}
          {result ? (
            <Result data={result} />
          ) : !error ? (
            <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
              Enter a brief and click <span className="font-medium">Generate</span> to see a full
              TikTok content plan with an expandable timeline.
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
