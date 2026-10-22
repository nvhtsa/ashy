(() => {
  const frames = [
    "Ashtyn",
    "aShtyn",
    "asHtyn",
    "ashTyn",
    "ashtYn",
    "ashtyN",
    "ashtYn",
    "ashTyn",
    "asHtyn",
    "aShtyn"
  ];

  function startWordmarkAnimation() {
    const mark = document.querySelector(".mark");
    if (!mark) {
      console.warn("ASHTYN wordmark animation: .mark element not found.");
      return;
    }

    let frame = 0;
    mark.textContent = frames[frame];
    window.setInterval(() => {
      frame = (frame + 1) % frames.length;
      mark.textContent = frames[frame];
    }, 350);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startWordmarkAnimation, { once: true });
  } else {
    startWordmarkAnimation();
  }
})();
