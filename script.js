document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  const toggleVideoSoundBtn = document.getElementById("toggleVideoSound");
  const toggleMusicBtn = document.getElementById("toggleMusic");

  // Safety: if critical elements missing, do nothing rather than crash.
  if (!splash || !bgVideo) {
    console.warn("Missing splash or bgVideo element.");
    return;
  }

  // Browser-safe default: allow autoplay by keeping video muted on load.
  bgVideo.muted = true;
  // Try to ensure video is playing behind the splash.
  bgVideo.play().catch(() => {});

  function updateButtons() {
    if (toggleVideoSoundBtn) {
      toggleVideoSoundBtn.textContent = bgVideo.muted ? "Unmute Video" : "Mute Video";
    }
    if (toggleMusicBtn && bgMusic) {
      toggleMusicBtn.textContent = bgMusic.paused ? "Play Music" : "Pause Music";
    }
  }

  async function enter() {
    // Hide splash immediately so the landing is visible even if media playback fails.
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 500);

    // Unmute + (re)play video
    try {
      bgVideo.muted = false;
      await bgVideo.play();
    } catch (e) {
      // Some browsers may still block unmuted playback; user can use button.
      bgVideo.muted = true;
      console.log("Video unmute/play blocked:", e);
    }

    // Start music (optional)
    if (bgMusic) {
      try {
        await bgMusic.play();
      } catch (e) {
        // Music is often blocked; user can press the button.
        console.log("Music play blocked:", e);
      }
    }

    updateButtons();
  }

  // Click / tap
  splash.addEventListener("click", enter);

  // Keyboard accessibility: Enter/Space
  splash.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      enter();
    }
  });

  // Optional controls
  if (toggleVideoSoundBtn) {
    toggleVideoSoundBtn.addEventListener("click", async () => {
      bgVideo.muted = !bgVideo.muted;
      try {
        await bgVideo.play();
      } catch (_) {}
      updateButtons();
    });
  }

  if (toggleMusicBtn && bgMusic) {
    toggleMusicBtn.addEventListener("click", async () => {
      try {
        if (bgMusic.paused) {
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

  updateButtons();
});
