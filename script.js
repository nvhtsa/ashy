const bgVideo = document.getElementById("bgVideo");
const muteVideoBtn = document.getElementById("muteVideoBtn");

const bgMusic = document.getElementById("bgMusic");
const musicBtn = document.getElementById("musicBtn");

muteVideoBtn.addEventListener("click", () => {
  bgVideo.muted = !bgVideo.muted;
  muteVideoBtn.textContent = bgVideo.muted ? "Unmute Video" : "Mute Video";
});

musicBtn.addEventListener("click", async () => {
  try {
    if (bgMusic.paused) {
      await bgMusic.play();
      musicBtn.textContent = "Pause Music";
    } else {
      bgMusic.pause();
      musicBtn.textContent = "Play Music";
    }
  } catch (e) {
    console.log("Music play blocked:", e);
    alert("Your browser blocked audio until you interact with the page. Click Play Music again.");
  }
});
