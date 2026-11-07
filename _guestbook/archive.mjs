// Snapshot the guestbook into a self-contained page that outlives the domain.
// Usage (from the repo root): node _guestbook/archive.mjs [--wayback]
//
// Reads supabaseUrl / supabaseKey / expiresAt from the site's config.js, so the
// page and the archive can never disagree about the project or the deadline.

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname);
const wantWayback = process.argv.includes("--wayback");

const configSource = await readFile(join(root, "..", "config.js"), "utf8");
const pick = (key) =>
  (configSource.match(new RegExp(`${key}\\s*:\\s*["']([^"']*)["']`)) || [])[1] || "";

const supabaseUrl = (process.env.SUPABASE_URL || pick("supabaseUrl")).replace(/\/+$/, "");
const supabaseKey = process.env.SUPABASE_KEY || pick("supabaseKey");
const expiresAt = new Date(process.env.EXPIRES_AT || pick("expiresAt") || "2027-01-16T23:59:59Z");
const siteUrl = process.env.SITE_URL || "https://ashy.lol/";

if (!supabaseUrl || !supabaseKey) {
  console.error("[archive] no Supabase project in config.js — nothing to fetch.");
  process.exit(1);
}

const escapeHtml = (value) =>
  String(value).replace(
    /[&<>"'`]/g,
    (char) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
        "`": "&#96;",
      })[char],
  );

const day = (iso) =>
  new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(iso));

const response = await fetch(
  `${supabaseUrl}/rest/v1/guestbook?select=name,message,created_at&order=created_at.desc&limit=1000`,
  { headers: { apikey: supabaseKey } },
);

if (!response.ok) {
  console.error(`[archive] Supabase answered ${response.status}: ${await response.text()}`);
  process.exit(1);
}

const entries = await response.json();
const takenAt = new Date();
const stamp = takenAt.toISOString().slice(0, 10);

const rows = entries
  .map((entry, index) => {
    const days = Math.max(
      0,
      Math.ceil((expiresAt.getTime() - new Date(entry.created_at).getTime()) / 86_400_000),
    );
    const tail =
      days === 0
        ? "signed on the last day"
        : `signed ${days} ${days === 1 ? "day" : "days"} before shutdown`;
    return `<li><p class="n">${String(entries.length - index).padStart(2, "0")}</p>
<p class="msg">${escapeHtml(entry.message)}</p>
<p class="meta"><b>${escapeHtml(entry.name || "anonymous")}</b> · ${escapeHtml(day(entry.created_at))} UTC · ${tail}</p></li>`;
  })
  .join("\n");

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>ashy.lol — final guestbook (archive)</title>
<style>
  :root { --ink:#0c0914; --text:#ece8f6; --muted:#8e84a8; --line:#2b2243; --violet:#a78bfa; }
  * { box-sizing:border-box; }
  body { margin:0; padding:48px 22px 80px; background:var(--ink); color:var(--text);
    font:15px/1.6 "Bricolage Grotesque", system-ui, sans-serif; }
  main { max-width:760px; margin:0 auto; }
  .brand { font-size:15px; letter-spacing:.22em; text-transform:uppercase; color:var(--muted);
    margin:0 0 34px; }
  h1 { font-size:clamp(34px,7vw,54px); font-weight:600; letter-spacing:-.02em; margin:0 0 14px; }
  .note { color:var(--muted); max-width:54ch; margin:0; }
  .rule { border-top:1px solid var(--line); margin:34px 0; }
  ol { list-style:none; padding:0; margin:0; }
  li { display:grid; grid-template-columns:38px 1fr; gap:12px; padding:16px 0;
    border-top:1px solid var(--line); }
  li:first-child { border-top:0; }
  .n { margin:0; padding-top:4px; font-size:11px; color:var(--muted); font-variant-numeric:tabular-nums; }
  .msg { grid-column:2; margin:0; font-size:16px; line-height:1.5; overflow-wrap:anywhere; }
  .meta { grid-column:2; margin:6px 0 0; font-size:12px; color:var(--muted); }
  .meta b { color:var(--violet); font-weight:400; }
  footer { margin-top:44px; padding-top:16px; border-top:1px solid var(--line);
    font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); }
  @media (max-width:560px) { li { grid-template-columns:1fr; gap:4px; } .msg,.meta { grid-column:1; } }
</style>
</head>
<body>
<main>
  <p class="brand">ashy.lol</p>
  <h1>Final guestbook</h1>
  <p class="note">The domain went dark on ${escapeHtml(day(expiresAt.toISOString()))} UTC. This is the snapshot taken on shutdown day: ${entries.length} ${entries.length === 1 ? "signature" : "signatures"}, kept only so the names outlive the site.</p>
  <div class="rule"></div>
  <ol>
${rows || '<li><p class="msg">Nobody signed it. That is its own kind of statement.</p></li>'}
  </ol>
  <footer>Snapshot taken ${escapeHtml(day(takenAt.toISOString()))} UTC · ashy.lol</footer>
</main>
</body>
</html>
`;

const outDir = join(root, "archive");
await mkdir(outDir, { recursive: true });
const htmlPath = join(outDir, `guestbook-${stamp}.html`);
await writeFile(htmlPath, html, "utf8");
await writeFile(
  join(outDir, `guestbook-${stamp}.json`),
  JSON.stringify(
    { site: siteUrl, expiresAt: expiresAt.toISOString(), takenAt: takenAt.toISOString(), entries },
    null,
    2,
  ),
  "utf8",
);

console.log(`[archive] ${entries.length} signatures`);
console.log(`[archive] wrote ${htmlPath}`);

const saveUrl = `https://web.archive.org/save/${siteUrl}guestbook`;
console.log(`[archive] capture the live page too: ${saveUrl}`);

if (wantWayback) {
  try {
    const capture = await fetch(saveUrl, {
      headers: { "User-Agent": "ashy.lol-guestbook-archive (final snapshot)" },
      redirect: "follow",
    });
    console.log(`[archive] wayback responded ${capture.status} ${capture.url}`);
  } catch (error) {
    console.error(`[archive] wayback request failed: ${error.message}`);
    console.error("[archive] open the save URL above in a browser instead.");
  }
}
