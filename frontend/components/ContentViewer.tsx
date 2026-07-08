import { Badge } from "@/components/ui/badge";
import { TimelineViewer } from "@/components/TimelineViewer";
import {
  VoiceoverScriptPanel,
  voiceoverFromScenes,
} from "@/components/VoiceoverScriptPanel";
import type { ContentDetail } from "@/types";

/** Renders the persisted content output (hook, storyboard timeline, caption...). */
export function ContentViewer({ content }: { content: ContentDetail }) {
  const voiceoverLines = voiceoverFromScenes(content.scenes);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-wide text-muted-foreground">Hook</div>
        <p className="font-medium">{content.hook}</p>
      </div>

      <VoiceoverScriptPanel lines={voiceoverLines} />

      <div>
        <div className="mb-2 text-sm font-semibold">Timeline / Storyboard</div>
        <TimelineViewer scenes={content.scenes} />
      </div>

      {content.music_suggestion ? (
        <div className="text-sm">
          <span className="text-muted-foreground">Music: </span>
          {content.music_suggestion}
        </div>
      ) : null}

      <div className="text-sm">
        <div className="text-muted-foreground">Caption</div>
        <p>{content.caption}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {content.hashtags.map((h) => (
          <Badge key={h} variant="muted">
            {h}
          </Badge>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
        <div>
          <div className="text-muted-foreground">Duration</div>
          <div className="font-medium">{content.duration}s</div>
        </div>
        <div>
          <div className="text-muted-foreground">Posting time</div>
          <div className="font-medium">{content.posting_time}</div>
        </div>
        <div>
          <div className="text-muted-foreground">CTA</div>
          <div className="font-medium">{content.cta}</div>
        </div>
      </div>
    </div>
  );
}
