/* P2-04w — Guided project intake, not a live language model.
 * Browser memory only. No fetch, WebSocket, remote generation, auto-send,
 * localStorage/sessionStorage, HTML injection or retained conversation.
 */
(() => {
  "use strict";
  const transcript = document.getElementById("project-chat-messages");
  const input = document.getElementById("project-chat-input");
  const send = document.getElementById("project-chat-send");
  const edit = document.getElementById("project-chat-edit");
  const restart = document.getElementById("project-chat-new");
  const progress = document.getElementById("project-chat-progress");
  const prompts = document.getElementById("project-chat-suggestions");
  const notice = document.getElementById("project-chat-notice");
  const summary = document.getElementById("project-chat-summary");
  const summaryText = document.getElementById("project-chat-summary-text");
  const summaryTitle = document.getElementById("project-chat-summary-title");
  const email = document.getElementById("project-chat-email");
  const shareNote = document.getElementById("project-chat-share-note");
  const copied = document.getElementById("project-chat-copy-status");
  if (!transcript || !input || !send || !progress || !summary || !restart) return;

  const QUESTIONS = Object.freeze([
    {
      key: "idea", name: "Project idea", minimum: 15, maximum: 1800,
      question: "What are you hoping to build, improve, or solve? Describe the problem in your own words."
    },
    {
      key: "outcome", name: "Desired outcome", minimum: 10, maximum: 1200,
      question: "What would success look like for your business or the people using this solution?"
    },
    {
      key: "audience", name: "Audience", minimum: 4, maximum: 350,
      question: "Who will use or benefit from this project—customers, a team, or a particular community?"
    },
    {
      key: "timeline", name: "Timeline", minimum: 3, maximum: 180,
      question: "When would you ideally like to begin or see a useful first version? An estimate is fine."
    },
    {
      key: "constraints", name: "Requirements & constraints", minimum: 2, maximum: 1000,
      question: "Any important constraints—budget, accessibility, security, integrations, languages or approvals? You can simply write “None yet”."
    }
  ]);
  const STARTERS = Object.freeze({
    creative: {
      service: "Product Design & Experience",
      idea: "I want to create original visuals and narrated video content for a business campaign."
    },
    automation: {
      service: "AI Systems & Automation",
      idea: "I want to reduce repetitive business tasks and give my team a clearer workflow."
    },
    product: {
      service: "Software & Digital Products",
      idea: "I want to build a mobile or web product that solves a real customer problem."
    },
    experience: {
      service: "Product Design & Experience",
      idea: "I want to improve the usability and visual experience of an existing digital product."
    },
    security: {
      service: "Cybersecurity & Quality",
      idea: "I need an authorized security review of a mobile application and its backend API."
    }
  });
  const SERVICES = new Set([
    ...Object.values(STARTERS).map(item => item.service),
    "Cloud & DevOps", "Data & Decision Intelligence", "Still exploring"
  ]);
  const BUSINESS_EMAIL = "metaautomating@gmail.com";
  let answerIndex = 0;
  let answers = {};
  let currentBrief = "";
  let service = "Still exploring";

  try {
    const requested = new URLSearchParams(window.location.search).get("service");
    if (requested && SERVICES.has(requested)) service = requested;
  } catch {
    // Invalid URL metadata never prevents local project intake.
  }

  const advanced = document.getElementById("project-chat-alternative");
  function openStructuredLink() {
    if (advanced && window.location.hash === "#brief-form") {
      advanced.open = true;
    }
  }
  openStructuredLink();
  window.addEventListener("hashchange", openStructuredLink);

  function message(who, content) {
    const outer = document.createElement("div");
    outer.className = "project-chat-message project-chat-" + who;
    if (who === "assistant") {
      const avatar = document.createElement("span");
      avatar.className = "project-chat-avatar";
      avatar.setAttribute("aria-hidden", "true");
      avatar.textContent = "✳";
      outer.appendChild(avatar);
    }
    const bubble = document.createElement("div");
    bubble.className = "project-chat-bubble";
    const text = document.createElement("p");
    text.textContent = content;
    bubble.appendChild(text);
    outer.appendChild(bubble);
    transcript.appendChild(outer);
    transcript.scrollTop = transcript.scrollHeight;
  }
  function error(text) {
    notice.textContent = text;
    notice.hidden = !text;
  }
  function update() {
    const done = answerIndex >= QUESTIONS.length;
    input.disabled = done;
    send.disabled = done;
    edit.hidden = answerIndex === 0;
    prompts.hidden = answerIndex !== 0;
    if (done) {
      progress.textContent = "Brief prepared · Review before sending";
    } else {
      const stage = QUESTIONS[answerIndex];
      progress.textContent = "Step " + (answerIndex + 1) + " of " +
        QUESTIONS.length + " · " + stage.name;
      input.placeholder = answerIndex === 0
        ? "Describe your project idea..."
        : "Your answer to: " + stage.name;
      input.maxLength = stage.maximum;
    }
  }
  const sanitizeText = text => String(text).replace(/\r\n?/g, "\n").trim();

  function composeEmailHref(brief) {
    const subject = "MetaAutomate | Project discovery inquiry";
    const head = "Hello MetaAutomate,\n\nPlease review my project brief:\n\n";
    const tail = "\n\nPlease reply with suitable next steps.\nThank you.";
    const overflow = "\n\n[Brief shortened for email link. Attach the downloaded complete .txt file.]";
    const make = (text, shortened) =>
      "mailto:" + BUSINESS_EMAIL + "?subject=" + encodeURIComponent(subject) +
      "&body=" + encodeURIComponent(head + text + (shortened ? overflow : "") + tail);
    const direct = make(brief, false);
    if (direct.length <= 1850) return {url: direct, shortened: false};
    const chars = Array.from(brief);
    let low = 0, high = chars.length;
    while (low < high) {
      const mid = Math.ceil((low + high) / 2);
      if (make(chars.slice(0, mid).join(""), true).length <= 1850) low = mid;
      else high = mid - 1;
    }
    return {url: make(chars.slice(0, low).join(""), true), shortened: true};
  }

  function buildBrief() {
    const normalized = key => sanitizeText(answers[key] || "");
    return [
      "METAAUTOMATE / PROJECT DISCOVERY BRIEF",
      "Guided conversation — locally prepared",
      "------------------------------------------",
      "SERVICE INTEREST", service,
      "",
      "PROJECT IDEA", normalized("idea"),
      "",
      "DESIRED OUTCOME", normalized("outcome"),
      "",
      "WHO BENEFITS", normalized("audience"),
      "",
      "PREFERRED TIMELINE", normalized("timeline"),
      "",
      "CONSTRAINTS / REQUIREMENTS", normalized("constraints"),
      "",
      "------------------------------------------",
      "Drafted locally in a browser-only guided form, not by a connected AI service.",
      "Nothing was automatically transmitted, saved to MetaAutomate or published.",
      "This is not a contract, an accepted project or a guarantee of delivery."
    ].join("\n");
  }

  function finish() {
    currentBrief = buildBrief();
    summaryText.textContent = currentBrief;
    const draft = composeEmailHref(currentBrief);
    email.href = draft.url;
    shareNote.textContent = draft.shortened
      ? "The email draft is shortened for compatibility. Download and attach the full .txt brief, then send it yourself."
      : "Your email app will open a draft. Review the details and press Send yourself. No message has been sent.";
    copied.textContent = "";
    message("assistant", "Your project discovery brief is prepared. Review it below, then choose whether to share it with MetaAutomate.");
    summary.hidden = false;
    update();
    summaryTitle.focus({preventScroll: true});
    summary.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto" : "smooth", block: "nearest"
    });
  }

  function submit() {
    if (answerIndex >= QUESTIONS.length) return;
    error("");
    const stage = QUESTIONS[answerIndex];
    const value = sanitizeText(input.value);
    if (value.length < stage.minimum || value.length > stage.maximum) {
      error("Please enter " + stage.minimum + "–" + stage.maximum +
            " characters for " + stage.name.toLowerCase() + ".");
      input.focus();
      return;
    }
    answers[stage.key] = value;
    message("user", value);
    input.value = "";
    answerIndex += 1;
    if (answerIndex >= QUESTIONS.length) finish();
    else {
      message("assistant", QUESTIONS[answerIndex].question);
      update();
      input.focus();
    }
  }

  function startOver() {
    answerIndex = 0;
    answers = {};
    currentBrief = "";
    service = "Still exploring";
    summary.hidden = true;
    email.href = "mailto:" + BUSINESS_EMAIL + "?subject=MetaAutomate%20%7C%20Project%20inquiry";
    input.disabled = false;
    input.value = "";
    error("");
    copied.textContent = "";
    transcript.replaceChildren();
    message("assistant", QUESTIONS[0].question);
    update();
    input.focus();
  }

  send.addEventListener("click", submit);
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submit();
    }
  });
  edit.addEventListener("click", () => {
    if (answerIndex === 0) return;
    summary.hidden = true;
    currentBrief = "";
    const prior = QUESTIONS[answerIndex - 1];
    input.disabled = false;
    input.value = answers[prior.key] || "";
    delete answers[prior.key];
    answerIndex -= 1;
    transcript.lastElementChild?.remove(); // Most recent guided assistant question.
    transcript.lastElementChild?.remove(); // Most recent user reply.
    error("");
    update();
    input.focus();
  });
  restart.addEventListener("click", startOver);
  document.querySelectorAll("[data-project-template]").forEach(button => {
    button.addEventListener("click", () => {
      const starter = STARTERS[button.dataset.projectTemplate];
      if (!starter) return;
      if (answerIndex !== 0) startOver();
      service = starter.service;
      input.value = starter.idea;
      error("");
      input.focus();
    });
  });

  document.getElementById("project-chat-copy")?.addEventListener("click", async () => {
    if (!currentBrief) return;
    try {
      await navigator.clipboard.writeText(currentBrief);
      copied.textContent = "Copied locally. Nothing was sent.";
    } catch {
      copied.textContent = "Clipboard unavailable. Select the brief text above and copy manually.";
      summaryText.focus();
    }
  });
  document.getElementById("project-chat-download")?.addEventListener("click", () => {
    if (!currentBrief) return;
    const object = URL.createObjectURL(new Blob(
      [currentBrief + "\n"], {type: "text/plain;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = object;
    link.download = "metaautomate-project-discovery.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(object), 1000);
    copied.textContent = "Downloaded locally. No project was submitted.";
  });
  update();
})();
