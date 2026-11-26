// Switchable failures for practice pages: add ?fault=NAME to the address.
//   broken      the main button does nothing
//   slow        the main button works after a 3 second delay
//   popup       a pop-up covers the page until it is closed
//   distractor  the main button fails, but an unrelated banner appears
// Add &variant=2 for the second pop-up or banner design (default 1).
//
// Each split has its OWN designs, so a verifier cannot learn one banner in
// training and meet the same one in validation or testing. A page says which
// split it is in:  <script src="../shared/faults.js" data-split="train">
// Each page calls runMainAction() when a main button is used.
(function () {
  const params = new URLSearchParams(location.search);
  // ?broken=1 is the older way of writing ?fault=broken (used by milestone1.py).
  const fault = params.get("broken") === "1" ? "broken" : params.get("fault");
  const variant = params.get("variant") === "2" ? 1 : 0;
  const split = document.currentScript.dataset.split;

  // banner / box: where it goes and how it looks.
  // cover: the layer behind a pop-up, which blocks the whole page.
  const DESIGNS = {
    train: [
      {
        banner: "left:0;right:0;bottom:0;height:90px;padding:28px;" +
          "background:#7b2cbf;color:white;font-size:24px;text-align:center",
        bannerText: "Special offer! Subscribe to our newsletter today.",
        cover: "rgba(0,0,0,0.6)",
        box: "width:300px;margin:180px auto;background:white;color:black;" +
          "padding:24px;text-align:center",
        popupText: "We value your privacy.", close: "Close"
      },
      {
        banner: "left:0;right:0;top:0;height:46px;padding:12px;" +
          "background:#fde047;color:#111;font-size:16px;text-align:center",
        bannerText: "Planned maintenance this weekend.",
        cover: "rgba(30,41,59,0.35)",
        box: "position:absolute;left:0;right:0;bottom:0;background:#111827;" +
          "color:white;padding:34px;text-align:center",
        popupText: "This site uses cookies.", close: "Accept"
      }
    ],
    validation: [
      {
        banner: "right:18px;bottom:18px;width:250px;padding:18px;border-radius:10px;" +
          "background:#065f46;color:white;font-size:15px;box-shadow:0 4px 14px #0006",
        bannerText: "New message from the support team.",
        cover: "rgba(30,58,138,0.55)",
        box: "width:420px;margin:40px auto;background:#dbeafe;color:#1e3a8a;" +
          "padding:30px;border-radius:18px;text-align:left",
        popupText: "Would you like to take a short survey?", close: "No thanks"
      },
      {
        banner: "right:0;top:120px;width:150px;height:260px;padding:20px 14px;" +
          "background:#fb923c;color:#431407;font-size:19px",
        bannerText: "Download our mobile app.",
        cover: "rgba(255,255,255,0.75)",
        box: "position:absolute;right:0;top:0;bottom:0;width:340px;" +
          "background:#334155;color:white;padding:80px 28px",
        popupText: "Sign up for weekly tips.", close: "Dismiss"
      }
    ],
    test: [
      {
        banner: "left:18px;bottom:18px;width:340px;padding:14px;" +
          "background:white;color:#b91c1c;border:4px dashed #b91c1c;font-size:16px",
        bannerText: "Limited time: free delivery on demo items.",
        cover: "rgba(127,29,29,0.45)",
        box: "width:260px;margin:300px 0 0 60px;background:#fef2f2;color:#7f1d1d;" +
          "padding:20px;border:3px solid #7f1d1d",
        popupText: "Please confirm your region.", close: "Continue"
      },
      {
        banner: "left:25%;width:50%;top:8px;padding:10px;border-radius:30px;" +
          "background:#0e7490;color:white;font-size:14px;text-align:center",
        bannerText: "You have 3 unread notifications.",
        cover: "rgba(15,23,42,0.85)",
        box: "width:520px;margin:90px auto;background:#ecfeff;color:#164e63;" +
          "padding:60px 30px;text-align:center;font-size:22px",
        popupText: "Rate your experience.", close: "Later"
      }
    ]
  };

  if (!DESIGNS[split]) {
    throw new Error("faults.js needs data-split: train, validation or test");
  }
  const design = DESIGNS[split][variant];

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
      banner.textContent = design.bannerText;
      banner.style.cssText = "position:fixed;box-sizing:border-box;" + design.banner;
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
        "position:fixed;inset:0;z-index:10;background:" + design.cover;
      const box = document.createElement("div");
      box.style.cssText = design.box;
      const text = document.createElement("p");
      text.textContent = design.popupText;
      const close = document.createElement("button");
      close.id = "fault-popup-close";
      close.type = "button";
      close.textContent = design.close;
      // Fixed style, so the page's own button style does not apply.
      close.style.cssText = "all:revert;padding:8px 20px;cursor:pointer";
      close.addEventListener("click", () => cover.remove());
      box.append(text, close);
      cover.appendChild(box);
      document.body.appendChild(cover);
    });
  }
})();
