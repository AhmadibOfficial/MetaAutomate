/* P2-057 MetaAutomate blue workspace.
 * Navigation is hideable on every screen; project data is never persisted here.
 * Existing intake and opt-in browser AI operate independently.
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
  const menu=document.getElementById("workspace-sidebar-toggle");
  const backdrop=document.getElementById("workspace-menu-backdrop");
  const search=document.getElementById("workspace-search-input");
  const searchEmpty=document.getElementById("workspace-search-empty");
  if(!main||!chat||!work||!workPanel||!heading||!intro||!aside||!menu)return;

  const onMobile=()=>window.matchMedia("(max-width:740px)").matches;
  let menuOpen=!onMobile();

  function updateSidebar(open,focus=false){
    menuOpen=Boolean(open);
    // Restore focus BEFORE hiding the active navigation control.
    if(!menuOpen&&aside.contains(document.activeElement))menu.focus();
    aside.hidden=!menuOpen;
    body.dataset.sidebar=menuOpen?"open":"closed";
    menu.setAttribute("aria-expanded",String(menuOpen));
    menu.setAttribute("aria-label",menuOpen?"Hide navigation":"Show navigation");
    menu.title=menuOpen?"Hide navigation":"Show navigation";
    if(backdrop)backdrop.hidden=!(onMobile()&&menuOpen);
    body.classList.toggle("workspace-drawer-open",onMobile()&&menuOpen);
    if(menuOpen&&focus)search?.focus();
    if(!menuOpen&&focus)menu.focus();
  }

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
      ?"Choose a tool and start creating."
      :"Describe your idea. We’ll help you shape it.";
    if(onMobile())updateSidebar(false);
    if(focus)heading.focus({preventScroll:true});
  }
  chat.addEventListener("click",()=>setMode("chat",true));
  work.addEventListener("click",()=>setMode("work",true));
  menu.addEventListener("click",()=>updateSidebar(!menuOpen,true));
  backdrop?.addEventListener("click",()=>updateSidebar(false,true));
  window.addEventListener("resize",()=>{
    const mobile=onMobile();
    if(mobile&&menuOpen)updateSidebar(false);
    else if(!mobile&&body.classList.contains("workspace-drawer-open")){
      updateSidebar(true);
    }
  });

  document.getElementById("workspace-work-brief")?.addEventListener("click",()=>{
    setMode("chat");
    const panel=document.getElementById("project-ai-experience");
    if(panel&&!panel.hidden)document.getElementById("project-ai-close")?.click();
    document.getElementById("project-chat-input")?.focus();
  });
  document.getElementById("workspace-work-ai")?.addEventListener("click",()=>{
    setMode("chat");
    const panel=document.getElementById("project-ai-experience");
    if(panel?.hidden)document.getElementById("project-ai-open")?.click();
    if(panel?.hidden===false){
      const input=document.getElementById("project-ai-input");
      if(input&&!input.disabled)input.focus();
      else document.getElementById("project-ai-load")?.focus();
    }
  });
  document.getElementById("project-chat-new")?.addEventListener("click",()=>{
    setMode("chat");
    if(onMobile())updateSidebar(false);
  });
  aside.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>{
    if(onMobile())updateSidebar(false);
  }));
  aside.querySelectorAll("[data-project-template]").forEach(button=>
    button.addEventListener("click",()=>{
      setMode("chat");
      const panel=document.getElementById("project-ai-experience");
      if(panel&&!panel.hidden)document.getElementById("project-ai-close")?.click();
      if(onMobile())updateSidebar(false);
    })
  );

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
    if(event.key==="Escape"&&onMobile()&&menuOpen){
      event.preventDefault();
      updateSidebar(false,true);
    }
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
      event.preventDefault();
      if(!menuOpen)updateSidebar(true);
      search?.focus();
    }
  });

  updateSidebar(!onMobile());
  try{
    const mode=new URLSearchParams(location.search).get("mode");
    if(mode==="work")setMode("work");
  }catch{/* Ignore malformed URL metadata. */}
})();
