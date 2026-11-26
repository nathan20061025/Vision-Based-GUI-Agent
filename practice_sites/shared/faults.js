// Switchable failures for practice pages: add ?fault=NAME to the address.
//   broken      the main button does nothing
//   slow        the main button works after a 3 second delay
//   popup       a pop-up covers the page until it is closed
//   distractor  the main button fails, but an unrelated banner appears
// Each page calls runMainAction() when a main button is used.
(function () {
  const params = new URLSearchParams(location.search);
  // ?broken=1 is the older way of writing ?fault=broken (used by milestone1.py).
  const fault = params.get("broken") === "1" ? "broken" : params.get("fault");

  window.runMainAction = function (action) {
    if (fault === "broken") return;
    if (fault === "slow") {
      setTimeout(action, 3000);
      return;
    }
    if (fault === "distractor") {
      if (document.getElementById("distractor")) return;
      const banner = document.createElement("div");
      banner.id = "distractor";
      banner.textContent = "Special offer! Subscribe to our newsletter today.";
      banner.style.cssText = "position:fixed;left:0;right:0;bottom:0;height:90px;" +
        "background:#7b2cbf;color:white;font-size:24px;padding:28px;text-align:center";
      document.body.appendChild(banner);
      return;
    }
    action();
  };

  if (fault === "popup") {
    window.addEventListener("DOMContentLoaded", () => {
      const cover = document.createElement("div");
      cover.id = "fault-popup";
      cover.style.cssText =
        "position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10";
      cover.innerHTML =
        '<div style="width:300px;margin:180px auto;background:white;color:black;' +
        'padding:24px;text-align:center"><p>We value your privacy.</p>' +
        '<button id="fault-popup-close" type="button">Close</button></div>';
      document.body.appendChild(cover);
      document.getElementById("fault-popup-close")
        .addEventListener("click", () => cover.remove());
    });
  }
})();
