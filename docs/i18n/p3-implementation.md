# P3 Offline Translation Workflow

## Status

P3 implements the mandatory offline workflow. It does not call an online AI
service and does not approve or directly modify approved translations.

```text
source AST -> context + job plan -> external/manual JSON response
          -> strict candidate artifact -> local QA -> atomic draft import
          -> existing P2 review and approval
```

## Job and candidate artifacts

`TranslationJob` is versioned and contains a deterministic `job_id`, language,
P2 `source_key`, placeholder-bearing source text, placeholder metadata, bounded
heading/neighbour context, relevant glossary terms, occurrence IDs and policy
version. Compatible missing occurrences share a job while retaining all
occurrence IDs. Approved and already matched content is never planned.

`TranslationCandidate` retains job identity, source key, language, target and
provenance (`provider`, model, prompt version and glossary hash). Local QA writes
an explicit `validation` result; provider-supplied validation is ignored.
Unknown schema versions, fields, job IDs, duplicate IDs and missing responses
are rejected.

## Context policy

`extract_context` reads only the supplied Pandoc AST. It records heading
hierarchy, one preceding and one following paragraph, and configurable bounded
neighbour text. It does not read repository files or invent headings. Context
is prompt material only and can never become a translation automatically.

## Offline CLI

```text
python -m sop_i18n translate plan --order-file sop/pdf-order.txt \
  --memory i18n/memory/zh-CN.json --glossary i18n/glossary.json \
  --out tmp/translation-jobs.json

python -m sop_i18n translate import-response \
  --jobs tmp/translation-jobs.json --response tmp/ai-response.json \
  --out tmp/candidates.json

python -m sop_i18n translate check --jobs tmp/translation-jobs.json \
  --candidates tmp/candidates.json --glossary i18n/glossary.json \
  --out tmp/checked-candidates.json

python -m sop_i18n translate import-drafts \
  --jobs tmp/translation-jobs.json --candidates tmp/checked-candidates.json \
  --memory i18n/memory/zh-CN.json
```

The response contract is JSON only:

```json
{"schema_version": 1, "translations": [{"job_id": "job_...", "target": "..."}]}
```

The checked candidate artifact is the input to draft import. Import validates
again, so a caller cannot bypass QA by editing the artifact. All selected
candidates are preflighted before memory mutation. Empty drafts are populated,
identical drafts are no-ops, conflicting nonempty drafts abort the batch, and
approved or rejected records are skipped. Persistence uses P2 atomic JSON save.

## QA

QA reuses P1 placeholder decoding and P2 glossary checking. It blocks missing,
duplicate or malformed placeholders, invalid nesting, empty output, source-key
or language mismatch, simple numerical/unit changes and output commentary.
Numbers inside placeholder tokens are treated as token text and must remain
unchanged; semantic correctness remains a human-review responsibility.

## Provider boundary and provenance

`TranslationProvider` is a small protocol. `OfflineProvider` intentionally
raises if called: offline translation is performed by exporting jobs and
parsing a user-supplied structured response. No online API contract is guessed
or added. The versioned prompt is `i18n/prompts/zh-CN-v1.txt`; it explicitly
marks document text as untrusted and requires exact placeholders and JSON.

An online adapter can later implement the protocol with explicit opt-in,
environment-provided credentials, bounded retries and no TM access. Official
builds and P2 resolution never require a provider.

## Limitations and P4 handoff

- Context extraction from the combined order AST labels the document as `ast`;
  richer per-file document labels require extending the order manifest API.
- Numerical QA is intentionally conservative and should be expanded with
  domain-specific command/unit rules after review data exists.
- No real AI calls are made by tests or CLI.
- P4 may integrate reviewed Chinese AST/PDF generation, but must keep source
  Markdown, build scripts and approved-record protection unchanged.
