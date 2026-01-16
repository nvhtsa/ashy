document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  const toggleVideoSoundBtn = document.getElementById("toggleVideoSound"); // optional
  const toggleMusicBtn = document.getElementById("toggleMusic");

  // NEW: volume UI
  const musicVolumeSlider = document.getElementById("musicVolume");
  const musicVolumeValue = document.getElementById("musicVolumeValue");

  // Safety
  if (!splash || !bgVideo) {
    console.warn("Missing splash or bgVideo element.");
    return;
  }

  /* ---------------------------
     ALWAYS MUTE MP4 (VIDEO) AUDIO
     --------------------------- */
  bgVideo.muted = true;
  bgVideo.volume = 0;
  bgVideo.play().catch(() => {});

  /* ---------------------------
     MP3 DEFAULT VOLUME (30%)
     --------------------------- */
  const DEFAULT_VOL = 0.3;

  function setMusicVolume01(v01) {
    if (!bgMusic) return;
    const clamped = Math.max(0, Math.min(1, v01));
    bgMusic.volume = clamped;

    // Update UI (0–100)
    if (musicVolumeSlider) musicVolumeSlider.value = String(Math.round(clamped * 100));
    if (musicVolumeValue) musicVolumeValue.textContent = `${Math.round(clamped * 100)}%`;
  }

  // Initialize slider/UI to 30%
  if (bgMusic) setMusicVolume01(DEFAULT_VOL);

  function updateButtons() {
    // Video audio locked off
    if (toggleVideoSoundBtn) {
      toggleVideoSoundBtn.textContent = "Video Muted";
      toggleVideoSoundBtn.disabled = true;
      toggleVideoSoundBtn.style.opacity = "0.6";
      toggleVideoSoundBtn.style.cursor = "not-allowed";
    }

    // Music state
    if (toggleMusicBtn && bgMusic) {
      toggleMusicBtn.textContent = bgMusic.paused ? "Play Music" : "Pause Music";
    }
  }

  async function enter() {
    // Reveal site
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 600);

    // Keep video silent forever
    bgVideo.muted = true;
    bgVideo.volume = 0;
    bgVideo.play().catch(() => {});

    // Start MP3 at 30% volume
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

 // Enter via click/tap (with subtle ripple)
splash.addEventListener("click", async (ev) => {
  // Create ripple
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



  // Toggle music button
  if (toggleMusicBtn && bgMusic) {
    toggleMusicBtn.addEventListener("click", async () => {
      try {
        if (bgMusic.paused) {
          bgMusic.muted = false;
          // Use current slider value if available, else default
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

  // Volume slider (controls MP3 only)
  if (musicVolumeSlider && bgMusic) {
    musicVolumeSlider.addEventListener("input", () => {
      const v01 = Number(musicVolumeSlider.value) / 100;
      setMusicVolume01(v01);
    });
  }

  updateButtons();
});
