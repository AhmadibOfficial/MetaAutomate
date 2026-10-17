/* P2-04z — Optional, one-time same-tab project handoff.
 * Browser sessionStorage is used ONLY after an explicit user interaction.
 * Never includes credentials, media, conversation history, AI output or consent.
 */
(() => {
  "use strict";
  const KEY="mat:creative:handoff:v1";
  const TTL_MS=10*60*1000;
  function clean(value,max) {
    if (typeof value!=="string") return "";
    return value.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g," ")
      .replace(/\r\n?/g,"\n").trim().slice(0,max);
  }
  function save(item) {
    if (!item || typeof item!=="object") return false;
    const goal=clean(item.goal,700);
    const audience=clean(item.audience||"",100);
    const kind=item.kind==="video"?"video":item.kind==="image"?"image":null;
    const source=item.source==="guided"?"guided":item.source==="device_ai"?"device_ai":null;
    if(!kind||!source||goal.length<20||!Number.isFinite(Date.now()))return false;
    const payload={version:1,createdAt:Date.now(),kind,source,goal,audience};
    try {
      window.sessionStorage.setItem(KEY,JSON.stringify(payload));
      return true;
    } catch {
      return false;
    }
  }
  function consume() {
    let raw;
    try {
      raw=window.sessionStorage.getItem(KEY);
      window.sessionStorage.removeItem(KEY); // read-once, even if malformed.
    } catch {
      return null;
    }
    if (!raw || raw.length>1800) return null;
    let item;
    try {item=JSON.parse(raw);}catch{return null;}
    if (!item || typeof item!=="object" || item.version!==1 ||
        typeof item.createdAt!=="number" || !Number.isFinite(item.createdAt) ||
        item.createdAt>Date.now()+10000 ||
        Date.now()-item.createdAt>TTL_MS ||
        !["image","video"].includes(item.kind) ||
        !["guided","device_ai"].includes(item.source) ||
        typeof item.goal!=="string" || item.goal.length<20 || item.goal.length>700 ||
        typeof item.audience!=="string" || item.audience.length>100) {
      return null;
    }
    return {kind:item.kind,source:item.source,
            goal:clean(item.goal,700),audience:clean(item.audience,100)};
  }
  Object.defineProperty(window,"MetaAutomateCreativeHandoff",{
    value:Object.freeze({save,consume}),writable:false,configurable:false
  });
})();
