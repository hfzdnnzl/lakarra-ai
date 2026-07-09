"use client";

import { useRef, useState } from "react";
import { Loader2, Upload, PlayCircle } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { VideoPreviewOverlay } from "@/components/VideoPreviewOverlay";
import type { ContentAsset } from "@/types";

interface UploadPanelProps {
  contentId: string;
  assets: ContentAsset[];
  onUploaded: () => Promise<void>;
}

export function UploadPanel({ contentId, assets, onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [previewAsset, setPreviewAsset] = useState<ContentAsset | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      await api.uploadContentAsset(contentId, file);
      await onUploaded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
          e.target.value = "";
        }}
      />
      <Button
        type="button"
        variant="outline"
        className="w-full"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
        Upload filmed video
      </Button>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {assets.length > 0 ? (
        <ul className="space-y-2 text-sm">
          {assets.map((asset) => (
            <li
              key={asset.id}
              className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2"
            >
              <span className="truncate">{asset.original_filename}</span>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-8 shrink-0 px-2"
                onClick={() => setPreviewAsset(asset)}
              >
                <PlayCircle className="mr-1 h-4 w-4" />
                Preview
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground">MP4, MOV, or WebM up to 50 MB.</p>
      )}

      {previewAsset ? (
        <VideoPreviewOverlay
          src={api.contentAssetStreamUrl(contentId, previewAsset.id)}
          title={previewAsset.original_filename}
          onClose={() => setPreviewAsset(null)}
        />
      ) : null}
    </div>
  );
}
