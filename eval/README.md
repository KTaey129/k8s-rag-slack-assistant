# Eval question set

`questions.jsonl` — 150 questions (140 grounded in `data/k8s-docs/`, 10 intentionally
out-of-scope), one JSON object per line.

**Schema:** `id` (unique slug, e.g. `wl-001`) · `category` (topic group, e.g.
`"workloads/pods"`, or `"out-of-scope"`) · `question` (phrased as for `/k8s <question>`)
· `expected_sources` (doc paths relative to `data/k8s-docs/`; `[]` for out-of-scope) ·
`reference_answer` (2-4 sentence ground truth grounded in the source doc, or a fixed
refusal string for out-of-scope rows) · `difficulty` (`easy`/`medium`/`hard`, ~40/40/20
split per category).

**How this was produced:** LLM-drafted (Claude, reading each source file in full before
writing its questions) from the actual fetched docs, not general training knowledge.
Every `expected_sources` path, JSON line, and `id` was verified — but this has **not**
been reviewed by a human yet; treat it as a strong draft pending spot-checking.

**Next steps:** satisfies the "hand-written eval question set" Roadmap item in the root
README. Next: retrieval-metrics scoring (hit rate, MRR) against `expected_sources`,
then LLM-as-judge validation against `reference_answer`.
