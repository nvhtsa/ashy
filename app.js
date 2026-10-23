(() => {
  const C = window.SITE, $ = (s) => document.querySelector(s);
  if (window.PLAYLIST && window.PLAYLIST.length) C.playlist = window.PLAYLIST;
  const el = (tag, props = {}, ...kids) => {
    const n = Object.assign(document.createElement(tag), props); n.append(...kids); return n;
  };

  C.socials.forEach((s) => $("#socials").append(
    el("a", { href: s.url, target: "_blank", rel: "noreferrer noopener" },
      el("img", { src: `assets/icons/${s.icon}.svg`, alt: "" }), s.name)));

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
  const chevron = () => {
    const s = el("span", { className: "fold-chev" });
    s.innerHTML = '<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6l5 5 5-5"/></svg>';
    return s;
  };
  let foldId = 0;
  const cards = (target, groups, fold) => groups.forEach((g) => {
    const body = [
      el("dl", {}, ...(g.items || []).flatMap(([k, v]) => [el("dt", { textContent: k }), el("dd", { textContent: v })])),
      ...(g.blocks || []).map(block)];
    if (!fold) return target.append(el("section", { className: "group" }, el("h2", { textContent: g.group }), ...body));
    const id = `fold${++foldId}`, count = (g.items || []).length + (g.blocks || []).length;
    const open = g.open === true;
    const btn = el("button", { type: "button", id: `${id}-btn` },
      el("span", { className: "fold-name", textContent: g.group }),
      el("span", { className: "fold-meta", textContent: `${count} setting${count === 1 ? "" : "s"}` }), chevron());
    btn.setAttribute("aria-expanded", String(open)); btn.setAttribute("aria-controls", id);
    const card = el("section", { className: "group fold" + (open ? " open" : "") },
      el("h2", { className: "fold-title" }, btn),
      el("div", { className: "fold-panel", id, role: "region" },
        el("div", { className: "fold-inner" }, el("div", { className: "fold-body" }, ...body))));
    card.querySelector(".fold-panel").setAttribute("aria-labelledby", `${id}-btn`);
    btn.onclick = () => btn.setAttribute("aria-expanded", String(card.classList.toggle("open")));
    target.append(card);
  });
  cards($("#gearList"), C.gear);
  cards($("#settingsList"), C.settings || [], true);

  const views = [...document.querySelectorAll("[data-view]")].filter((v) => v.tagName === "SECTION");
  const tabs = [...document.querySelectorAll("nav a")];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const replay = (node, slide) => {
    node.classList.remove("enter", "slide"); void node.offsetWidth;
    node.classList.add("enter"); if (slide) node.classList.add("slide");
  };
  const bloom = $("#bloom");
  const PAGE_NAMES = new Set(["gear", "settings", "listening"]);
  const pathFor = (page) => page === "home" ? "/" : `/${page}`;
  const pageFromLocation = () => {
    const last = location.pathname.split("/").filter(Boolean).pop() || "home";
    return PAGE_NAMES.has(last) ? last : "home";
  };
  let routeId = 0;
  const TITLES = {
  home: "ASHTYN®",
  gear: "Gear | ASHTYN®",
  settings: "Settings | ASHTYN®",
  listening: "Listening | ASHTYN®"
};

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
    const fancy = !!(cur && animate && !calm);
    if (fancy) {
      const pill = tabs.find((a) => (a.pathname.replace(/\/$/, "") || "/") === pathFor(v));
      if (pill) {
        const r = pill.getBoundingClientRect();
        bloom.style.left = r.left + r.width / 2 + "px"; bloom.style.top = r.top + r.height / 2 + "px";
      }
      bloom.classList.remove("go"); void bloom.offsetWidth; bloom.classList.add("go");
      cur.classList.add("leaving");
      await wait(280);
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



  const audio = $("#audio"), title = $("#pTitle"), artist = $("#pArtist"), playBtn = $("#pPlay"), seek = $("#pSeek"), vol = $("#pVol"),
    cur = $("#pCur"), dur = $("#pDur"), mute = $("#pMute");
  const ICON_PLAY = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13l11-6.5z"/></svg>';
  const ICON_PAUSE = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"/></svg>';
  const fmt = (s) => (isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "0:00");
  const fill = (inp) => inp.style.setProperty("--p", (inp.value / inp.max) * 100 + "%");
  let i = 0, actx = null, analyser = null, gain = null, freq = null;
  const BANDS = 56;
  const fx = {
    bass: 0, mid: 0, high: 0, kick: 0, hit: false, k: 1, live: false, last: 0, lo: null, hi: null,
    bands: new Float32Array(BANDS), ref: new Float32Array(BANDS), tmp: new Float32Array(BANDS)
  };
  let bassAvg = 0, lastHit = 0;
  try {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    const src = actx.createMediaElementSource(audio);
    analyser = actx.createAnalyser(); analyser.fftSize = 2048; analyser.smoothingTimeConstant = .7;
    analyser.minDecibels = -95; analyser.maxDecibels = -6;
    gain = actx.createGain();
    src.connect(analyser); src.connect(gain); gain.connect(actx.destination);
    freq = new Uint8Array(analyser.frequencyBinCount);
  } catch (e) { actx = analyser = gain = null; }

  function mapBands() {
    if (!analyser) return;
    const binHz = actx.sampleRate / analyser.fftSize, top = analyser.frequencyBinCount - 1;
    const lo = [], hi = [];
    for (let b = 0; b < BANDS; b++) {
      const e0 = Math.max(1, Math.round(55 * Math.pow(12000 / 55, b / BANDS) / binHz));
      const e1 = Math.max(1, Math.round(55 * Math.pow(12000 / 55, (b + 1) / BANDS) / binHz));
      lo.push(Math.min(e0, top));
      hi.push(Math.min(top + 1, Math.max(e0 + 1, e1)));
    }
    fx.lo = lo; fx.hi = hi;
  }

  function meter(now) {
    if (!fx.last) fx.last = now;
    const dt = Math.min(.05, Math.max(0, (now - fx.last) / 1000));
    fx.last = now;
    const vf = gain ? gain.gain.value : audio.volume;
    fx.k = vf < .15 ? .2 + (vf / .15) * .8 : 1 + (vf - .15) * 1.41;
    fx.live = !!(analyser && !audio.paused && actx && actx.state === "running");
    const bands = fx.bands, ref = fx.ref, tmp = fx.tmp;

    if (fx.live) {
      analyser.getByteFrequencyData(freq);
      if (!fx.lo) mapBands();
      const follow = 1 - Math.exp(-dt / .55);
      for (let b = 0; b < BANDS; b++) {
        let sum = 0, c = 0;
        for (let k = fx.lo[b]; k < fx.hi[b]; k++) { sum += freq[k]; c++; }
        const raw = c ? sum / c / 255 : 0;
        const music = raw < .06 ? 0 : (raw - .06) / .94;
        ref[b] += (music - ref[b]) * follow;
        const u = b / (BANDS - 1);
        const shape = .26 + .64 * Math.pow(1 - u, .75);
        const jump = 3.2 * Math.pow(1 - u, 1.3);
        bands[b] = Math.max(0, Math.min(1, shape * (.42 + music * .92) * .7 + (music - ref[b]) * jump));
      }
      for (let b = 0; b < BANDS; b++) tmp[b] = b
        ? (bands[b - 1] + bands[b] * 2 + bands[Math.min(BANDS - 1, b + 1)]) * .25
        : bands[0];
      bands.set(tmp);
    } else {
      const fall = Math.pow(.2, dt);
      for (let b = 0; b < BANDS; b++) { bands[b] *= fall; ref[b] *= fall; }
    }

    let low = 0, high = 0, mid = 0;
    for (let b = 0; b < 10; b++) low += bands[b];
    for (let b = 10; b < 30; b++) mid += bands[b];
    for (let b = 30; b < BANDS; b++) high += bands[b];
    low /= 10; mid /= 20; high /= BANDS - 30;

    const ease = (cur, next, up, down) => cur + (next - cur) * (1 - Math.exp(-dt / (next > cur ? up : down)));
    fx.bass = ease(fx.bass, Math.min(1, low * fx.k), .03, .16);
    fx.mid = ease(fx.mid, Math.min(1, mid * fx.k), .05, .22);
    fx.high = ease(fx.high, Math.min(1, high * fx.k), .04, .2);

    const dev = low - bassAvg;
    bassAvg += (low - bassAvg) * (1 - Math.exp(-dt / .7));
    fx.hit = dev > .07 && now - lastHit > 140;
    if (fx.hit) { fx.kick = Math.min(1, dev * 4.5); lastHit = now; }
    fx.kick *= Math.pow(.86, dt * 60);
  }

  const setVol = () => {
    const v = vol.value / 100; if (gain) gain.gain.value = v; else audio.volume = v;
    fill(vol); mute.classList.toggle("off", v === 0);
  };
  let lastVol = 15;
  mute.onclick = () => { if (+vol.value > 0) { lastVol = +vol.value; vol.value = 0; } else vol.value = lastVol || 15; setVol(); };
  vol.oninput = setVol; setVol();

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
    audio.src = C.playlist[i].src;
    const [name, ...by] = C.playlist[i].title.split(/\s+[–—-]\s+/);
    title.textContent = name; artist.textContent = by.join(" – ");
    seek.value = 0; fill(seek); cur.textContent = "0:00"; dur.textContent = "0:00";
    mark();
    if (play) startMusic();
  }
  playBtn.onclick = () => { if (audio.paused) startMusic(); else { unbind(); audio.pause(); } };
  $("#pNext").onclick = () => load(i + 1, true);
  $("#pPrev").onclick = () => load(i - 1, true);
  audio.onplay = audio.onpause = () => {
    playBtn.innerHTML = audio.paused ? ICON_PLAY : ICON_PAUSE;
    playerEl.classList.toggle("playing", !audio.paused);
  };
  audio.onended = () => load(i + 1, true);
  audio.ontimeupdate = () => {
    if (audio.duration) seek.value = (audio.currentTime / audio.duration) * 100;
    fill(seek); cur.textContent = fmt(audio.currentTime);
  };
  audio.onloadedmetadata = () => (dur.textContent = fmt(audio.duration));
  seek.oninput = () => {
    if (audio.duration) audio.currentTime = (seek.value / 100) * audio.duration;
    fill(seek); cur.textContent = fmt(audio.currentTime);
  };
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

  (function initViz() {
    const canvas = $("#viz");
    if (!canvas || !canvas.getContext) return;
    const vctx = canvas.getContext("2d");
    const PAD = 46, BAR = 2, GAP = 3;
    const MAX = 34, LOW_SPAN = 24;           
    let dpr = 1, ox = 0, oy = 0, bars = [], runs = [], raf = 0, pending = 0;
    let env = new Float32Array(0), target = new Float32Array(0), smooth = new Float32Array(0), ease = new Float32Array(0);
    let mean = 0, last = performance.now(), clock = 0;

    function build(w, h, r) {
      const hw = w / 2, hh = h / 2, rad = Math.max(0, Math.min(r, hw, hh));
      const x0 = -hw + rad, span = Math.max(1, (hw - rad) * 2);
      const n = Math.max(6, Math.round(span / (BAR + GAP)));
      const curve = Math.max(1, rad * 1.4), step = span / n;
      bars = []; runs = [];
      let runStart = 0;
      const cut = () => { if (bars.length > runStart) runs.push([runStart, bars.length]); runStart = bars.length; };
      for (let i = 0; i < n; i++) {
        const x = x0 + ((i + .5) / n) * span;
        const near = Math.min(x - x0, x0 + span - x) - step / 2;
        const t = Math.max(0, Math.min(1, near / curve));
        const cap = Math.sqrt(1 - (1 - t) * (1 - t));
        const edge = Math.abs((i + .5) / n - .5) * 2; 
        bars.push({ x, y: -hh, nx: 0, ny: -1, u: edge, cap });
      }
      cut();
      const len = bars.length;
      env = new Float32Array(len); target = new Float32Array(len);
      smooth = new Float32Array(len); ease = new Float32Array(len);
    }

    function layout() {
      const rect = playerEl.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      dpr = Math.min(2, devicePixelRatio || 1);
      const rad = parseFloat(getComputedStyle(playerEl).borderTopLeftRadius) || 22;
      const vw = document.documentElement.clientWidth || innerWidth;
      const left = Math.max(0, Math.round(rect.left));
      const right = Math.min(vw, Math.round(rect.right));
      const top = Math.max(0, Math.round(rect.top - PAD));
      const W = Math.max(1, right - left), H = Math.max(1, Math.round(rect.top - top + 4));
      canvas.style.left = left + "px"; canvas.style.top = top + "px";
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      const cx = rect.left + rect.width / 2, mid = rect.top + rect.height / 2;
      ox = cx - left; oy = mid - top;
      build(rect.width, rect.height, rad);
    }

    function frame(now) {
      const dt = Math.min(.05, (now - last) / 1000); last = now; clock += dt;
      vctx.setTransform(1, 0, 0, 1, 0, 0);
      vctx.clearRect(0, 0, canvas.width, canvas.height);
      vctx.setTransform(dpr, 0, 0, dpr, ox * dpr, oy * dpr);
      const live = fx.live;
      const n = bars.length;

      for (let i = 0; i < n; i++) {
        const s = Math.pow(bars[i].u, 2.1) * LOW_SPAN, a = s | 0, f = s - a;
        const v = Math.min(1, (fx.bands[a] * (1 - f) + fx.bands[Math.min(BANDS - 1, a + 1)] * f) * fx.k);
        target[i] = Math.pow(v, 1.35); 
      }
      for (let i = 0; i < n; i++) {
        const p0 = target[i ? i - 1 : 0], p2 = target[i < n - 1 ? i + 1 : n - 1];
        smooth[i] = (p0 + target[i] * 2 + p2) * .25;
      }

      const kUp = 1 - Math.exp(-dt / .022), kDown = 1 - Math.exp(-dt / .18);
      const kick = fx.kick;
      let total = 0;
      for (let i = 0; i < n; i++) {
        const t = smooth[i];
        env[i] += (t - env[i]) * (t > env[i] ? kUp : kDown);
        const idle = .026 + .014 * Math.sin(clock * 1.2 + bars[i].u * 8); 
        const v = Math.min(1, env[i] * (1.08 + kick * .55) + (live ? 0 : idle)) * bars[i].cap;
        ease[i] = v;
        total += v;
      }
      mean += (total / Math.max(1, n) - mean) * (1 - Math.exp(-dt / .12));
      const grad = vctx.createLinearGradient(0, -MAX - 40, 0, 0);
      grad.addColorStop(0, `rgba(150,110,255,${(.1 + Math.min(.24, mean * .6)).toFixed(3)})`);
      grad.addColorStop(.55, `rgba(130,90,240,${(.05 + Math.min(.14, mean * .34)).toFixed(3)})`);
      grad.addColorStop(1, "rgba(109,61,240,0)");
      vctx.fillStyle = grad;
      for (const [a0, a1] of runs) {
        vctx.beginPath();
        vctx.moveTo(bars[a0].x, bars[a0].y);
        for (let i = a0 + 1; i < a1; i++) vctx.lineTo(bars[i].x, bars[i].y);
        for (let i = a1 - 1; i >= a0; i--) {
          const b = bars[i], l = 4.5 + ease[i] * MAX + BAR / 2;
          vctx.lineTo(b.x + b.nx * l, b.y + b.ny * l);
        }
        vctx.closePath();
        vctx.fill();
      }

      vctx.lineCap = "round"; vctx.lineWidth = 1;
      vctx.strokeStyle = `rgba(167,139,250,${(.07 + Math.min(.3, fx.bass * .4 + fx.kick * .3)).toFixed(3)})`;
      for (const [a0, a1] of runs) {
        vctx.beginPath();
        for (let i = a0; i < a1; i++) (i === a0 ? vctx.moveTo(bars[i].x, bars[i].y) : vctx.lineTo(bars[i].x, bars[i].y));
        vctx.stroke();
      }

      vctx.lineWidth = BAR;
      for (let q = 0; q < 4; q++) {
        const hot = q >= 2 ? "232,224,255" : "167,139,250";
        vctx.strokeStyle = `rgba(${hot},${(.1 + ((q + 1) / 4) * .62).toFixed(3)})`;
        vctx.beginPath();
        for (let i = 0; i < n; i++) {
          if (Math.min(3, (ease[i] * 4) | 0) !== q) continue;
          const b = bars[i], l = 2 + ease[i] * MAX;
          vctx.moveTo(b.x + b.nx * 2.5, b.y + b.ny * 2.5);
          vctx.lineTo(b.x + b.nx * (2.5 + l), b.y + b.ny * (2.5 + l));
        }
        vctx.stroke();
      }

      vctx.lineJoin = "round"; vctx.lineCap = "round";
      for (let pass = 0; pass < 2; pass++) {
        vctx.lineWidth = pass ? 1.4 : 6;
        vctx.strokeStyle = `rgba(226,216,255,${(pass
          ? .28 + Math.min(.5, mean * 1.1)
          : .06 + Math.min(.12, mean * .3)).toFixed(3)})`;
        for (const [a0, a1] of runs) {
          vctx.beginPath();
          for (let i = a0; i < a1; i++) {
            const b = bars[i], l = 4.5 + ease[i] * MAX + BAR / 2;
            if (i === a0) vctx.moveTo(b.x, b.y - l);
            else vctx.lineTo(b.x, b.y - l);
          }
          vctx.stroke();
        }
      }
      if (!calm) raf = requestAnimationFrame(frame);
    }
    const relayout = () => { cancelAnimationFrame(pending); pending = requestAnimationFrame(layout); };
    addEventListener("resize", relayout);
    if (window.ResizeObserver) new ResizeObserver(relayout).observe(playerEl);
    playerEl.addEventListener("animationend", relayout);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout).catch(() => {});
    layout();
    raf = requestAnimationFrame(frame);
  })();

  load(Math.floor(Math.random() * C.playlist.length), true); 

  const logo = document.querySelector(".logo");
  function analyse(now) {
    meter(now);
    if (logo && !calm) {
      const sc = 1 + fx.bass * .075 + fx.kick * .11, sh = Math.min(30, fx.kick * fx.kick * 12);
      logo.style.transform = `translate(${(Math.random() - .5) * sh}px,${(Math.random() - .5) * sh}px) scale(${sc})`;
      logo.style.filter = `drop-shadow(0 0 22px rgba(255,255,255,${.06 + fx.bass * .3 + fx.kick * .4})) ` +
        `drop-shadow(0 0 44px rgba(109,61,240,${.45 + fx.bass * .3})) drop-shadow(0 0 70px rgba(180,200,255,.12))`;
    }
    requestAnimationFrame(analyse);
  }
  requestAnimationFrame(analyse);

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
      const B = still ? 0 : fx.bass * .12, K = still ? 0 : fx.kick * .12;

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

  (function initGlow() {
    if (calm || !matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const glow = $("#cursorGlow");
    let x = -400, y = -400;
    addEventListener("pointermove", (e) => {
      if (e.pointerType === "touch") return;
      x = e.clientX; y = e.clientY; glow.classList.add("on");
    }, { passive: true });
    document.documentElement.addEventListener("mouseleave", () => glow.classList.remove("on"));
    (function loop() {
      glow.style.transform = `translate3d(${x}px,${y}px,0) scale(${1 + fx.bass * .1 + fx.kick * .04})`;
      requestAnimationFrame(loop);
    })();
  })();

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
