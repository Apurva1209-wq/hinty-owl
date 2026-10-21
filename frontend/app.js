(function () {
  "use strict";
  var LOCAL = ["localhost", "127.0.0.1", ""].indexOf(location.hostname) !== -1;
  var API = LOCAL ? "http://127.0.0.1:5000" : (window.API_URL || "").replace(/\/$/, "");

  var $ = function (id) { return document.getElementById(id); };
  var chat = $("chat"), owl = $("owl"), input = $("q"), sendBtn = $("send"), statusEl = $("status");
  var subject = "Maths", stars = 0, history = [], lastQ = "";

  // subject chips
  document.querySelectorAll(".chip").forEach(function (c) {
    c.addEventListener("click", function () {
      document.querySelectorAll(".chip").forEach(function (x) { x.classList.remove("active"); });
      c.classList.add("active");
      subject = c.getAttribute("data-s");
      input.focus();
    });
  });

  function add(text, who) {
    var d = document.createElement("div");
    d.className = "msg " + who;
    d.textContent = text;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
    return d;
  }

  function celebrate() {
    stars++;
    $("stars").textContent = stars;
    var s = document.createElement("div");
    s.className = "pop-star";
    s.textContent = ["⭐", "🎉", "🌟", "✨"][stars % 4];
    s.style.left = 30 + Math.random() * 40 + "%";
    s.style.bottom = "25%";
    document.body.appendChild(s);
    setTimeout(function () { s.remove(); }, 1000);
  }

  function getHint(question, level) {
    sendBtn.disabled = true;
    owl.classList.add("think");
    var thinking = add("Hinty is thinking… 🤔", "bot");
    return fetch(API + "/api/hint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        grade: $("grade").value,
        subject: subject,
        level: level,
        history: history
      })
    })
      .then(function (res) { return res.json().catch(function () { return {}; }); })
      .then(function (data) {
        thinking.remove();
        if (data.hint) {
          add(data.hint, "bot");
          history.push({ role: "user", content: question }, { role: "assistant", content: data.hint });
          history = history.slice(-6);
          celebrate();
          $("levels").hidden = level >= 3;
        } else {
          add(data.error || "Oops! Something went wrong 🙈 Try again!", "bot");
        }
      })
      .catch(function (err) {
        console.error(err);
        thinking.remove();
        add("I can't reach my brain right now 🛜 Please make sure the backend is running.", "bot");
      })
      .then(function () {
        sendBtn.disabled = false;
        owl.classList.remove("think");
        input.focus();
      });
  }

  // The form submit handles BOTH the button click and pressing Enter.
  // There is NO keydown/keypress handler, so typing can never be blocked.
  $("askForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q || sendBtn.disabled) return;
    input.value = "";
    lastQ = q;
    add(q, "user");
    getHint(q, 1);
  });

  document.querySelectorAll("#levels button").forEach(function (b) {
    b.addEventListener("click", function () {
      if (!lastQ || sendBtn.disabled) return;
      add(b.textContent, "user");
      getHint(lastQ, parseInt(b.getAttribute("data-l"), 10));
    });
  });

  // status check so you can instantly see if the backend is reachable
  fetch(API + "/")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var ok = d.gemini_key_set || d.groq_key_set;
      statusEl.textContent = ok ? "Hinty's brain is online ✅" : "Backend is on, but no API key is set ⚠️";
    })
    .catch(function () { statusEl.textContent = "Hinty's brain is offline ❌ (start the backend)"; });

  input.focus();
})();
