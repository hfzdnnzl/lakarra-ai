/** Prefer TikTok caption (first line) over generic video id titles. */

export function videoDisplayLabel(video: {
  title: string;
  caption?: string | null;
}): string {
  const caption = video.caption?.trim();
  if (caption) {
    const firstLine = caption.split("\n")[0].trim();
    const line = firstLine || caption;
    return line.length > 120 ? `${line.slice(0, 117)}…` : line;
  }
  const title = video.title?.trim() ?? "";
  if (title && !/^video\s+/i.test(title)) {
    return title.length > 120 ? `${title.slice(0, 117)}…` : title;
  }
  return title || "Untitled video";
}
