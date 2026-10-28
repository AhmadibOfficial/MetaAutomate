/* MetaAutomate P2-064 public website — local, accessible goal selector. */
(() => {
  "use strict";
  const goals=Object.freeze({
    customers:{title:"Customer experience",desc:"Organize inquiries, prepare follow-up processes and give customer-service teams a clearer path to review."},
    operations:{title:"Business operations",desc:"Map a process, identify bottlenecks, and prepare a reviewable path to better operations."},
    costs:{title:"Costs & finance",desc:"Identify spending questions, prepare structured cost reviews and define how improvement could be measured."},
    automation:{title:"Intelligent automation",desc:"Map repetitive work, design an approval-first workflow and define safe verification before any future execution."},
    insights:{title:"Business intelligence",desc:"Clarify the decision, identify trustworthy data and prepare an explainable way to evaluate the outcome."}
  });
  const title=document.getElementById("focus-title");
  const desc=document.getElementById("focus-description");
  const link=document.getElementById("focus-start");
  const buttons=Array.from(document.querySelectorAll("button[data-goal]"));
  function select(key) {
    if(!Object.hasOwn(goals,key))return;
    const item=goals[key];
    title.textContent=item.title;
    desc.textContent=item.desc;
    link.href="/universal/?goal="+key;
    for(const button of buttons)button.setAttribute("aria-pressed",String(button.dataset.goal===key));
  }
  for(const button of buttons){
    button.addEventListener("click",()=>select(button.dataset.goal));
    button.addEventListener("keydown",event=>{
      if(event.key!=="ArrowRight"&&event.key!=="ArrowLeft")return;
      event.preventDefault();
      const index=buttons.indexOf(button);
      const next=(index+(event.key==="ArrowRight"?1:-1)+buttons.length)%buttons.length;
      buttons[next].focus();
      select(buttons[next].dataset.goal);
    });
  }
  select("operations");
})();