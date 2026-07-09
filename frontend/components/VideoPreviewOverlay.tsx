"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

type Props = {
  src: string;
  title?: string;
  onClose: () => void;
};

export function VideoPreviewOverlay({ src, title, onClose }: Props) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title ? `Preview: ${title}` : "Video preview"}
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-black/50 p-2 text-white hover:bg-black/70"
        aria-label="Close preview"
      >
        <X className="h-5 w-5" />
      </button>

      <div
        className="relative flex max-h-[90vh] w-full max-w-4xl flex-col items-center"
        onClick={(e) => e.stopPropagation()}
      >
        {title ? (
          <p className="mb-3 max-w-full truncate text-sm text-white/80">{title}</p>
        ) : null}
        <video
          key={src}
          src={src}
          controls
          autoPlay
          playsInline
          className="max-h-[calc(90vh-2rem)] w-full rounded-lg bg-black object-contain shadow-2xl"
        />
      </div>
    </div>
  );
}
