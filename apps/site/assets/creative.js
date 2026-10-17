/* MetaAutomate Creative Workbench
 * Browser-only planning: NO image/video generation, no uploads, no fetch,
 * no automatic session storage; explicit one-time local handoff may be consumed.
 * No external provider, autopublish, payment, model execution or uploads.
 * All untrusted user-entered text is inserted with textContent ONLY.
 */
(() => {
  "use strict";
  const form = document.getElementById("creative-brief-form");
  if (!form) return;
  const kind = document.getElementById("creative-kind");
  const videoControl = document.getElementById("creative-video-control");
  const output = document.getElementById("creative-output");
  const structure = document.getElementById("creative-structure");
  const checks = document.getElementById("creative-checks");
  const status = document.getElementById("creative-outcome");
  const exportButton = document.getElementById("creative-export");
  let currentReport = "";

  const VIEWS = Object.freeze({
    social: "Social education",
    product: "Product presentation",
    training: "Training and awareness",
    brand: "Brand storytelling",
    clear: "Clear and educational",
    minimal: "Minimal and professional",
    warm: "Warm and conversational"
  });
  const values = () => Object.fromEntries(
    ["kind", "channel", "goal", "audience", "voice", "duration",
     "rights", "likeness", "proof", "reviewer"].map(name => [
      name, String(form.elements.namedItem(name)?.value || "").trim()
    ])
  );
  const line = (parent, name, value) => {
    const box = document.createElement("div");
    box.className = "creative-plan-line";
    const title = document.createElement("strong");
    const text = document.createElement("p");
    title.textContent = name;
    text.textContent = value;
    box.append(title, text);
    parent.append(box);
  };
  function updateFormat() {
    videoControl.hidden = kind.value !== "video";
  }
  kind.addEventListener("change", updateFormat);
  updateFormat();

  // Only an explicitly chosen, ten-minute same-tab handoff can fill fields.
  // Consume-once: never restore the full conversation or AI-generated claims.
  const incoming = window.MetaAutomateCreativeHandoff?.consume?.();
  if (incoming) {
    const goalField=form.elements.namedItem("goal");
    const audienceField=form.elements.namedItem("audience");
    if (goalField) goalField.value=incoming.goal;
    if (audienceField) audienceField.value=incoming.audience;
    kind.value=incoming.kind;
    updateFormat();
    const notice=document.getElementById("creative-import-notice");
    if (notice) {
      notice.hidden=false;
      notice.textContent="Project idea transferred locally from Start a Project. "+
        "Review the goal and audience. Rights, consent and human approval "+
        "have NOT been established. No AI media was generated.";
    }
  }

  form.addEventListener("reset", () => {
    output.hidden = true;
    currentReport = "";
    exportButton.disabled = true;
    // reset event fires before form values reset; explicit default.
    videoControl.hidden = true;
  });

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const v = values();
    const duration = Number(v.duration);
    const isVideo = v.kind === "video";
    const timeIsValid = !isVideo || [30, 60, 90, 120].includes(duration);
    const rightsKnown = ["owned", "licensed", "permission", "none"].includes(v.rights);
    const consentKnown = ["none", "consented"].includes(v.likeness);
    const rightsProof = ["licensed", "permission"].includes(v.rights)
      ? v.proof.length >= 8 : true;
    const issues = [];
    if (!rightsKnown) issues.push("The rights to referenced assets are not established.");
    if (!rightsProof) issues.push("Licensed or permitted assets require a traceable permission reference.");
    if (!consentKnown) issues.push("Likeness or voice consent has not been established.");
    if (!timeIsValid) issues.push("Video runtime must be within 30–120 seconds.");
    const canReview = issues.length === 0;
    const kindLabel = isVideo ? "SHORT-FORM VIDEO" : "IMAGE CONCEPT";

    status.classList.toggle("is-held", !canReview);
    status.textContent = canReview ? "READY FOR HUMAN REVIEW · NOT APPROVED"
                                   : "HOLD · RIGHTS OR CONSENT UNRESOLVED";
    structure.replaceChildren();
    checks.replaceChildren();

    line(structure, "Objective", v.goal);
    line(structure, "Audience and channel",
      v.audience + " · " + (VIEWS[v.channel] || v.channel));
    line(structure, "Visual direction",
      (VIEWS[v.voice] || v.voice) + " · Use original artwork and"
      + " accessible, high-contrast typography where appropriate.");
    if (isVideo) {
      const times = [0, 0.18, 0.58, 0.85, 1].map(x => Math.round(x * duration));
      const scenes = [
        "Introduce a genuine audience problem and give context.",
        "Explain the core idea visually with concrete, supportable examples.",
        "Show an actionable takeaway without guarantees or unsupported figures.",
        "End with a clear, non-manipulative next step."
      ];
      for (let i = 0; i < 4; i++) {
        line(structure, "Scene " + (i + 1) + " · " + times[i]
          + "–" + times[i+1] + " sec", scenes[i]);
      }
      line(structure, "Audio and accessibility",
        "Develop a human-reviewed narration or appropriately licensed soundtrack;"
        + " prepare synchronized captions and verify timing and readability.");
    } else {
      line(structure, "Image composition",
        "Define one primary message, readable hierarchy, an original visual metaphor,"
        + " licensed visual references and an accessible alternative-text description.");
      line(structure, "Human production step",
        "Prepare image prompt options and a source-reference record for review;"
        + " no generated image or approved creative has been created.");
    }
    const reviewLines = [
      "Rights declaration: " + (rightsKnown ? v.rights : "UNRESOLVED")
        + (v.proof ? " · evidence reference recorded" : " · no evidence reference entered"),
      "Identifiable people or voices: " + v.likeness,
      "Review owner: " + v.reviewer + " (named only; NOT authenticated)",
      "Verify source permissions, licences, likeness and voice consent independently.",
      "Check factual claims, brand identity, accessible text and captions before production.",
      "Confirm intended model or production tool, terms, estimated cost and human approval separately.",
      "Generation, export of media, distribution and publishing remain disabled here."
    ];
    [...issues, ...reviewLines].forEach((item, i) => {
      const li = document.createElement("li");
      li.className = i < issues.length ? "creative-review-blocker" : "";
      li.textContent = item;
      checks.append(li);
    });
    const structurePlain = [...structure.querySelectorAll(".creative-plan-line")]
      .map(el => el.querySelector("strong").textContent + "\n"
        + el.querySelector("p").textContent).join("\n\n");
    currentReport = [
      "MetaAutomate / CREATIVE REVIEW BRIEF",
      "STATUS: " + (canReview ? "READY FOR HUMAN REVIEW - NOT APPROVED"
                              : "HOLD - RIGHTS OR CONSENT UNRESOLVED"),
      "FORMAT: " + kindLabel,
      "NO MEDIA GENERATED OR PUBLISHED",
      "",
      structurePlain,
      "",
      "RIGHTS AND HUMAN REVIEW",
      ...reviewLines.map(x => "- " + x),
      ...issues.map(x => "- BLOCKER: " + x),
      "",
      "This browser-generated brief is self-reported planning material,"
        + " not a validated licence, authenticated consent, approval"
        + " or authorization to run a generative model."
    ].join("\n");
    output.hidden = false;
    exportButton.disabled = false;
    output.scrollIntoView({behavior: "smooth", block: "start"});
  });
  exportButton.addEventListener("click", () => {
    if (!currentReport) return;
    const blob = new Blob([currentReport], {type: "text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "metaautomate-creative-review-brief.txt";
    a.click();
    URL.revokeObjectURL(url);
  });
})();
