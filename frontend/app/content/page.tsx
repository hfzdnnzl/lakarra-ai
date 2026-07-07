import { redirect } from "next/navigation";

// The memory-based "Content Ideas" list is superseded by the persistent Content
// Library (Phase 2.5). Redirect to keep any old links working.
export default function ContentIdeasRedirect() {
  redirect("/content-library");
}
