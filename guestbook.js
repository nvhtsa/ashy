// Guestbook view for ashy.lol. Reads window.SITE.guestbook from config.js and
// talks to Supabase's REST API directly — no SDK, no server, nothing to keep alive.

(() => {
  const C = (window.SITE && window.SITE.guestbook) || {};
  // Accept either the bare project URL or one pasted with /rest/v1 on the end.
  const url = String(C.supabaseUrl || "").replace(/\/+$/, "").replace(/\/rest\/v1$/, "");
  const key = String(C.supabaseKey || "");
  const live = Boolean(url && key);
  const deadline = new Date(C.expiresAt || "2027-01-16T23:59:59Z");
  const COOLDOWN = 60_000;

  const $ = (id) => document.getElementById(id);
  const els = {
    days: $("gbDays"), hours: $("gbHours"), minutes: $("gbMinutes"), seconds: $("gbSeconds"),
    form: $("gbForm"), name: $("gbName"), message: $("gbMessage"), trap: $("gbTrap"),
    chars: $("gbChars"), submit: $("gbSubmit"), msg: $("gbMsg"), setup: $("gbSetup"),
    list: $("gbList"), meta: $("gbMeta"), clock: $("gbClock"),
  };
  if (!els.form) return;

  let started = false, timer = 0, loaded = false, closed = false;

  const pad = (n) => String(n).padStart(2, "0");
  const api = (q = "") => `${url}/rest/v1/guestbook${q}`;
  // Publishable (sb_publishable_...) and legacy anon keys both belong on the
  // apikey header. They are not JWTs, so they must not be sent as a bearer token.
  const headers = () => ({
    apikey: key,
    "Content-Type": "application/json",
    Accept: "application/json",
  });

  const say = (text, bad) => {
    els.msg.textContent = text;
    els.msg.classList.toggle("bad", Boolean(bad));
  };

  const stamp = (iso) =>
    new Intl.DateTimeFormat(undefined, {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZone: "UTC",
    }).format(new Date(iso));

  function close() {
    closed = true;
    els.form.hidden = true;
    els.setup.hidden = false;
    els.setup.textContent = "Closed. It went down with the domain.";
    els.clock.classList.add("done");
  }

  function tick() {
    const left = Math.max(0, deadline - Date.now());
    els.days.textContent = String(Math.floor(left / 86_400_000));
    els.hours.textContent = pad(Math.floor(left / 3_600_000) % 24);
    els.minutes.textContent = pad(Math.floor(left / 60_000) % 60);
    els.seconds.textContent = pad(Math.floor(left / 1000) % 60);
    if (left === 0 && !closed) close();
  }

  function setupState() {
    els.form.hidden = true;
    els.setup.hidden = false;
    els.meta.textContent = "not open yet";
  }

  function render(rows) {
    const entries = rows.map((row) => ({
      name: row.name || "anonymous",
      message: row.message,
      createdAt: row.created_at,
      days: Math.max(0, Math.ceil((deadline - new Date(row.created_at)) / 86_400_000)),
    }));

    els.list.replaceChildren(
      ...entries.map((entry, index) => {
        const li = document.createElement("li");
        li.className = "gb-item";

        const n = document.createElement("span");
        n.className = "gb-n";
        n.textContent = pad(entries.length - index);

        const body = document.createElement("div");
        const msg = document.createElement("p");
        msg.className = "gb-text";
        msg.textContent = entry.message;

        const meta = document.createElement("p");
        meta.className = "gb-by";
        const who = document.createElement("span");
        who.textContent = entry.name;
        const tail = entry.days === 0
          ? "signed on the last day"
          : `signed ${entry.days} ${entry.days === 1 ? "day" : "days"} before the end`;
        meta.append(who, ` · ${stamp(entry.createdAt)} UTC · ${tail}`);

        body.append(msg, meta);
        li.append(n, body);
        return li;
      }),
    );

    els.meta.textContent = entries.length
      ? `${entries.length} ${entries.length === 1 ? "signature" : "signatures"}, none permanent`
      : "nobody yet";
  }

  async function load() {
    try {
      const r = await fetch(api("?select=name,message,created_at&order=created_at.desc&limit=200"), {
        headers: headers(),
      });
      if (!r.ok) throw new Error(r.status);
      render(await r.json());
      loaded = true;
      els.meta.classList.remove("bad");
    } catch {
      els.meta.textContent = "couldn't load signatures";
      els.meta.classList.add("bad");
    }
  }

  async function sign(event) {
    event.preventDefault();
    if (closed) return;

    const message = els.message.value.trim();
    if (message.length < 2) { say("Write a few words first.", true); els.message.focus(); return; }
    if (els.trap.value) return;

    const last = Number(localStorage.getItem("ashy.gb.last") || 0);
    if (Date.now() - last < COOLDOWN) { say("You signed a minute ago — give it a moment.", true); return; }

    els.submit.disabled = true;
    say("Signing…");

    try {
      const r = await fetch(api(), {
        method: "POST",
        headers: { ...headers(), Prefer: "return=minimal" },
        body: JSON.stringify({ name: els.name.value.trim() || "anonymous", message }),
      });

      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        say(detail.message || "That didn't go through.", true);
        if (r.status === 401 || r.status === 403) close();
        return;
      }

      localStorage.setItem("ashy.gb.last", String(Date.now()));
      els.message.value = "";
      els.chars.textContent = "0";
      say("Signed. It's temporary, like everything here.");
      await load();
    } catch {
      say("Network trouble. Try again in a moment.", true);
    } finally {
      els.submit.disabled = false;
    }
  }

  function start() {
    if (started) return;
    started = true;

    tick();
    timer = setInterval(tick, 1000);

    els.message.addEventListener("input", () => {
      els.chars.textContent = String(els.message.value.length);
    });
    els.form.addEventListener("submit", sign);

    if (live) load();
    else setupState();
  }

  // The router hides and shows sections. Start when this view is first shown.
  addEventListener("viewchange", (event) => {
    if (event.detail && event.detail.view === "guestbook") {
      start();
      if (live && started && !loaded) load();
    }
  });

  if (document.body.dataset.view === "guestbook") start();

  addEventListener("pagehide", () => clearInterval(timer));
})();
