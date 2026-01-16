document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash");
  const bgVideo = document.getElementById("bgVideo");
  const bgMusic = document.getElementById("bgMusic");

  if (!splash) {
    console.error('Missing #splash in HTML');
    return;
  }

  splash.addEventListener("click", async () => {
    // UNSTICK: hide splash no matter what
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 400);

    // Start video
    if (bgVideo) {
      bgVideo.muted = false;
      bgVideo.play().catch(console.log);
    }

    // Start music (optional)
    if (bgMusic) {
      bgMusic.play().catch(console.log);
    }
  });
});
