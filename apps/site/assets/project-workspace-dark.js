/* P2-056: responsive, functional project workspace shell.
 * Existing guided intake, optional WebGPU AI and existing creators remain
 * separate verified components. No fabricated accounts, chat history, or
 * server tasks. No storage, remote requests, hidden file transfer.
 */
(() => {
  "use strict";
  const body=document.body;
  const main=document.querySelector(".project-chat");
  const chat=document.getElementById("workspace-mode-chat");
  const work=document.getElementById("workspace-mode-work");
  const workPanel=document.getElementById("workspace-work-panel");
  const heading=document.getElementById("project-chat-title");
  const intro=document.getElementById("workspace-intro");
  const aside=document.getElementById("project-workspace-side");
  const mobileToggle=document.getElementById("workspace-mobile-menu");
  const backdrop=document.getElementById("workspace-menu-backdrop");
  const search=document.getElementById("workspace-search-input");
  const searchEmpty=document.getElementById("workspace-search-empty");
  if(!main||!chat||!work||!workPanel||!heading||!intro)return;

  function setMode(mode,focus=false){
    const isWork=mode==="work";
    body.dataset.workspaceMode=isWork?"work":"chat";
    chat.setAttribute("aria-pressed",String(!isWork));
    work.setAttribute("aria-pressed",String(isWork));
    workPanel.hidden=!isWork;
    heading.textContent=isWork
      ?"What would you like to create today?"
      :"What would you like to build today?";
    intro.textContent=isWork
      ?"Choose a working tool and make something useful."
      :"Describe your project, explore an idea, or start creating now.";
    if(focus)heading.focus({preventScroll:true});
    closeMenu();
  }
  function closeMenu(){
    if(!aside||!mobileToggle||!backdrop)return;
    aside.classList.remove("is-open");
    mobileToggle.setAttribute("aria-expanded","false");
    backdrop.hidden=true;
  }
  function openMenu(){
    if(!aside||!mobileToggle||!backdrop)return;
    aside.classList.add("is-open");
    mobileToggle.setAttribute("aria-expanded","true");
    backdrop.hidden=false;
    search?.focus();
  }
  chat.addEventListener("click",()=>setMode("chat",true));
  work.addEventListener("click",()=>setMode("work",true));
  document.getElementById("workspace-work-brief")?.addEventListener("click",()=>{
    setMode("chat");
    const input=document.getElementById("project-chat-input");
    const aiPanel=document.getElementById("project-ai-experience");
    if(aiPanel&&!aiPanel.hidden)document.getElementById("project-ai-close")?.click();
    input?.focus();
  });
  document.getElementById("workspace-work-ai")?.addEventListener("click",()=>{
    setMode("chat");
    const panel=document.getElementById("project-ai-experience");
    if(panel?.hidden)document.getElementById("project-ai-open")?.click();
    if(panel?.hidden===false){
      const load=document.getElementById("project-ai-load");
      const input=document.getElementById("project-ai-input");
      if(input&&!input.disabled) input.focus();
      else load?.focus();
    }
  });
  document.getElementById("project-chat-new")?.addEventListener("click",()=>{
    setMode("chat");
    closeMenu();
  });

  mobileToggle?.addEventListener("click",()=>{
    aside?.classList.contains("is-open")?closeMenu():openMenu();
  });
  backdrop?.addEventListener("click",()=>{
    closeMenu();
    mobileToggle?.focus();
  });
  aside?.querySelectorAll("a").forEach(a=>a.addEventListener("click",closeMenu));
  aside?.querySelectorAll("[data-project-template]").forEach(button=>
    button.addEventListener("click",()=>{
      setMode("chat");
      const aiPanel=document.getElementById("project-ai-experience");
      if(aiPanel&&!aiPanel.hidden)document.getElementById("project-ai-close")?.click();
      closeMenu();
    })
  );

  // Search only visible, shipped starting points; not user conversations.
  // Never imply that project history or a server-side library is available.
  const starters=[...document.querySelectorAll(".project-chat-templates [data-project-template]")];
  function filterStarters(value){
    const query=String(value||"").toLocaleLowerCase().trim().slice(0,70);
    let visible=0;
    for(const button of starters){
      const found=button.textContent.toLocaleLowerCase().includes(query);
      button.hidden=!found;
      if(found)visible++;
    }
    if(searchEmpty)searchEmpty.hidden=visible!==0;
  }
  search?.addEventListener("input",()=>filterStarters(search.value));
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&aside?.classList.contains("is-open")){
      closeMenu();
      mobileToggle?.focus();
    }
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
      event.preventDefault();
      if(window.matchMedia("(max-width:740px)").matches)openMenu();
      search?.focus();
    }
  });
  // Safe query mode; no arbitrary redirects or untrusted template fields.
  try{
    const mode=new URLSearchParams(location.search).get("mode");
    if(mode==="work")setMode("work");
  }catch{/* Ignore malformed URL metadata. */}
})();
