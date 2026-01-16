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

  const DEFAULT_VOL = 0.3;
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
  ];

  const npTitle = document.getElementById("npTitle");
  const npTime = document.getElementById("npTime");
  const npDur  = document.getElementById("npDur");
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
    if (npDur)  npDur.textContent = "0:00";

    updatePlayButton();

    if (autoplay && userEntered) {
      bgMusic.play().catch((e) => console.log("Autoplay blocked:", e));
    }
  }

  function nextTrack() { loadTrack(trackIndex + 1, true); }
  function prevTrack() { loadTrack(trackIndex - 1, true); }

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
});
