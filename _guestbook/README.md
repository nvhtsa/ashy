# ashy.lol guestbook

The guestbook is a view of the main site, not a separate page: it lives at `ashy.lol/guestbook`,
shares the nav, background and styling, and is rendered by `guestbook.js` from the markup in
`index.html`.

This folder is tooling only. The leading underscore keeps it out of the published site.

## Setup, once

1. Create a free project at [supabase.com](https://supabase.com).
2. SQL Editor → paste all of `schema.sql` → run.
3. Settings → API Keys → copy the **Project URL** and the **Publishable** key (`sb_publishable_…`),
   or the legacy **anon** key on the Legacy API Keys tab. Put both in the `guestbook` block in
   `config.js`. Both values are public by design, so they belong in the repo.

   Never paste the **secret** / `service_role` key there: it bypasses row level security.
4. Commit and push.

The client sends the key on the `apikey` header only. Publishable and legacy anon keys are not JWTs, so
they are never sent as a bearer token — that combination is what makes either key type work.

## The deadline is in the database

`schema.sql` sets an insert policy of `now() < '2027-01-16 23:59:59+00'`. After that moment the
database rejects signatures no matter what the page does, even a hand-written `curl`. If the registrar
date moves, change it in **both** `schema.sql` (re-run the policy) and `config.js` (`expiresAt`).

Also enforced, since there is no server: 280-character and 2-character check constraints, no update or
delete grant at all, and a trigger that refuses more than five inserts in ten seconds.

## The last day

```bash
node _guestbook/archive.mjs            # _guestbook/archive/guestbook-<date>.html + .json
node _guestbook/archive.mjs --wayback  # also asks the Wayback Machine to capture the live page
```

The HTML has its styles inline, so it opens from a folder in ten years with nothing installed. Commit
the archive, then delete the Supabase project whenever you like — the JSON is the only copy of
everyone's wording once it is gone.

## Files

| File          | Role                                                     |
| ------------- | -------------------------------------------------------- |
| `schema.sql`  | Table, RLS policies, deadline and throttle                |
| `archive.mjs` | Shutdown-day snapshot (Node 20.11+)                       |

The client itself is `guestbook.js` at the site root, wired into `index.html` under
`data-view="guestbook"` and registered in `app.js`'s `PAGE_NAMES`.
