# Local Translation Review UI

The repository includes a local-only browser review tool. It does not require
an online service or a JavaScript build tool and binds to `127.0.0.1` by
default.

Start it with the completed P3 artifact:

```bash
python -m sop_i18n review \
  --jobs tmp/translation-jobs.json \
  --candidates tmp/i18n-runs/deepseek-001/candidates.json \
  --memory i18n/memory/zh-CN.json \
  --glossary i18n/glossary.json
```

Open `http://127.0.0.1:8765` in a browser. The UI provides candidate filtering,
source/target/context display, QA issues, candidate editing, draft import and
explicit approval. The approved action requires a passing local QA result and
uses the existing P2 approval function. Approved records are protected from UI
edits.

The `保存候选` action only updates the candidate artifact. `保存并导入 draft`
updates the candidate and atomically persists a P2 draft. `审核通过并批准`
does both and then performs P2 approval. The UI never changes Markdown or calls
an AI provider.

When the same canonical source text already has an approved TM record, the
candidate is classified as `duplicate` and disappears from the default
`candidate` list. Retrying approval is idempotent: the existing approved
translation is reused and the TM record is never overwritten.

The server is intended for local use only; it has no authentication and should
not be exposed beyond loopback. Stop it with `Ctrl+C`.
