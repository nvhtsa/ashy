# ASHTYN — art direction brief

Paste the prompt blocks below into an image model (GPT image / Sora / Midjourney).
Bring the result back and the platform set gets built around it.

---

## 1. Wordmark — main plate

**Prompt**

> A custom hand-drawn display wordmark reading exactly "ASHTYN", all caps, one
> word, one line. Heavy condensed letterforms drawn from scratch — no standard
> typeface. The letters are chunky and slightly irregular, as if cut from sheet
> metal and then melted: thick verticals, sharp angled cuts on the terminals,
> one letter subtly out of alignment so the word looks hand-set rather than
> typed. Material: polished chrome — bright specular highlights, a hard horizon
> line across the middle, deep black reflections, purple light bleeding in from
> one side. Background pure white. Nothing else in the image: no other text, no
> logo, no badge, no border, no mockup, no shadow on the page.

**Negative:** esports badge, shield, wing, lightning bolt clipart, 3D bevel
preset, glossy web 2.0, drop shadow, checkerboard transparency, watermark,
signature, extra letters, misspelling.

**Output:** 3000 × 1200, white background (or true transparent PNG).

---

## 2. Wordmark — second plate (the chaotic one)

> The same wordmark again, but printed twice: once in solid black, once in
> electric violet, offset about 12 pixels so the violet hangs off the black like
> a misregistered screen print. Fine horizontal scanlines cut through both.
> Slight rotation, 2 degrees. White background. No other elements.

This is the load-bearing variant — the misregistration is the brand's "wrong on
purpose" edge. Keep both plates clean so they can be split and re-composited.

---

## 3. Monogram — profile picture

> A single capital "A" in the same hand-drawn chrome lettering: heavy, condensed,
> slightly warped, one angled cut across the top. Centred, filling about 70% of a
> square canvas. Deep black background with a dark purple radial glow behind the
> letter. Polished chrome surface, violet rim light. No text, no circle, no
> border — the platform applies its own circular crop.

**Output:** 1024 × 1024, black background.

---

## 4. Rules for generating

- **Spell it right.** "ASHTYN" — A S H T Y N. Six letters, one word. Image
  models misspell; check before anything else.
- **White or black ground only.** No scenes, no gradients to the corners, no
  vignettes baked in — the banner layout supplies the ground.
- **One idea per image.** A wordmark plate, or a monogram. Never a banner.
- **Ask for the silhouette first.** If the flat black shape doesn't read as
  ASHTYN at 200px wide, the chrome won't save it.
- **Keep the source.** Full-size PNG, uncompressed. Everything below is cut from
  it, and repeated regeneration will drift.

---

## 5. What happens with the art

Once a plate exists in `C:\Users\ashtyn\Pictures\gg\`:

| Surface | Size | Rule |
|---|---|---|
| YouTube banner | 2560 × 1440 | wordmark inside the 1546 × 423 band, never crossing it |
| YouTube / Twitch avatar | 1024, 800, 512, 256 | square crop on the monogram, safe inside a circle |
| Twitch banner | 1200 × 480 | full-bleed crop |
| X header | 1500 × 500 | full-bleed crop |
| Thumbnails | 1280 × 720 | existing template, tag chip bottom-left |

`brand/src/format_platform.py` already does the cuts and reports whether the
letters land inside the safe band before anything is uploaded.
