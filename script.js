document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  const toggleVideoSoundBtn = document.getElementById("toggleVideoSound");
  const toggleMusicBtn = document.getElementById("toggleMusic");

  const musicVolumeSlider = document.getElementById("musicVolume");
  const musicVolumeValue = document.getElementById("musicVolumeValue");

  if (!splash || !bgVideo) {
    console.warn("Missing splash or bgVideo element.");
    return;
  }

  document.querySelector(".content")?.classList.remove("visible");

  const DEFAULT_VOL = 0.1;
  let userEntered = false;
  let trackIndex = 0;

  bgVideo.muted = true;
  bgVideo.volume = 0;
  bgVideo.play().catch(() => {});

  function setMusicVolume01(v01) {
    if (!bgMusic) return;
    const clamped = Math.max(0, Math.min(1, v01));
    bgMusic.volume = clamped;

    if (musicVolumeSlider) musicVolumeSlider.value = String(Math.round(clamped * 100));
    if (musicVolumeValue) musicVolumeValue.textContent = `${Math.round(clamped * 100)}%`;
  }

  if (bgMusic) {
    bgMusic.muted = false;
    setMusicVolume01(DEFAULT_VOL);
  }

  function updateButtons() {
    if (toggleVideoSoundBtn) {
      toggleVideoSoundBtn.textContent = "Video Muted";
      toggleVideoSoundBtn.disabled = true;
      toggleVideoSoundBtn.style.opacity = "0.6";
      toggleVideoSoundBtn.style.cursor = "not-allowed";
    }

    if (toggleMusicBtn && bgMusic) {
      toggleMusicBtn.textContent = bgMusic.paused ? "Play Music" : "Pause Music";
    }
  }

  const PLAYLIST = [
    { title: "TORN – Ramzoid", src: "assets/media/track1.mp3" },
    { title: "JUST TOUCHED DOWN – Westwood", src: "assets/media/track2.mp3" },
    { title: "LIVING IN MY HEAD – Friz", src: "assets/media/track3.mp3" },
    { title: "puke! - Chris Miles", src: "assets/media/track4.mp3" },
    { title: "DENNIS TYPE BEAT - hooligan chase", src: "assets/media/track5.mp3" },
    
  ];

  const npTitle = document.getElementById("npTitle");
  const npTime = document.getElementById("npTime");
  const npDur = document.getElementById("npDur");
  const npSeek = document.getElementById("npSeek");
  const npPlay = document.getElementById("npPlay");
  const npPrev = document.getElementById("npPrev");
  const npNext = document.getElementById("npNext");

  function fmtTime(s) {
    if (!isFinite(s) || s < 0) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  function updatePlayButton() {
    if (!npPlay || !bgMusic) return;
    npPlay.textContent = bgMusic.paused ? "▶" : "⏸";
  }

  function loadTrack(i, autoplay = false) {
    if (!bgMusic || !PLAYLIST.length) return;

    trackIndex = (i + PLAYLIST.length) % PLAYLIST.length;

    bgMusic.src = PLAYLIST[trackIndex].src;
    bgMusic.load();

    if (npTitle) npTitle.textContent = PLAYLIST[trackIndex].title;
    if (npSeek) npSeek.value = "0";
    if (npTime) npTime.textContent = "0:00";
    if (npDur) npDur.textContent = "0:00";

    updatePlayButton();

    if (autoplay && userEntered) {
      bgMusic.play().catch((e) => console.log("Autoplay blocked:", e));
    }
  }

  function nextTrack() {
    loadTrack(trackIndex + 1, true);
  }
  function prevTrack() {
    loadTrack(trackIndex - 1, true);
  }

  if (bgMusic) {
    bgMusic.addEventListener("loadedmetadata", () => {
      if (npDur) npDur.textContent = fmtTime(bgMusic.duration);
    });

    bgMusic.addEventListener("timeupdate", () => {
      if (!npTime || !npSeek || !bgMusic.duration) return;
      npTime.textContent = fmtTime(bgMusic.currentTime);
      npSeek.value = String(Math.round((bgMusic.currentTime / bgMusic.duration) * 100));
    });

    bgMusic.addEventListener("play", updatePlayButton);
    bgMusic.addEventListener("pause", updatePlayButton);

    bgMusic.addEventListener("ended", () => nextTrack());
  }

  npPlay?.addEventListener("click", async () => {
    if (!bgMusic || !userEntered) return;
    try {
      if (bgMusic.paused) await bgMusic.play();
      else bgMusic.pause();
    } catch (e) {
      console.log("Play/pause blocked:", e);
    }
    updatePlayButton();
    updateButtons();
  });

  npNext?.addEventListener("click", () => {
    if (!userEntered) return;
    nextTrack();
  });

  npPrev?.addEventListener("click", () => {
    if (!userEntered) return;
    prevTrack();
  });

  npSeek?.addEventListener("input", () => {
    if (!bgMusic || !isFinite(bgMusic.duration)) return;
    bgMusic.currentTime = (Number(npSeek.value) / 100) * bgMusic.duration;
  });

  if (musicVolumeSlider && bgMusic) {
    musicVolumeSlider.addEventListener("input", () => {
      setMusicVolume01(Number(musicVolumeSlider.value) / 100);
    });
  }

  if (toggleMusicBtn && bgMusic) {
    toggleMusicBtn.addEventListener("click", async () => {
      if (!userEntered) return;
      try {
        if (bgMusic.paused) await bgMusic.play();
        else bgMusic.pause();
      } catch (e) {
        console.log("Music toggle blocked:", e);
      }
      updatePlayButton();
      updateButtons();
    });
  }

  loadTrack(0, false);

  async function enter() {
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 600);

    document.querySelector(".content")?.classList.add("visible");

    userEntered = true;

    bgVideo.muted = true;
    bgVideo.volume = 0;

    if (bgMusic) {
      try {
        setMusicVolume01(DEFAULT_VOL);
        await bgMusic.play();
      } catch (e) {
        console.log("Music play blocked:", e);
      }
    }

    updatePlayButton();
    updateButtons();
  }

  splash.addEventListener("click", async (ev) => {
    const r = document.createElement("span");
    r.className = "splash-ripple";

    const x = ev.clientX ?? window.innerWidth / 2;
    const y = ev.clientY ?? window.innerHeight / 2;

    r.style.left = `${x}px`;
    r.style.top = `${y}px`;

    splash.appendChild(r);
    setTimeout(() => r.remove(), 600);

    await enter();
  });

  splash.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      splash.click();
    }
  });

  updateButtons();

  function initFX() {
   // if (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return;

    const rainCanvas = document.getElementById("fxRain");
    const trailCanvas = document.getElementById("fxTrail");
    if (!rainCanvas || !trailCanvas) {
      console.warn("FX canvases not found. Add: <canvas id='fxRain'> and <canvas id='fxTrail'>");
      return;
    }

    const rctx = rainCanvas.getContext("2d", { alpha: true });
    const tctx = trailCanvas.getContext("2d", { alpha: true });
    if (!rctx || !tctx) return;

    const DPR = Math.min(2, window.devicePixelRatio || 1);

    function resize() {
      const w = window.innerWidth;
      const h = window.innerHeight;

      for (const c of [rainCanvas, trailCanvas]) {
        c.width = Math.floor(w * DPR);
        c.height = Math.floor(h * DPR);
        c.style.width = w + "px";
        c.style.height = h + "px";
      }

      rctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      tctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    }
    window.addEventListener("resize", resize, { passive: true });
    resize();

    const rand = (min, max) => Math.random() * (max - min) + min;

    const TRAIL_INNER = { r: 210, g: 235, b: 255 }; 
    const TRAIL_EDGE = { r: 205, g: 175, b: 255 };  

    const trail = [];
    const MAX_TRAIL = 34;         
    const TRAIL_ALPHA = 0.22;      
    const FADE_SPEED = 0.045;    

    let lastX = window.innerWidth / 2;
    let lastY = window.innerHeight / 2;
    let lastT = performance.now();

    const drops = [];
    const DROP_COUNT = 170;   
    const SPEED_MIN = 6;
    const SPEED_MAX = 14;
    const LEN_MIN = 9;
    const LEN_MAX = 20;

    let wind = 0.35;             
    let windTarget = 0.35;         
    const WIND_BASE = 0.35;
    const WIND_MAX = 3.0;           

    function initDrops() {
      drops.length = 0;
      for (let i = 0; i < DROP_COUNT; i++) {
        drops.push({
          x: rand(0, window.innerWidth),
          y: rand(0, window.innerHeight),
          v: rand(SPEED_MIN, SPEED_MAX),
          l: rand(LEN_MIN, LEN_MAX),
          a: rand(0.22, 0.45), 
        });
      }
    }
    initDrops();

    window.addEventListener(
      "pointermove",
      (e) => {
        const now = performance.now();
        const x = e.clientX;
        const y = e.clientY;

        const dt = Math.max(8, now - lastT);
        const vx = (x - lastX) / dt; 

        windTarget = WIND_BASE + vx * 18;
        windTarget = Math.max(-WIND_MAX, Math.min(WIND_MAX, windTarget));

        lastX = x;
        lastY = y;
        lastT = now;

        trail.push({
          x,
          y,
          r: rand(10, 18),
          a: TRAIL_ALPHA,
          life: 1.0,
        });
        while (trail.length > MAX_TRAIL) trail.shift();
      },
      { passive: true }
    );

    function drawRain() {
      rctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      wind += (windTarget - wind) * 0.08;

      rctx.lineWidth = 1.25;
      rctx.lineCap = "round";
      rctx.shadowColor = "rgba(200,220,255,0.25)";
      rctx.shadowBlur = 6;

      for (const d of drops) {
        
        const dx = wind * d.l;

        rctx.strokeStyle = `rgba(255,255,255,${d.a})`;
        rctx.beginPath();
        rctx.moveTo(d.x, d.y);
        rctx.lineTo(d.x + dx, d.y + d.l);
        rctx.stroke();

        d.x += wind * (d.v * 0.32);
        d.y += d.v;

        if (d.y > window.innerHeight + 30) {
          d.y = -30;
          d.x = rand(-40, window.innerWidth + 40);
        }
        if (d.x > window.innerWidth + 60) d.x = -60;
        if (d.x < -60) d.x = window.innerWidth + 60;
      }
    }

function drawTrail() {

  tctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

  for (let i = trail.length - 1; i >= 0; i--) {
    const p = trail[i];
    p.life -= FADE_SPEED;
    if (p.life <= 0) {
      trail.splice(i, 1);
      continue;
    }

    const alpha = p.a * p.life;
    const radius = p.r * (0.85 + 0.15 * p.life);

    const g = tctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius);
    g.addColorStop(0, `rgba(${TRAIL_INNER.r},${TRAIL_INNER.g},${TRAIL_INNER.b},${alpha})`);
    g.addColorStop(0.55, `rgba(${TRAIL_EDGE.r},${TRAIL_EDGE.g},${TRAIL_EDGE.b},${alpha * 0.65})`);
    g.addColorStop(1, "rgba(255,255,255,0)");

    tctx.fillStyle = g;
    tctx.beginPath();
    tctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    tctx.fill();
  }
}


    function loop() {
      drawRain();
      drawTrail();
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  initFX();
});
