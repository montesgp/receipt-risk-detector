# AI-regeneration detection research (issue #67)

Tracks the investigation into whether a fully AI-regenerated receipt (no
surviving provenance metadata, no corrupted CBU/CUIT digit) can be
distinguished from a real screenshot by anything measurable in the pixels —
most likely font-rendering/kerning differences between the source app's real
UI and an AI model's re-drawn text, per the observation that started this
(comparing a real Mercado Pago receipt against a ChatGPT/gpt-image fake of
the same one).

This is a research spike, not a shipped detector. Nothing here feeds the
production pipeline until a finding is validated and turned into a proper
change (own proposal/design/tasks, its own ruleset version, its own tests) —
see `openspec/` for that process once/if this gets there.

## Collecting samples — tracked in issue #68

**Where files go**, once redacted (see below — never commit an unredacted
file, even here):

```
apps/api/research/aigc-detection/samples/
  real/   -- genuine receipts, any bank
  fake/   -- AI-generated/edited receipts, any tool (ChatGPT, Qwen, Grok, ...)
```

One manifest entry per file in `manifest.json` (schema below). Filename
itself doesn't matter — the manifest is the source of truth — but a
descriptive name helps: `<bank>_<n>_<real|fake>_<wsp|direct>.<ext>`.

**Redact every file before it touches this directory** — same treatment as
`samples/images/reference/reference_real_mp_bbva_redacted.jpg`: solid black
boxes over name, CUIT/CUIL, CVU, CBU, operation number, identification code.
Only amount, date, and entity names stay visible. This repo is public.

### WhatsApp or direct — capture **both**, for every sample, real and fake

Two different things are being measured and both matter:

1. **The operational case**: every receipt this product will ever actually
   receive in production has already been through WhatsApp (or a similar
   lossy re-encode) — that's how people actually send these. Whatever
   detector eventually comes out of this research has to work on *that*
   file, not a pristine export. So the WhatsApp-passed version of each
   sample is the one that matters for validating any eventual signal.
2. **The diagnostic contrast**: keeping the pre-WhatsApp original alongside
   it is what let us confirm today, byte-for-byte, that WhatsApp strips the
   C2PA manifest entirely (see #67). Without the pair, we're guessing at
   *what* changed; with it, we can measure exactly what survives the
   channel and what doesn't — for metadata, and eventually for whatever
   pixel-level signal this research is looking for.

So: send it through WhatsApp to yourself (or however you'd realistically
receive one), keep both files, redact both, add both to the manifest with
`passed_through_whatsapp` set correctly and `paired_with` pointing at the
other one's `id`. A sample with no pair (e.g. a real receipt you don't have
a pre-WhatsApp copy of) is still useful — add it alone, just leave
`paired_with` null.

Real samples need the same pairing for the same reason: the reference set
and any future detector both need to know what a *genuine* receipt looks
like after the exact channel degradation it will actually be evaluated
through.

### What's actually useful to collect

- Different banks / apps, not just Mercado Pago — the font/kerning question
  is meaningless with only one template.
- Different generators for the fake side (ChatGPT/gpt-image, Qwen, Grok are
  the three already seen this session — more if available).
- Repeats of the same bank/template help less than breadth across
  banks/templates once you have 2-3 of each.

## `manifest.json` schema

```jsonc
{
  "samples": [
    {
      "id": "mp_bbva_003_fake_wsp",       // unique, referenced by paired_with
      "path": "samples/fake/mp_bbva_003_fake_wsp.jpg",
      "label": "fake",                     // "real" | "fake"
      "bank_template": "mercado_pago",     // free text, name the app/bank
      "generator": "chatgpt",              // null for "real"; else the tool
      "passed_through_whatsapp": true,
      "paired_with": "mp_bbva_003_fake_direct",  // this file's other half, or null
      "sha256": "...",                     // sha256 of the committed (redacted) bytes
      "redacted": true,                    // must always be true before commit
      "notes": ""
    }
  ]
}
```

## Running the measurement skeleton

```
uv run python research/aigc-detection/measure.py
```

For every sample in `manifest.json`, runs the same RapidOCR engine the
production adapter uses (`RECEIPT_RISK_OCR_MODEL_DIR` must be set, same as
running the API) and writes the raw per-box geometry (position, size,
rotation, confidence — not just the lossy `RawTextBox` the production parser
keeps) to `measurements/<id>.json`. This is data collection only: no
statistics, no threshold, no verdict. Once there are enough samples across
enough banks, the actual comparison (real-vs-fake distributions on whatever
geometric measures turn out to separate them) is the next step, written
against real numbers instead of guessed.
