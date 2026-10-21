(() => {
  const C = window.SITE, $ = (s) => document.querySelector(s);
  const el = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props); n.append(...kids); return n;
  };

  // Socials
  C.socials.forEach((s) => $("#socials").append(
    el("a", { href: s.url, target: "_blank", rel: "noreferrer noopener" },
      el("img", { src: `assets/icons/${s.icon}.svg`, alt: "" }), s.name)));

  // Gear and Settings share one card layout
  const copy = (btn, text) => btn.onclick = async () => {
    try { await navigator.clipboard.writeText(text); btn.textContent = "Copied"; }
    catch (e) { btn.textContent = "Copy failed"; }
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  };
  const block = (b) => {
    const btn = el("button", { type: "button", textContent: "Copy" }); copy(btn, b.text);
    return el("div", { className: "block" },
      el("div", { className: "bhead" }, el("span", { textContent: b.label }), btn),
      el("pre", { textContent: b.text }));
  };
  const cards = (target, groups) => groups.forEach((g) => target.append(
    el("section", { className: "group" }, el("h2", { textContent: g.group }),
      el("dl", {}, ...(g.items || []).flatMap(([k, v]) => [el("dt", { textContent: k }), el("dd", { textContent: v })])),
      ...(g.blocks || []).map(block))));
  cards($("#gearList"), C.gear);
  cards($("#settingsList"), C.settings || []);

  // Tabs (clean path routing keeps the music playing between pages)
  const views = [...document.querySelectorAll("[data-view]")].filter((v) => v.tagName === "SECTION");
  const tabs = [...document.querySelectorAll("nav a")];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const replay = (node) => { node.classList.remove("enter"); void node.offsetWidth; node.classList.add("enter"); };
  const PAGE_NAMES = new Set(["gear", "settings", "listening"]);
  const pathFor = (page) => page === "home" ? "/" : `/${page}`;
  const pageFromLocation = () => {
    const last = location.pathname.split("/").filter(Boolean).pop() || "home";
    return PAGE_NAMES.has(last) ? last : "home";
  };
  let routeId = 0;
  const TITLES = { home: "ASHTYN", gear: "Gear | ASHTYN", settings: "Settings | ASHTYN", listening: "Listening | ASHTYN" };

  // Support old #gear links and GitHub Pages' ?p=/gear fallback.
  const fallbackPath = new URLSearchParams(location.search).get("p");
  if (fallbackPath && /^\/(gear|settings|listening)\/?$/.test(fallbackPath)) {
    history.replaceState(null, "", fallbackPath.replace(/\/$/, ""));
  } else if (location.hash) {
    const legacyPage = location.hash.slice(1);
    if (legacyPage === "home" || PAGE_NAMES.has(legacyPage)) {
      history.replaceState(null, "", pathFor(legacyPage));
    }
  }

  async function route(animate) {
    const id = ++routeId;
    const v = pageFromLocation();
    tabs.forEach((a) => a.setAttribute("aria-current",
      (a.pathname.replace(/\/$/, "") || "/") === pathFor(v) ? "page" : "false"));
    document.body.dataset.view = v;
    document.title = TITLES[v] || "ASHTYN";
    const cur = views.find((x) => !x.hidden);
    if (cur && cur.dataset.view === v) { cur.classList.remove("leaving"); return; }
    if (cur && animate && !calm) {
      cur.classList.add("leaving");
      await wait(180);
      if (id !== routeId) return;
      cur.classList.remove("leaving");
    }
    views.forEach((x) => (x.hidden = x.dataset.view !== v));
    if (animate) replay(views.find((x) => x.dataset.view === v));
  }

  tabs.forEach((a) => a.addEventListener("click", (e) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    const page = a.pathname.split("/").filter(Boolean).pop() || "home";
    if (page !== pageFromLocation()) {
      history.pushState(null, "", pathFor(PAGE_NAMES.has(page) ? page : "home"));
      route(true);
    }
  }));
  const homeMark = document.querySelector(".mark");
  if (homeMark) homeMark.addEventListener("click", (e) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (pageFromLocation() !== "home") {
      history.pushState(null, "", "/");
      route(true);
    }
  });
  addEventListener("popstate", () => route(true));
  route(false);

  // Player + audio analysis. The whole site reacts to this music.
  const audio = $("#audio"), title = $("#pTitle"), playBtn = $("#pPlay"), seek = $("#pSeek"), vol = $("#pVol");
  let i = 0, actx = null, analyser = null, gain = null, freq = null;
  const fx = { bass: 0, kick: 0, mid: 0, hit: false, k: 1 };
  try {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    const src = actx.createMediaElementSource(audio);
    analyser = actx.createAnalyser(); analyser.fftSize = 1024; analyser.smoothingTimeConstant = .7;
    gain = actx.createGain();
    src.connect(analyser); src.connect(gain); gain.connect(actx.destination);
    freq = new Uint8Array(analyser.frequencyBinCount);
  } catch (e) { actx = analyser = gain = null; }
  const setVol = () => { const v = vol.value / 100; if (gain) gain.gain.value = v; else audio.volume = v; };
  vol.oninput = setVol; setVol();

  // Browsers block sound until the visitor interacts. Try on load; if blocked,
  // the first click, tap or key press starts the music.
  function startMusic() {
    if (actx && actx.state !== "running") actx.resume().catch(() => {});
    if (audio.paused) audio.play().catch(() => {});
  }
  const GESTURES = ["pointerdown", "keydown", "touchend"];
  const unbind = () => GESTURES.forEach((g) => removeEventListener(g, onGesture, true));
  function onGesture(e) {
    if (e.target.closest && e.target.closest(".player")) return;
    startMusic();
  }
  const settle = () => { if (!audio.paused && (!actx || actx.state === "running")) unbind(); };
  GESTURES.forEach((g) => addEventListener(g, onGesture, true));
  audio.addEventListener("playing", settle);
  if (actx) actx.onstatechange = settle;

  function load(n, play) {
    i = (n + C.playlist.length) % C.playlist.length;
    audio.src = C.playlist[i].src; title.textContent = C.playlist[i].title; seek.value = 0;
    mark();
    if (play) startMusic();
  }
  playBtn.onclick = () => { if (audio.paused) startMusic(); else { unbind(); audio.pause(); } };
  $("#pNext").onclick = () => load(i + 1, true);
  $("#pPrev").onclick = () => load(i - 1, true);
  audio.onplay = audio.onpause = () => {
    playBtn.innerHTML = audio.paused ? "&#9654;" : "&#10074;&#10074;";
    playerEl.classList.toggle("playing", !audio.paused);
  };
  audio.onended = () => load(i + 1, true);
  audio.ontimeupdate = () => { if (audio.duration) seek.value = (audio.currentTime / audio.duration) * 100; };
  seek.oninput = () => { if (audio.duration) audio.currentTime = (seek.value / 100) * audio.duration; };
  // Expandable tracklist: pick any song
  const playerEl = document.querySelector(".player"), queue = $("#pQueue"), listBtn = $("#pList");
  C.playlist.forEach((t, n) => queue.append(el("button", { type: "button", onclick: () => load(n, true) },
    el("span", { className: "n", textContent: String(n + 1) }),
    el("span", { className: "eq" }, el("i"), el("i"), el("i")),
    el("span", { className: "t", textContent: t.title }))));
  function mark() { [...queue.children].forEach((b, n) => b.setAttribute("aria-current", n === i ? "true" : "false")); }
  const setOpen = (o) => { playerEl.classList.toggle("open", o); listBtn.setAttribute("aria-expanded", String(o)); };
  listBtn.onclick = () => setOpen(!playerEl.classList.contains("open"));
  addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  addEventListener("pointerdown", (e) => { if (!e.target.closest(".player")) setOpen(false); });

  load(Math.floor(Math.random() * C.playlist.length), true); // random track on every page load

  // Bass, beat and mid levels, updated every frame. The logo reacts here;
  // the intro and the background orbs read fx.
  const logo = document.querySelector(".logo");
  let avg = 0, lastHit = 0;
  function analyse(now) {
    fx.hit = false;
    if (analyser && !audio.paused && actx.state === "running") {
      analyser.getByteFrequencyData(freq);
      let b = 0, m = 0;
      for (let k = 1; k <= 6; k++) b += freq[k];
      for (let k = 12; k < 64; k++) m += freq[k];
      b /= 6 * 255; m /= 52 * 255;
      // Louder volume = stronger reactions: about 1x at the default 15%, about 2.2x at max
      const vf = gain ? gain.gain.value : audio.volume;
      const k = fx.k = vf < .15 ? .2 + (vf / .15) * .8 : 1 + (vf - .15) * 1.41;
      avg = avg * .96 + b * .04;
      if (b > .3 && b > avg * 1.1 + .02 && now - lastHit > 140) { fx.kick = k; fx.hit = true; lastHit = now; }
      const tb = b * k;
      fx.bass += (tb - fx.bass) * (tb > fx.bass ? .55 : .12);
      fx.mid += (m * k - fx.mid) * .3;
    } else { fx.bass *= .92; fx.mid *= .92; avg *= .98; }
    fx.kick *= .86;
    if (logo && !calm) {
      const sc = 1 + fx.bass * .075 + fx.kick * .11, sh = Math.min(30, fx.kick * fx.kick * 12);
      logo.style.transform = `translate(${(Math.random() - .5) * sh}px,${(Math.random() - .5) * sh}px) scale(${sc})`;
      logo.style.filter = `drop-shadow(0 0 22px rgba(255,255,255,${.06 + fx.bass * .3 + fx.kick * .4})) ` +
        `drop-shadow(0 0 44px rgba(109,61,240,${.45 + fx.bass * .3})) drop-shadow(0 0 70px rgba(180,200,255,.12))`;
    }
    requestAnimationFrame(analyse);
  }
  requestAnimationFrame(analyse);

  // Last.fm: what's playing on Spotify
  const { user, apiKey } = C.lastfm;
  const ago = (uts) => {
    const m = Math.round((Date.now() / 1000 - uts) / 60);
    return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`;
  };
  function show(tracks, msg) {
    const np = $("#np"), recent = $("#recent");
    np.replaceChildren(); recent.replaceChildren(); np.classList.remove("live");
    if (!tracks) { $("#npLede").textContent = ""; np.append(el("p", { textContent: msg })); return; }
    const t = tracks[0], live = t["@attr"]?.nowplaying === "true";
    $("#npLede").textContent = live ? "Playing on Spotify right now." : "Nothing playing right now. This is my last track.";
    np.classList.toggle("live", live);
    np.append(
      el("img", { className: "art", src: t.image?.[3]?.["#text"] || "", alt: "" }),
      el("div", {},
        el("a", { className: "t", href: t.url, target: "_blank", rel: "noreferrer noopener", textContent: t.name }),
        el("div", { className: "s", textContent: `${t.artist["#text"]}${t.album["#text"] ? " on " + t.album["#text"] : ""}` }),
        el("div", { className: "st", textContent: live ? "Playing now" : t.date ? ago(t.date.uts) : "" })));
    tracks.slice(1, 6).forEach((r) => recent.append(
      el("a", { href: r.url, target: "_blank", rel: "noreferrer noopener" },
        el("span", { textContent: `${r.name} by ${r.artist["#text"]}` }),
        el("span", { textContent: r.date ? ago(r.date.uts) : "" }))));
  }
  async function poll() {
    if (!user || !apiKey) { show(null, "Add your Last.fm username and API key in config.js to show what you're listening to."); return false; }
    try {
      const r = await fetch(`https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=${encodeURIComponent(user)}&api_key=${encodeURIComponent(apiKey)}&format=json&limit=6`);
      const d = await r.json();
      if (!d.recenttracks) throw new Error(d.message);
      const tracks = [].concat(d.recenttracks.track);
      show(tracks);
      return tracks[0]?.["@attr"]?.nowplaying === "true";
    } catch (e) { show(null, "Couldn't reach Last.fm. Check the username and API key in config.js."); return false; }
  }
  poll(); setInterval(poll, 20000);

  // PS2-style intro: drifting orbs and glass towers that rush at the camera on click
  function initIntro(canvas, still) {
    const ctx = canvas.getContext("2d"), DPR = Math.min(2, devicePixelRatio || 1);
    const rnd = (a, b) => a + Math.random() * (b - a);
    let W, H, raf, flyAt = 0, last = performance.now(), mx = 0, my = 0, dead = false;
    const sprite = document.createElement("canvas"); sprite.width = sprite.height = 128;
    const sc = sprite.getContext("2d"), g = sc.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, "rgba(225,210,255,1)"); g.addColorStop(.25, "rgba(167,139,250,.7)");
    g.addColorStop(.6, "rgba(109,61,240,.22)"); g.addColorStop(1, "rgba(109,61,240,0)");
    sc.fillStyle = g; sc.fillRect(0, 0, 128, 128);
    const resize = () => {
      W = innerWidth; H = innerHeight; canvas.width = W * DPR; canvas.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };
    addEventListener("resize", resize); resize();
    const orbs = Array.from({ length: innerWidth < 600 ? 55 : 95 }, () => ({
      x: rnd(-1.8, 1.8), y: rnd(-1.4, 1.4), z: rnd(.35, 1.8), s: rnd(.018, .06),
      a: rnd(.45, 1), ph: rnd(0, 6.28), sp: rnd(.2, .6) }));
    const towers = Array.from({ length: 9 }, (_, k) => ({
      x: (k + .5) / 9 + rnd(-.03, .03), w: rnd(26, 58), h: rnd(.3, .78), ph: rnd(0, 6.28) }));
    addEventListener("pointermove", (e) => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; }, { passive: true });

    function frame(now) {
      if (dead) return;
      const dt = Math.min(.05, (now - last) / 1000); last = now;
      const t = still ? 0 : now / 1000, ft = flyAt ? (now - flyAt) / 1000 : 0, p = Math.min(1, ft / 1.1);
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      const B = still ? 0 : fx.bass, K = still ? 0 : fx.kick;

      const spread = 1 + p * p * 2.5;
      towers.forEach((tw) => {
        const w = tw.w * (1 + p * 2), h = tw.h * H * (1 + p) * (1 + B * .08), x = W / 2 + (tw.x - .5) * W * spread;
        const al = (.16 + .08 * Math.sin(t * .8 + tw.ph)) * (1 - p) * (1 + B * 1.3 + K * .8);
        const gr = ctx.createLinearGradient(0, H - h, 0, H);
        gr.addColorStop(0, "rgba(139,92,246,0)"); gr.addColorStop(1, `rgba(139,92,246,${al * 2})`);
        ctx.fillStyle = gr; ctx.fillRect(x - w / 2, H - h, w, h);
      });

      const speed = flyAt ? .35 + 9 * ft * ft + B * 1.5 : 0, out = Math.max(0, (ft - 1.4) / .6);
      for (const o of orbs) {
        if (!still) {
          o.y -= dt * o.sp * .06 * (1 + B * 10); if (o.y < -1.5) o.y = 1.5;
          o.x += Math.sin(t * o.sp + o.ph) * dt * .03;
        }
        if (flyAt) o.z -= dt * speed;
        if (o.z < .06) continue;
        const k = 1 / o.z, r = o.s * k * Math.min(W, H) * 1.6 * (1 + B * .8 + K * .5);
        const px = W / 2 + (o.x - mx * .3) * k * W * .22, py = H / 2 + (o.y - my * .3) * k * H * .22;
        if (px < -r || px > W + r || py < -r || py > H + r) continue;
        const near = Math.min(1, (o.z - .06) / .2), far = Math.min(1, (2.2 - o.z) / .5);
        ctx.globalAlpha = Math.min(1, Math.max(0, o.a * (.6 + .4 * Math.sin(t * o.sp * 2 + o.ph)) * (.8 + B * .7 + K * .5) * near * far * (1 - out)));
        ctx.drawImage(sprite, px - r, py - r, r * 2, r * 2);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
    return { fly: () => (flyAt = performance.now()), stop: () => { dead = true; cancelAnimationFrame(raf); } };
  }

  // Small purple and white orbs behind every page. They flow with the bass.
  function initOrbs(canvas, still) {
    const ctx = canvas.getContext("2d"), DPR = Math.min(2, devicePixelRatio || 1);
    const rnd = (a, b) => a + Math.random() * (b - a);
    let W, H, last = performance.now();
    const sprite = (rgb) => {
      const c = document.createElement("canvas"); c.width = c.height = 64;
      const x = c.getContext("2d"), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, `rgba(${rgb},1)`); g.addColorStop(.3, `rgba(${rgb},.45)`); g.addColorStop(1, `rgba(${rgb},0)`);
      x.fillStyle = g; x.fillRect(0, 0, 64, 64); return c;
    };
    const tint = [sprite("167,139,250"), sprite("245,240,255")];
    const resize = () => {
      W = innerWidth; H = innerHeight; canvas.width = W * DPR; canvas.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    };
    addEventListener("resize", resize); resize();
    const orbs = Array.from({ length: innerWidth < 600 ? 30 : 52 }, () => ({
      x: Math.random(), y: Math.random(), r: rnd(2, 7), vy: rnd(.012, .04), a: rnd(.3, .75),
      ph: rnd(0, 6.28), w: Math.random() < .35 ? 1 : 0, v: 0 }));
    function frame(now) {
      const dt = Math.min(.05, (now - last) / 1000); last = now;
      const t = still ? 0 : now / 1000, B = still ? 0 : fx.bass, K = still ? 0 : fx.kick;
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "lighter";
      for (const o of orbs) {
        if (!still) {
          o.v *= Math.pow(.05, dt);
          if (fx.hit && !still) o.v += (.12 + o.vy * 5) * fx.k;
          o.y -= dt * (o.vy * (1 + B * 10 + K * 10) + o.v);
          o.x += (Math.sin(t * .5 + o.ph) * .02 + (o.w ? .004 : -.004) * B) * dt * 2;
          if (o.y < -.05) { o.y = 1.05; o.x = Math.random(); }
          if (o.x < -.05) o.x = 1.05; else if (o.x > 1.05) o.x = -.05;
        }
        const d = o.r * (1 + B * 1.8 + K * 1.2) * 6;
        ctx.globalAlpha = Math.min(1, o.a * (.45 + .25 * Math.sin(t + o.ph)) * (.7 + B * 1.3 + K * .9));
        ctx.drawImage(tint[o.w], o.x * W - d / 2, o.y * H - d / 2, d, d);
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  initOrbs($("#bgOrbs"), calm);

  // Enter: orbs rush the camera, then the site fades in. Music is already
  // trying to play; this click unlocks it if the browser blocked autoplay.
  const intro = initIntro($("#intro"), calm);
  let opened = false;
  $("#splash").onclick = () => {
    if (opened) return; opened = true;
    startMusic();
    $("#splash").classList.add("go");
    intro.fly();
    setTimeout(() => {
      $("#splash").classList.add("gone"); $("#app").classList.add("in");
      replay(views.find((x) => !x.hidden));
      setTimeout(intro.stop, 1200);
    }, calm ? 0 : 850);
  };
})();
