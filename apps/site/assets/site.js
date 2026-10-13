/* MetaAutomate global company experience
 * Functional local interactions only. No telemetry, API requests,
 * cookies, storage, external dependencies or secret handling.
 */
(() => {
  "use strict";
  const navButton = document.getElementById("menu-button");
  const nav = document.getElementById("site-navigation");
  const header = document.querySelector(".site-header");
  const mobileQuery = window.matchMedia("(max-width: 1024px)");

  function showMenu(open) {
    if (!navButton || !nav) return;
    nav.classList.toggle("is-open", open);
    navButton.setAttribute("aria-expanded", String(open));
    navButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  }
  navButton?.addEventListener("click", () => {
    showMenu(navButton.getAttribute("aria-expanded") !== "true");
  });
  nav?.addEventListener("click", event => {
    if (event.target.closest("a")) showMenu(false);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && navButton?.getAttribute("aria-expanded") === "true") {
      showMenu(false);
      navButton.focus();
    }
  });
  document.addEventListener("click", event => {
    if (navButton && nav && !navButton.contains(event.target) && !nav.contains(event.target)) {
      showMenu(false);
    }
  });
  mobileQuery.addEventListener?.("change", () => showMenu(false));
  function onScroll() {
    header?.classList.toggle("is-scrolled", window.scrollY > 10);
  }
  onScroll();
  window.addEventListener("scroll", onScroll, {passive:true});
  document.querySelectorAll("[data-year]").forEach(node => {
    node.textContent = String(new Date().getFullYear());
  });

  // Operating philosophy, a conceptual design rather than a live agent interface.
  const phases = Object.freeze({
    understand: {
      number:"01 / 05", icon:"◎", title:"Start with the objective.",
      description:"Understand the problem, the desired outcome, the people involved and the limits of the work before deciding what should be built.",
      keyword:"CLARITY"
    },
    design: {
      number:"02 / 05", icon:"◈", title:"Engineer the right system.",
      description:"Translate context into deliberate architecture, capability boundaries and a clear pathway from idea to an implementable solution.",
      keyword:"ARCHITECTURE"
    },
    create: {
      number:"03 / 05", icon:"⌘", title:"Make the solution real.",
      description:"Build interfaces, software and workflows with craft, maintainability and the people who will use them in mind.",
      keyword:"CREATION"
    },
    verify: {
      number:"04 / 05", icon:"◇", title:"Prove what the system does.",
      description:"Test assumptions, check requirements, assess security and make responsible decisions from evidence—not promises.",
      keyword:"ASSURANCE"
    },
    improve: {
      number:"05 / 05", icon:"↗", title:"Keep learning. Keep improving.",
      description:"Use feedback and measurable outcomes to evolve the system and deepen the value it creates over time.",
      keyword:"EVOLUTION"
    }
  });
  const operationTabs = [...document.querySelectorAll("[data-operation]")];
  const operationPanel = document.getElementById("operation-content");
  function selectPhase(key, setFocus=false) {
    const phase=phases[key];
    if (!phase || !operationPanel) return;
    document.getElementById("operation-counter").textContent=phase.number;
    document.getElementById("operation-title").textContent=phase.title;
    document.getElementById("operation-description").textContent=phase.description;
    document.getElementById("operation-symbol").textContent=phase.icon;
    document.getElementById("operation-keyword").textContent=phase.keyword;
    for (const tab of operationTabs) {
      const selected=tab.dataset.operation===key;
      tab.classList.toggle("is-selected",selected);
      tab.setAttribute("aria-selected",String(selected));
      tab.tabIndex=selected?0:-1;
      if (selected) {
        operationPanel.setAttribute("aria-labelledby", tab.id);
        if (setFocus) tab.focus();
      }
    }
  }
  for (const tab of operationTabs) {
    tab.addEventListener("click", () => selectPhase(tab.dataset.operation));
    tab.addEventListener("keydown", event => {
      if (!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Home","End"].includes(event.key)) return;
      event.preventDefault();
      const i=operationTabs.indexOf(tab);
      const index=event.key==="Home"?0:event.key==="End"?operationTabs.length-1:
        ((i+(["ArrowLeft","ArrowUp"].includes(event.key)?-1:1)+operationTabs.length)%operationTabs.length);
      selectPhase(operationTabs[index].dataset.operation,true);
    });
  }
  if (operationTabs.length) selectPhase(operationTabs[0].dataset.operation);

  // Client-side project brief: never transmits private project information.
  const form=document.getElementById("brief-form");
  if (!form) return;

  const params=new URLSearchParams(window.location.search);
  const service=params.get("service");
  if (service && service.length<=100) {
    const select=document.getElementById("brief-service");
    if ([...select.options].some(option=>option.value===service)) select.value=service;
  }

  const result=document.getElementById("brief-result");
  const output=document.getElementById("brief-output");
  const error=document.getElementById("brief-error");
  const status=document.getElementById("brief-status");
  let currentBrief="";

  const value=id=>document.getElementById(id).value.trim();
  const normalized=value=>value.replace(/\r\n?/g,"\n").trim();
  function showError(message){
    error.textContent=message;
    error.hidden=false;
  }
  form.addEventListener("submit",event=>{
    event.preventDefault();
    error.hidden=true;
    error.textContent="";
    if (!form.checkValidity()) {
      showError("Complete the required fields and use the minimum description lengths.");
      form.reportValidity();
      return;
    }
    const lines=[
      "METAAUTOMATE / PROJECT DISCOVERY BRIEF",
      "Turn Your Vision Into Reality",
      "------------------------------------------",
      "",
      "SERVICE DISCIPLINE",
      value("brief-service"),
      "",
      "PROJECT STAGE",
      value("brief-stage"),
      "",
      "PROBLEM / CHALLENGE",
      normalized(value("brief-problem")),
      "",
      "DESIRED OUTCOME",
      normalized(value("brief-outcome")),
      "",
      "PREFERRED TIMELINE",
      value("brief-time")||"To be discussed",
      "",
      "REGION / TIMEZONE",
      value("brief-region")||"Not provided",
      "",
      "CONSTRAINTS",
      normalized(value("brief-constraints"))||"To be discussed",
      "",
      "------------------------------------------",
      "Created locally in the browser. No information was transmitted.",
      "This is a project discovery brief, not a contract or accepted engagement."
    ];
    currentBrief=lines.join("\n");
    output.textContent=currentBrief;
    result.hidden=false;
    status.textContent="";
    result.scrollIntoView({behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth",block:"start"});
  });

  form.addEventListener("reset",()=>{
    currentBrief="";
    result.hidden=true;
    error.hidden=true;
    error.textContent="";
    status.textContent="";
  });

  document.getElementById("brief-copy")?.addEventListener("click",async()=>{
    if (!currentBrief) return;
    try {
      await navigator.clipboard.writeText(currentBrief);
      status.textContent="Brief copied. You can paste it into your preferred secure business communication channel.";
    } catch {
      status.textContent="Clipboard access is unavailable. Select the brief text above to copy it manually.";
      output.focus();
    }
  });
  document.getElementById("brief-download")?.addEventListener("click",()=>{
    if (!currentBrief) return;
    const blob=new Blob([currentBrief+"\n"],{type:"text/plain;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");
    link.href=url;
    link.download="metaautomate-project-brief.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    status.textContent="Your project brief has been downloaded. No data was transmitted to MetaAutomate.";
  });
})();