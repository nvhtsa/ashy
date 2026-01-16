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

const nameEl = document.getElementById("floatingName");
const nameBox = document.querySelector(".name-box");

if (nameEl && nameBox) {
  const MOVE_INTERVAL = 4000; 
  const PADDING = 20;        

  function moveName() {
    const boxRect = nameBox.getBoundingClientRect();
    const nameRect = nameEl.getBoundingClientRect();

    const maxX = boxRect.width - nameRect.width - PADDING;
    const maxY = boxRect.height - nameRect.height - PADDING;

    const x = Math.random() * maxX + PADDING / 2;
    const y = Math.random() * maxY + PADDING / 2;

    nameEl.style.transform = `translate(${x}px, ${y}px)`;
  }

  moveName();

  setInterval(moveName, MOVE_INTERVAL);
}




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
