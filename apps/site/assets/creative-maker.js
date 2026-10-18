/* P2-050 MetaAutomate Image Creator: actual local canvas generation and PNG export.
 * No API, provider, storage, stock photos, AI model, upload or auto-publish.
 */
(() => {
  "use strict";
  const form=document.getElementById("maker-form");
  const canvas=document.getElementById("maker-canvas");
  if(!form || !canvas || !canvas.getContext) return;
  const $=id=>document.getElementById(id);
  const format=$("maker-format"),theme=$("maker-theme"),brand=$("maker-brand");
  const headline=$("maker-title-input"),subtitle=$("maker-subtitle"),action=$("maker-action");
  const save=$("maker-download"),status=$("maker-status"),meta=$("maker-meta");
  const ctx=canvas.getContext("2d",{alpha:false});
  const SIZES={square:[1080,1080],story:[1080,1920],wide:[1920,1080]};
  const PALETTE={
    white:{background:"#f8fafc",foreground:"#0f2541",muted:"#455b75",accent:"#1761b2",secondary:"#d9e9fa",tag:"#e5f0fb",shadow:"rgba(14,46,79,.08)"},
    navy:{background:"#09172c",foreground:"#ffffff",muted:"#c1cee0",accent:"#74adff",secondary:"#143258",tag:"#13345e",shadow:"rgba(0,0,0,.25)"},
    blue:{background:"#0c4c98",foreground:"#ffffff",muted:"#e0edff",accent:"#a4d0ff",secondary:"#1465b7",tag:"#125ead",shadow:"rgba(0,0,0,.15)"}
  };
  let dirty=true,ready=false,sequence=0;
  const sanitize=(value,max)=>String(value||"").replace(/[\u0000-\u001f\u007f]/g," ").trim().slice(0,max);
  function rounded(x,y,w,h,r,fill){
    ctx.beginPath();
    if(typeof ctx.roundRect==="function")ctx.roundRect(x,y,w,h,r);
    else ctx.rect(x,y,w,h);
    ctx.fillStyle=fill;ctx.fill();
  }
  function wrap(text,maxWidth,font,maxLines){
    ctx.font=font;
    const words=text.split(/\s+/).filter(Boolean),lines=[];
    let line="";
    function splitLongWord(word){
      const chunks=[];let segment="";
      for(const char of Array.from(word)){
        if(ctx.measureText(segment+char).width>maxWidth && segment){
          chunks.push(segment);segment=char;
        }else segment+=char;
      }
      if(segment)chunks.push(segment);
      return chunks;
    }
    for(const word of words){
      const chunks=ctx.measureText(word).width>maxWidth?splitLongWord(word):[word];
      for(const chunk of chunks){
        const next=line?line+" "+chunk:chunk;
        if(ctx.measureText(next).width>maxWidth && line){lines.push(line);line=chunk;}
        else line=next;
      }
    }
    if(line)lines.push(line);
    if(lines.length>maxLines){
      const last=lines.slice(0,maxLines);
      let end=last[maxLines-1];
      while(end.length>1 && ctx.measureText(end+"…").width>maxWidth)end=end.slice(0,-1);
      last[maxLines-1]=end+"…";
      return last;
    }
    return lines;
  }
  function textLines(lines,x,y,step,color,font){
    ctx.fillStyle=color;ctx.font=font;ctx.textBaseline="alphabetic";
    lines.forEach((line,i)=>ctx.fillText(line,x,y+i*step));
  }
  function read(){
    const key=format.value,palette=PALETTE[theme.value];
    if(!SIZES[key] || !palette)throw Error("Invalid design settings");
    const data={
      size:key,colors:palette,
      brand:sanitize(brand.value,45),
      headline:sanitize(headline.value,130),
      subtitle:sanitize(subtitle.value,190),
      action:sanitize(action.value,65)
    };
    if(data.brand.length<2 || data.headline.length<8)throw Error("Add a brand and main message before generating");
    return data;
  }
  function render(){
    const data=read(),[w,h]=SIZES[data.size],p=data.colors;
    canvas.width=w;canvas.height=h; // resets canvas transform, avoids stale renders.
    ctx.fillStyle=p.background;ctx.fillRect(0,0,w,h);
    const landscape=data.size==="wide",tall=data.size==="story";
    const margin=landscape?116:92;
    const top=landscape?120:tall?148:113;
    const available=w-margin*2;
    // Original geometric illustration, no external photos or model assets.
    ctx.save();ctx.globalAlpha=.68;
    rounded(w-(landscape?570:465),tall?240:100,landscape?820:590,tall?520:430,
      80,p.secondary);
    ctx.translate(w-(landscape?320:248),tall?410:270);
    ctx.rotate(-.26);
    rounded(-200,-116,380,232,62,p.tag);
    ctx.restore();
    ctx.save();ctx.globalAlpha=.18;
    ctx.fillStyle=p.accent;
    ctx.beginPath();
    ctx.arc(w-(landscape?250:183),tall?790:570,landscape?205:150,0,Math.PI*2);
    ctx.fill();ctx.restore();
    rounded(margin,top,Math.min(available,490),landscape?57:54,27,p.tag);
    const brandSize=landscape?24:25;
    ctx.font="750 "+brandSize+"px Arial, Helvetica, sans-serif";
    ctx.fillStyle=p.accent;ctx.textBaseline="middle";
    const brandLabel=data.brand.toUpperCase();
    ctx.fillText(brandLabel,margin+22,top+(landscape?29:27),
      Math.min(available-44,440));
    const titleStart=landscape?345:tall?710:385;
    const titleFont=landscape?105:tall?91:84;
    const maxTitleLines=tall?6:landscape?4:5;
    const titleFamily="800 "+titleFont+"px Arial, Helvetica, sans-serif";
    const lines=wrap(data.headline,available,titleFamily,maxTitleLines);
    const lineHeight=titleFont*1.16;
    ctx.fillStyle=p.foreground;ctx.font=titleFamily;
    textLines(lines,margin,titleStart,lineHeight,p.foreground,titleFamily);
    const bottomTitle=titleStart+(lines.length-1)*lineHeight;
    const subFont=landscape?37:tall?41:34;
    const subFamily="400 "+subFont+"px Arial, Helvetica, sans-serif";
    const subTop=Math.min(bottomTitle+(landscape?100:105),h-(tall?400:landscape?200:255));
    textLines(wrap(data.subtitle,available,subFamily,tall?5:3),margin,subTop,subFont*1.45,p.muted,subFamily);
    const ruleY=h-(landscape?175:tall?275:183);
    ctx.fillStyle=p.accent;ctx.fillRect(margin,ruleY,Math.min(available,145),8);
    if(data.action){
      const actionFont=landscape?34:tall?40:30;
      ctx.fillStyle=p.foreground;
      ctx.font="700 "+actionFont+"px Arial, Helvetica, sans-serif";
      ctx.fillText(data.action,margin,ruleY+(landscape?68:tall?94:70),available);
    }
    ctx.fillStyle=p.muted;ctx.font="500 "+(landscape?23:22)+"px Arial, Helvetica, sans-serif";
    ctx.fillText("CREATED WITH METAAUTOMATE",margin,h-(landscape?61:69));
    meta.textContent=(data.size==="square"?"Square social image":data.size==="story"?"Vertical story":"Widescreen graphic")+
      " · "+w+" × "+h+" PNG";
    status.textContent="Preview ready. Download your original PNG graphic.";
    ready=true;dirty=false;save.disabled=false;
  }
  function invalidate(){
    dirty=true;ready=false;save.disabled=true;
    status.textContent="Settings changed. Update the preview to create the new image.";
  }
  for(const el of [format,theme,brand,headline,subtitle,action]){
    el.addEventListener("input",invalidate);
    el.addEventListener("change",invalidate);
  }
  form.addEventListener("submit",event=>{
    event.preventDefault();
    if(!form.reportValidity())return;
    try {render();}catch(e){ready=false;save.disabled=true;status.textContent=e.message||"Preview failed.";}
  });
  save.addEventListener("click",()=>{
    if(!ready || dirty || save.disabled)return;
    save.disabled=true;
    const mySequence=++sequence;
    canvas.toBlob(blob=>{
      if(mySequence!==sequence)return;
      if(!blob || blob.size<1000){
        status.textContent="PNG export failed on this device. Try updating the preview.";
        save.disabled=false;return;
      }
      const url=URL.createObjectURL(blob);
      const a=document.createElement("a");
      a.href=url;a.download="metaautomate-original-"+format.value+".png";
      document.body.appendChild(a);a.click();a.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);
      status.textContent="PNG downloaded to your device.";
      save.disabled=false;
    },"image/png");
  });
  try{render();}catch{save.disabled=true;status.textContent="Enter your graphic text to create a preview.";}
})();
