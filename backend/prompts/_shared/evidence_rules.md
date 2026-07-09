## Evidence rules (all analysis passes)

- Every conclusion must explain WHY using observable facts — never generic statements.
- Every `root_cause` and `recommendation` must include at least one `evidence` entry.
- `evidence.source` must be one of: `retention`, `completion_rate`, `watch_duration`, `comments`, `scene`, `script`, `metrics`.
- `evidence.description` must cite a specific observable fact (metric value, comment theme, timestamp, on-screen element).
- `confidence` is `high` only when multiple independent signals agree; `medium` when partially supported; `low` when mainly inferred.
- Do not restate raw metrics without interpretation.
- Do not use decimal scores (0.0–1.0). Use `rating` (excellent/good/average/weak/poor) AND `score` (1–10 integer) with explanation.
- Never generate scripts, captions, or new content.
