/* P2-04y — Optional *real* browser-side WebGPU inference.
 * No API keys, account, persistence, server LLM or media-generation actions.
 * Import and model downloads happen ONLY after an explicit user click.
 */
(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  const open = byId("project-ai-open");
  const panel = byId("project-ai-experience");
  if (!open || !panel) return;
  const close = byId("project-ai-close");
  const consent = byId("project-ai-consent");
  const load = byId("project-ai-load");
  const status = byId("project-ai-status");
  const feed = byId("project-ai-messages");
  const input = byId("project-ai-input");
  const send = byId("project-ai-send");
  const reset = byId("project-ai-reset");
  const exportChat = byId("project-ai-export");
  const creativeHandoff = byId("project-ai-creative-handoff");
  const creativeFormat = byId("project-ai-creative-format");
  const creativeNote = byId("project-ai-creative-note");
  const error = byId("project-ai-error");
  const guided = ["project-chat-messages","project-chat-suggestions",
                  "project-chat-summary"].map(byId);
  const actionArea = document.querySelector(".project-chat-action-area");
  const legacyStatus = document.querySelector(".project-chat-offline");
  let guidedSummaryVisible = false;
  const modelId = "Qwen2.5-0.5B-Instruct-q4f32_1-MLC";
  // Pin the library version; WebLLM's prebuilt config resolves the matching
  // model library and weights. This is still third-party, unaudited client code.
  const moduleURL = "https://esm.run/@mlc-ai/web-llm@0.2.85";
  const systemInstruction = (
    "You are a concise, practical MetaAutomate project discovery assistant. " +
    "Help the visitor define a problem, audience, intended result, risks and " +
    "first prototype. Ask at most one focused follow-up question. Clearly " +
    "differentiate possibilities from real MetaAutomate capabilities. " +
    "You cannot access accounts, generate media, deploy, email, book or " +
    "publish anything. Do not promise profits, licensing, model accuracy " +
    "or future deliveries. Never ask for passwords or private credentials. " +
    "You are a small on-device model and may be inaccurate."
  );
  let engine = null;
  let loading = false;
  let answering = false;
  let turns = [];
  let lastProjectQuestion = "";
  const setStatus = value => { status.textContent = value; };
  const setError = value => {
    error.textContent = value;
    error.hidden = !value;
  };
  const setReady = ready => {
    input.disabled = !ready;
    send.disabled = !ready || answering;
    load.disabled = loading || !!engine;
    if (creativeHandoff) creativeHandoff.disabled = !engine || answering || lastProjectQuestion.length < 20;
    if (exportChat) exportChat.disabled = !turns.length || answering;
  };

  function addMessage(role, message) {
    const item = document.createElement("div");
    item.className = "project-ai-message project-ai-" + role;
    const title = document.createElement("strong");
    title.textContent = role === "user" ? "You" : "MetaAutomate On-device AI";
    const body = document.createElement("p");
    body.textContent = message;
    item.append(title,body);
    feed.appendChild(item);
    feed.scrollTop = feed.scrollHeight;
  }
  function switchMode(show) {
    if (show) guidedSummaryVisible = Boolean(guided[2] && !guided[2].hidden);
    panel.hidden = !show;
    open.setAttribute("aria-expanded",String(show));
    open.textContent = show ? "AI on this device · Experiment" : "Try AI on this device ✳";
    if(guided[0]) guided[0].hidden = show;
    if(guided[1]) guided[1].hidden = show;
    if(guided[2]) guided[2].hidden = show || !guidedSummaryVisible;
    if(actionArea) actionArea.hidden = show;
    if(legacyStatus) legacyStatus.textContent = show
      ? "OPTIONAL ON-DEVICE AI · EXPERIMENTAL"
      : "GUIDED INTAKE · NO LIVE AI";
    if(show) {
      if(engine) input.focus();
      else load.focus();
    } else open.focus();
  }
  open.addEventListener("click", () => switchMode(panel.hidden));
  close.addEventListener("click", () => switchMode(false));

  async function checkHardware() {
    if (!window.isSecureContext || !navigator.gpu) {
      throw new Error("WebGPU is unavailable. Use a current WebGPU-enabled browser on a compatible device.");
    }
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
      throw new Error("No suitable graphics adapter is available for local AI.");
    }
  }
  load.addEventListener("click", async () => {
    if (loading || engine) return;
    loading=true;
    setError("");
    setReady(false);
    setStatus("Checking WebGPU support...");
    try {
      await checkHardware();
      setStatus("Loading the WebLLM library after your consent...");
      const webllm = await import(moduleURL);
      if (typeof webllm.CreateMLCEngine !== "function") {
        throw new Error("The WebLLM package did not load correctly.");
      }
      setStatus("Downloading model to your browser. First use may take time...");
      const candidate = await webllm.CreateMLCEngine(modelId, {
        initProgressCallback: progress => {
          const detail = typeof progress?.text === "string"
            ? progress.text.slice(0,180)
            : "Preparing on-device model...";
          setStatus(detail);
        }
      });
      if (!candidate?.chat?.completions?.create) {
        throw new Error("The local model did not initialize correctly.");
      }
      engine=candidate;
      consent.hidden=true;
      setStatus("On-device text AI is ready. Responses are generated locally; outputs may contain errors.");
      setReady(true);
      if(!feed.children.length){
        addMessage("assistant","Tell me what you want to build or improve. I can help explore the idea, but I cannot execute a project or generate media.");
      }
      input.focus();
    } catch (err) {
      // Never leak raw third-party error objects, filesystem locations or stack.
      const message=err instanceof Error ? err.message : "The local AI could not start.";
      const safe=message.slice(0,200);
      setError("On-device AI is not available: " + safe + " You can continue with guided intake.");
      setStatus("Model unavailable. No AI response was generated.");
    } finally {
      loading=false;
      setReady(Boolean(engine));
    }
  });

  async function submit() {
    if (!engine || answering) return;
    const text=input.value.trim();
    if (text.length < 3 || text.length > 1000) {
      setError("Enter a project question between 3 and 1000 characters.");
      return;
    }
    setError("");
    input.value="";
    addMessage("user",text);
    answering=true;
    setReady(false);
    setStatus("Generating a local AI response...");
    const nextTurns=[...turns,{role:"user",content:text}];
    const limited=nextTurns.slice(-8);
    const modelMessages=[{role:"system",content:systemInstruction},...limited];
    try {
      const completion=await engine.chat.completions.create({
        messages:modelMessages,
        temperature:0.45,
        max_tokens:260,
        stream:false
      });
      const reply=completion?.choices?.[0]?.message?.content;
      if(typeof reply!=="string" || reply.trim().length<2) {
        throw new Error("The model returned no readable text.");
      }
      const bounded=reply.trim().slice(0,2600);
      lastProjectQuestion=text.slice(0,700);
      turns=[...limited,{role:"assistant",content:bounded}].slice(-8);
      addMessage("assistant",bounded);
      setStatus("On-device AI response completed. Verify important information independently.");
    } catch {
      addMessage("assistant","The on-device model could not finish this reply. Please try again or use the guided project form.");
      setStatus("Local response failed. No project action was taken.");
    } finally {
      answering=false;
      setReady(true);
      input.focus();
    }
  }
  send.addEventListener("click",submit);
  input.addEventListener("keydown",event=>{
    if(event.key==="Enter" && !event.shiftKey && !event.isComposing){
      event.preventDefault();
      submit();
    }
  });
  reset.addEventListener("click",()=>{
    if(answering) return;
    turns=[];
    lastProjectQuestion="";
    if (creativeHandoff) creativeHandoff.disabled=true;
    if (exportChat) exportChat.disabled=true;
    feed.replaceChildren();
    setError("");
    setStatus(engine
      ? "Conversation cleared from page memory. Local model remains loaded."
      : "No AI is running. Start the model to begin.");
    if(engine) input.focus();
  });
  exportChat?.addEventListener("click", () => {
    if (!turns.length || answering) return;
    // Explicit download only: model cache is separate from conversation memory.
    const lines=[
      "METAAUTOMATE / ON-DEVICE AI CONVERSATION",
      "Experimental model output. Review all statements independently.",
      "No conversation was uploaded or stored in a MetaAutomate account.",
      "",
      ...turns.map(turn=>(turn.role==="user"?"YOU":"ON-DEVICE AI")+
        "\n"+turn.content+"\n")
    ];
    const blob=new Blob([lines.join("\n")],{type:"text/plain;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");
    link.href=url;
    link.download="metaautomate-on-device-chat.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    if (creativeNote) creativeNote.textContent=
      "A copy of the recent conversation was downloaded to your device. Nothing was sent.";
  });
  creativeHandoff?.addEventListener("click", () => {
    if (!engine || answering || lastProjectQuestion.length<20) return;
    const adapter=window.MetaAutomateCreativeHandoff;
    if (!adapter?.save?.({
      kind:creativeFormat?.value,source:"device_ai",
      goal:lastProjectQuestion,audience:""
    })) {
      if(creativeNote) creativeNote.textContent =
        "The one-time local transfer was blocked. Copy your idea and open Creative Workbench instead.";
      return;
    }
    window.location.assign("/creative/#creative-form");
  });
  // No hidden initialization or network request occurs until the user chooses
  // "Download model and start local AI".
  setReady(false);
})();
