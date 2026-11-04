/* MetaAutomate P2-065 Command Center — deterministic, browser-local guidance only.
   No network, persistence, model inference, business actions, account access or publishing. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const PAGES = ["chat","agents","projects","tools","settings"];
  const DATA = Object.freeze(JSON.parse($("tool-data").textContent));
  const MAX_CHATS = 12, MAX_TURNS = 30;
  const sessions = [];
  let activeId = null, nextId = 1, selectedTool = null, currentPanel = "chat";
  const prompt = $("command-input");
  const sidebar = $("chat-sidebar");
  const backdrop = $("drawer-backdrop");
  const toggle = $("mobile-toggle");
  const search = $("chat-search");
  const conversation = $("conversation");
  const messages = $("message-list");
  const history = $("chat-history");
  const scroller = document.querySelector(".content-scroller");

  const asText = value => typeof value === "string" ? value : "";
  const sanitize = value => asText(value).replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g," ").trim().slice(0,700);
  const sessionById = id => sessions.find(item => item.id === id) || null;
  const currentSession = () => sessionById(activeId);
  const isMobileDrawer = () => window.matchMedia("(max-width: 970px)").matches;
  const elt = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function closeDrawer(restoreFocus=false) {
    const wasOpen=sidebar.classList.contains("is-open");
    sidebar.classList.remove("is-open");
    backdrop.hidden=true;
    toggle.setAttribute("aria-expanded","false");
    if (restoreFocus && wasOpen) toggle.focus();
  }
  function openDrawer() {
    if (!isMobileDrawer()) return;
    sidebar.classList.add("is-open");
    backdrop.hidden=false;
    toggle.setAttribute("aria-expanded","true");
    $("side-close").focus();
  }
  toggle.addEventListener("click",()=>sidebar.classList.contains("is-open")?closeDrawer(true):openDrawer());
  $("side-close").addEventListener("click",()=>closeDrawer(true));
  backdrop.addEventListener("click",()=>closeDrawer(true));
  document.addEventListener("keydown", e => {
    if (e.key==="Escape" && sidebar.classList.contains("is-open")) closeDrawer(true);
  });
  window.addEventListener("resize",()=>{if(!isMobileDrawer())closeDrawer();});

  function setPanel(next) {
    if (!PAGES.includes(next)) return;
    currentPanel=next;
    for (const panel of document.querySelectorAll("[data-page]"))
      panel.hidden=panel.dataset.page!==next;
    for (const button of document.querySelectorAll("[data-panel]")) {
      const selected=button.dataset.panel===next;
      button.classList.toggle("active",selected);
      button.setAttribute("aria-pressed",String(selected));
    }
    scroller.scrollTop=0;
    closeDrawer();
  }
  for (const button of document.querySelectorAll("[data-panel]"))
    button.addEventListener("click",()=>setPanel(button.dataset.panel));

  function renderHistory() {
    history.replaceChildren();
    const query=search.value.trim().toLowerCase();
    const filtered=sessions.filter(item=>item.title.toLowerCase().includes(query));
    for (const item of filtered) {
      const button=elt("button","history-item");
      button.type="button";
      button.setAttribute("aria-current",String(item.id===activeId));
      button.setAttribute("aria-label","Open chat: "+item.title);
      const glyph=document.createElementNS("http://www.w3.org/2000/svg","svg");
      const use=document.createElementNS("http://www.w3.org/2000/svg","use");
      use.setAttribute("href","#i-chat");
      glyph.appendChild(use);
      button.append(glyph,elt("span","history-title",item.title));
      button.addEventListener("click",()=>{
        activeId=item.id;selectedTool=null;
        updateToolSelection();renderMessages();renderHistory();setPanel("chat");
      });
      history.appendChild(button);
    }
    $("chat-count").textContent=String(sessions.length);
    $("chat-empty").hidden=filtered.length>0;
    $("chat-empty").textContent=sessions.length===0 ?
      "No chats yet. Start with a goal or choose a tool." :
      "No chat titles match your search.";
  }

  search.addEventListener("input",renderHistory);
  function iconNode(name) {
    const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
    const use=document.createElementNS("http://www.w3.org/2000/svg","use");
    use.setAttribute("href","#i-"+name);
    svg.appendChild(use);
    return svg;
  }
  function updateToolSelection() {
    const chosen=selectedTool && DATA[selectedTool];
    $("selected-tool").hidden=!chosen;
    $("selected-tool-name").textContent=chosen ? chosen.name : "";
    prompt.placeholder=chosen ? "Describe your goal for "+chosen.name+"..." :
      "Describe what you want to create or improve...";
  }
  function chooseTool(key) {
    if (!Object.hasOwn(DATA,key)) return;
    selectedTool=key;
    updateToolSelection();
    setPanel("chat");
    prompt.focus();
  }
  $("remove-tool").addEventListener("click",()=>{selectedTool=null;updateToolSelection();prompt.focus();});
  for(const button of document.querySelectorAll("[data-choose]"))
    button.addEventListener("click",()=>chooseTool(button.dataset.choose));

  function renderDirectory() {
    const destination=$("agent-directory");
    destination.replaceChildren();
    const iconFor={image:"image",video:"video",project:"spark",intelligence:"chart",workflow:"folder",growth:"grid"};
    for (const [key,definition] of Object.entries(DATA)) {
      const tile=elt("article","directory-item");
      const symbol=iconNode(iconFor[key]);
      const title=elt("strong","",definition.name);
      const detail=elt("span","",definition.intro);
      const actions=elt("div","tool-actions");
      const button=elt("button","","Plan with guide");
      button.type="button";
      button.addEventListener("click",()=>chooseTool(key));
      const link=elt("a","","Open existing tool ↗");
      link.href=definition.url;
      actions.append(button,link);
      tile.append(symbol,title,detail,actions);
      destination.appendChild(tile);
    }
  }

  function inferTool(text) {
    const x=text.toLowerCase();
    if (/\b(video|film|clip|narrat|voiceover|reel|youtube)\b/.test(x))return "video";
    if (/\b(image|photo|graphic|poster|logo|thumbnail|design)\b/.test(x))return "image";
    if (/\b(inventory|stock|warehouse|workflow|task|schedule|process|operations)\b/.test(x))return "workflow";
    if (/\b(sales|marketing|leads|growth|customer|retention|campaign)\b/.test(x))return "growth";
    if (/\b(data|analytics|measure|metric|cost|budget|forecast|intelligence)\b/.test(x))return "intelligence";
    return "project";
  }
  function appendMessage(turn) {
    const li=elt("li","message "+(turn.role==="user"?"user":"guide"));
    const avatar=elt("span","avatar",turn.role==="user"?"You":"M");
    avatar.setAttribute("aria-hidden","true");
    const card=elt("div","message-body");
    const label=elt("strong","speaker",turn.role==="user"?"You":"MetaAutomate guide · Rules-based");
    card.appendChild(label);
    if(turn.role==="user"){
      card.appendChild(elt("p","",turn.text));
    } else {
      card.appendChild(elt("p","",turn.intro));
      const list=elt("ol");
      for (const step of turn.steps) list.appendChild(elt("li","",step));
      card.appendChild(list);
      const link=elt("a","message-link","Continue in "+turn.toolName+" ↗");
      link.href=turn.url;
      card.appendChild(link);
      card.appendChild(elt("p","safety-hint","No external action was performed. Review the next step yourself."));
    }
    li.append(avatar,card);
    messages.appendChild(li);
  }
  function renderMessages() {
    const session=currentSession();
    const hasMessages=Boolean(session && session.turns.length);
    $("welcome").hidden=hasMessages;
    conversation.hidden=!hasMessages;
    messages.replaceChildren();
    if(hasMessages){
      $("conversation-title").textContent=session.title;
      for (const turn of session.turns) appendMessage(turn);
      requestAnimationFrame(()=>{scroller.scrollTop=scroller.scrollHeight;});
    }
  }
  function newChat() {
    activeId=null;
    selectedTool=null;
    updateToolSelection();
    prompt.value="";
    renderMessages();
    renderHistory();
    setPanel("chat");
    prompt.focus();
  }
  $("new-chat").addEventListener("click",newChat);
  function send() {
    const text=sanitize(prompt.value);
    if(!text){prompt.focus();return;}
    let session=currentSession();
    if(!session){
      if(sessions.length>=MAX_CHATS){
        // Oldest session is only removed after an explicit new command;
        // no data is uploaded or silently persisted.
        sessions.shift();
      }
      session={id:nextId++,title:text.length>42?text.slice(0,42)+"…":text,turns:[]};
      sessions.push(session);
      activeId=session.id;
    }
    if(session.turns.length>=MAX_TURNS){
      prompt.setCustomValidity("This chat reached its local limit. Start a new chat to continue.");
      prompt.reportValidity();
      return;
    }
    prompt.setCustomValidity("");
    const key=selectedTool && DATA[selectedTool] ? selectedTool : inferTool(text);
    const definition=DATA[key];
    session.turns.push({role:"user",text});
    session.turns.push({
      role:"guide",toolName:definition.name,url:definition.url,
      intro:"Here is a practical next-step path for your goal. "+definition.intro,
      steps:[...definition.steps]
    });
    prompt.value="";
    renderHistory();renderMessages();setPanel("chat");
    // setPanel resets scroll position; return to newest message.
    requestAnimationFrame(()=>{scroller.scrollTop=scroller.scrollHeight;});
    prompt.focus();
  }
  $("command-form").addEventListener("submit",e=>{e.preventDefault();send();});
  prompt.addEventListener("keydown",e=>{
    if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){
      e.preventDefault();
      $("command-form").requestSubmit();
    }
  });
  prompt.addEventListener("input",()=>prompt.setCustomValidity(""));
  for(const button of document.querySelectorAll("[data-prompt]"))
    button.addEventListener("click",()=>{prompt.value=button.dataset.prompt;prompt.focus();});
  $("export-chat").addEventListener("click",()=>{
    const session=currentSession();
    if(!session)return;
    const text=["MetaAutomate / Local guided session",
      "Not an AI transcript or verified business evidence.",
      "No external actions executed.",
      "","Topic: "+session.title,"",
      ...session.turns.flatMap(turn=>turn.role==="user"?
        ["YOU: "+turn.text,""]:
        ["GUIDE (RULE-BASED): "+turn.intro,...turn.steps.map((s,i)=>String(i+1)+". "+s),
         "Continue: "+turn.url,""])
    ].join("\n");
    const blob=new Blob([text],{type:"text/plain;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const link=elt("a");
    link.href=url;
    link.download="metaautomate-guided-session.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
  });
  $("clear-all").addEventListener("click",()=>{
    sessions.splice(0,sessions.length);
    newChat();
    setPanel("settings");
    const notice=elt("p","clear-confirmation","Chats cleared from this browser tab.");
    const parent=$("clear-all").parentElement;
    const old=parent.querySelector(".clear-confirmation");
    if(old)old.remove();
    parent.appendChild(notice);
  });
  renderDirectory();
  updateToolSelection();
  renderHistory();
  renderMessages();
  setPanel("chat");
})();