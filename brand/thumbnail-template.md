# Thumbnail template — `ashtyn-thumbnail-template.psd`

1280 × 720, RGB/8. Five layers, bottom to top:

| # | Layer | What it is | Editable how |
|---|-------|------------|--------------|
| 1 | `1 - ART (replace this)` | Placeholder capture gradient | Drop a 1280 × 720 screenshot in, or replace the layer |
| 2 | `2 - TAG PLATE` | 391 × 54 rounded plate, `#14121A` at 78%, 1px `#E9E5DD` at 28% | Move/resize with the tag; keep it hugging the label |
| 3 | `3 - TAG MARK a` | **Live type** — a bare `a` in iris `#9B8AF0`, Consolas 26px, no brackets (the brackets were retired with the v2 mark) | Retype; one glyph, one colour |
| 4 | `4 - TAG LABEL` | **Live type** — series label, smoke `#E9E5DD`, Consolas 24px, 140 tracking | Retype per series: `ZOMBIES · PART 1` |
| 5 | `5 - TITLE` | **Live type** — two lines max, white, 95px, 90px leading, −35 tracking | Retype; keep it to two lines |

## Fonts

Only two, and one of them is already on your machine.

| File (in `brand/fonts/`) | Installs as | Used for |
|---|---|---|
| `BricolageGrotesque-SemiBold.ttf` | Bricolage Grotesque SemiBold (600) | Wordmark `[ashtyn]`, avatar `[a]`, all banner/avatar exports |
| `BricolageGrotesque-Bold.ttf` | Bricolage Grotesque Bold (700) | Thumbnail titles in the PSD |
| — (system font) | Consolas | Tag mark and tag label in the PSD |

Install: select both `.ttf` files → right-click → **Install** (Windows) or double-click → **Install Font**
(macOS). Both weights are pinned static instances of the same variable font, so they group under one
family instead of showing up as separate fonts.

Consolas ships with Windows and with Office on macOS; it is not redistributable, which is why it isn't in
`brand/fonts`. If you edit on a Mac without it, any mono works — just use the same one for both tag layers.

Nothing else is needed. There is deliberately no second display face: the whole identity is one grotesque
plus one mono.

## Notes

- Photoshop may show a one-time "text layers need to be updated" prompt on first open. Accept it; it redraws
  the type from the embedded text data. Everything stays type afterwards.
- The tag chip is a fixed plate. If a label gets much longer, widen the plate rather than shrinking the type.
- Keep the tag in the same corner at the same size on every upload — that repetition is the whole system.

## Rebuilding from source

`src/export.html` is the master. Each layer is a stage in that file; `src/prep_psd.py` turns the renders into
buffers; `src/build_psd.cjs` assembles the PSD.

```bash
# 0. once: npm install ag-psd  (in a scratch dir)
# 1. render stages with headless Chrome at 1280x720 -> src/layers/*.png
#    (#thumb-art, #thumb-title, #thumb-mark, #thumb-label, #thumb-plate, #thumb-all)
python brand/src/prep_psd.py
AG_PSD_PATH=/path/to/node_modules/ag-psd node brand/src/build_psd.cjs
```
