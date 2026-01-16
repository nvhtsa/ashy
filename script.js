document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  if (!splash) {
    console.error('No element with id="splash" found.');
    return;
  }
  if (!bgVideo) {
    console.error('No element with id="bgVideo" found.');
    return;
  }
  if (!bgMusic) {
    console.warn('No element with id="bgMusic" found (music won’t play).');
  }

  // defaults
  bgVideo.muted = true;

  // If you want the splash to truly gate entry, pause media until click:
  bgVideo.pause();
  if (bgMusic) bgMusic.pause();

  splash.addEventListener("click", async () => {
    try {
      bgVideo.muted = false;
      await bgVideo.play();
      if (bgMusic) await bgMusic.play();
    } catch (e) {
      console.log("Autoplay blocked:", e);
    }

    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 700);
  });
});
