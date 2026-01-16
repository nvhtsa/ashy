document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  const toggleVideoSoundBtn = document.getElementById("toggleVideoSound"); // optional
  const toggleMusicBtn = document.getElementById("toggleMusic");

  const musicVolumeSlider = document.getElementById("musicVolume");
  const musicVolumeValue = document.getElementById("musicVolumeValue");

  if (!splash || !bgVideo) {
    console.warn("Missing splash or bgVideo element.");
    return;
  }

document.querySelector(".content")?.classList.add("visible");

  bgVideo.muted = true;
  bgVideo.volume = 0;
  bgVideo.play().catch(() => {});

  const DEFAULT_VOL = 0.3;

  function setMusicVolume01(v01) {
    if (!bgMusic) return;
    const clamped = Math.max(0, Math.min(1, v01));
    bgMusic.volume = clamped;

    if (musicVolumeSlider) musicVolumeSlider.value = String(Math.round(clamped * 100));
    if (musicVolumeValue) musicVolumeValue.textContent = `${Math.round(clamped * 100)}%`;
  }

  if (bgMusic) setMusicVolume01(DEFAULT_VOL);

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

  async function enter() {
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 600);

    bgVideo.muted = true;
    bgVideo.volume = 0;
    bgVideo.play().catch(() => {});

    if (bgMusic) {
      try {
        bgMusic.muted = false;
        setMusicVolume01(DEFAULT_VOL);
        await bgMusic.play();
      } catch (e) {
        console.log("Music play blocked:", e);
      }
    }

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

(() => {
  const nameEl = document.getElementById("floatingName");
  const box = document.querySelector(".name-box");
  if (!nameEl || !box) return;

  const text = nameEl.textContent.trim();
  nameEl.textContent = "";
  const letters = [];

  for (const ch of text) {
    const span = document.createElement("span");
    span.className = "ch";
    span.textContent = ch === " " ? "\u00A0" : ch;
    nameEl.appendChild(span);
    letters.push({
      el: span,
      tx: 0, ty: 0,      
      ttx: 0, tty: 0,      
      next: 0              
    });
  }

  const MOVE_INTERVAL = 4200; 
  const EDGE_PADDING = 18; 
  const PARALLAX_MAX = 14;    
  const LERP = 0.10;

  const LETTER_MAX = 7;
  const LETTER_RETARGET_MIN = 600;
  const LETTER_RETARGET_MAX = 1400;
  const LETTER_LERP = 0.12;

  let base = { x: 0, y: 0 };    
  let par = { x: 0, y: 0 };          
  let parTarget = { x: 0, y: 0 };    
  let rafId = null;

  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  const rand = (min, max) => min + Math.random() * (max - min);

  function pickNewBase() {
    nameEl.style.transform = `translate(0px, 0px)`;

    const boxRect = box.getBoundingClientRect();
    const nameRect = nameEl.getBoundingClientRect();

    const maxX = Math.max(0, boxRect.width - nameRect.width - EDGE_PADDING);
    const maxY = Math.max(0, boxRect.height - nameRect.height - EDGE_PADDING);

    base.x = Math.random() * maxX + EDGE_PADDING / 2;
    base.y = Math.random() * maxY + EDGE_PADDING / 2;
  }

  function setParallaxFromEvent(clientX, clientY) {
    const r = box.getBoundingClientRect();
    const nx = (clientX - (r.left + r.width / 2)) / (r.width / 2);   
    const ny = (clientY - (r.top + r.height / 2)) / (r.height / 2); 

    parTarget.x = clamp(nx, -1, 1) * PARALLAX_MAX;
    parTarget.y = clamp(ny, -1, 1) * PARALLAX_MAX;
  }

  box.addEventListener("mousemove", (e) => setParallaxFromEvent(e.clientX, e.clientY));
  box.addEventListener("mouseleave", () => { parTarget.x = 0; parTarget.y = 0; });

  box.addEventListener("touchmove", (e) => {
    if (!e.touches || !e.touches[0]) return;
    setParallaxFromEvent(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: true });

  box.addEventListener("touchend", () => { parTarget.x = 0; parTarget.y = 0; });

  function retargetLetter(letter, now) {
    letter.ttx = rand(-LETTER_MAX, LETTER_MAX);
    letter.tty = rand(-LETTER_MAX, LETTER_MAX);
    letter.next = now + rand(LETTER_RETARGET_MIN, LETTER_RETARGET_MAX);
  }

  function animate(now) {

    par.x += (parTarget.x - par.x) * LERP;
    par.y += (parTarget.y - par.y) * LERP;

    const boxRect = box.getBoundingClientRect();
    const nameRect = nameEl.getBoundingClientRect();

    const maxX = Math.max(0, boxRect.width - nameRect.width);
    const maxY = Math.max(0, boxRect.height - nameRect.height);

    const x = clamp(base.x + par.x, 0, maxX);
    const y = clamp(base.y + par.y, 0, maxY);

    nameEl.style.transform = `translate(${x}px, ${y}px)`;

    for (const L of letters) {
      if (!L.next) retargetLetter(L, now);
      if (now >= L.next) retargetLetter(L, now);

      L.tx += (L.ttx - L.tx) * LETTER_LERP;
      L.ty += (L.tty - L.ty) * LETTER_LERP;

      L.el.style.transform = `translate3d(${L.tx}px, ${L.ty}px, 0)`;
    }

    rafId = requestAnimationFrame(animate);
  }

  pickNewBase();
  setInterval(pickNewBase, MOVE_INTERVAL);

  if (rafId) cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(animate);
})();





  if (toggleMusicBtn && bgMusic) {
    toggleMusicBtn.addEventListener("click", async () => {
      try {
        if (bgMusic.paused) {
          bgMusic.muted = false;
          const v = musicVolumeSlider ? Number(musicVolumeSlider.value) / 100 : DEFAULT_VOL;
          setMusicVolume01(v);
          await bgMusic.play();
        } else {
          bgMusic.pause();
        }
      } catch (e) {
        console.log("Music toggle blocked:", e);
      }
      updateButtons();
    });
  }

  if (musicVolumeSlider && bgMusic) {
    musicVolumeSlider.addEventListener("input", () => {
      const v01 = Number(musicVolumeSlider.value) / 100;
      setMusicVolume01(v01);
    });
  }

  updateButtons();
});
