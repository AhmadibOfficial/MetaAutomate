/* P2-050: Real browser-local narrated video export.
 * Generates moving original graphic + user-supplied audio as WebM.
 * No server, AI model, upload, payment, voice cloning or automatic sharing.
 */
(() => {
  "use strict";
  const $=id=>document.getElementById(id);
  const form=$("video-maker-form");
  if(!form)return;
  const audioInput=$("video-maker-audio"),audioPreview=$("video-maker-audio-preview"),rights=$("video-maker-rights");
  const size=$("video-maker-format"),run=$("video-maker-run");
  const status=$("video-maker-status"),preview=$("video-maker-preview");
  const link=$("video-maker-download"),poster=$("maker-canvas");
  const DIMENSIONS={wide:[1280,720],story:[720,1280]};
  let busy=false,generatedURL=null,previewURL=null;
  function message(text){status.textContent=text;}
  function cleanupPrevious(){
    if(generatedURL){URL.revokeObjectURL(generatedURL);generatedURL=null;}
    link.hidden=true;
    preview.pause();preview.removeAttribute("src");preview.load();
    preview.hidden=true;
  }
  function mime(){
    if(typeof MediaRecorder==="undefined")return null;
    for(const candidate of ["video/webm;codecs=vp8,opus","video/webm;codecs=vp9,opus","video/webm"]){
      if(MediaRecorder.isTypeSupported(candidate))return candidate;
    }
    return null;
  }
  function audioUsable(buffer){
    // Basic digital-silence detection only; not a semantic speech review.
    let squares=0,samples=0;
    for(let channel=0;channel<buffer.numberOfChannels;channel++){
      const data=buffer.getChannelData(channel);
      for(let i=0;i<data.length;i+=32){squares+=data[i]*data[i];samples++;}
    }
    return samples>100 && Math.sqrt(squares/samples)>=0.008;
  }
  async function produce(event){
    event.preventDefault();
    if(busy || !form.reportValidity())return;
    if(!poster || !poster.width || !poster.height) {message("Create your graphic first.");return;}
    const file=audioInput.files?.[0];
    if(!file || file.size<1024 || file.size>18_000_000){
      message("Choose an MP3 or WAV narration under 18 MB.");return;
    }
    if(!rights.checked){message("Confirm rights to the recording before export.");return;}
    const codec=mime();
    if(!codec || !HTMLCanvasElement.prototype.captureStream ||
       typeof AudioContext==="undefined"){
      message("This browser cannot create narrated WebM videos. Use a current desktop Chromium browser.");return;
    }
    const dims=DIMENSIONS[size.value];
    if(!dims){message("Choose a supported video format.");return;}
    busy=true;run.disabled=true;cleanupPrevious();
    const audioCtx=new AudioContext();
    let media=null,src=null,animation=0,stopper=0;
    try{
      // User gesture launches audio context before asynchronous decode.
      await audioCtx.resume();
      message("Checking your narration...");
      const decoded=await audioCtx.decodeAudioData(await file.arrayBuffer());
      if(decoded.duration<29.95 || decoded.duration>120.05 || !audioUsable(decoded)){
        throw Error("Use clear, audible narration between 30 and 120 seconds.");
      }
      const canvas=document.createElement("canvas");
      canvas.width=dims[0];canvas.height=dims[1];
      const cx=canvas.getContext("2d",{alpha:false});
      if(!cx)throw Error("2D video canvas is not available.");
      const videoStream=canvas.captureStream(24);
      const audioOut=audioCtx.createMediaStreamDestination();
      src=audioCtx.createBufferSource();
      src.buffer=decoded;
      src.connect(audioOut);
      const tracks=[...videoStream.getVideoTracks(),...audioOut.stream.getAudioTracks()];
      const stream=new MediaStream(tracks);
      media=new MediaRecorder(stream,{
        mimeType:codec,videoBitsPerSecond:1_800_000,audioBitsPerSecond:128_000
      });
      const blobs=[];
      const duration=Math.min(120,decoded.duration);
      const begin=performance.now();
      const draw=()=>{
        const progress=Math.max(0,Math.min(1,(performance.now()-begin)/(duration*1000)));
        const zoom=1+.038*progress;
        const scale=Math.max(canvas.width/poster.width,canvas.height/poster.height)*zoom;
        const dw=poster.width*scale,dh=poster.height*scale;
        cx.fillStyle="#08182b";cx.fillRect(0,0,canvas.width,canvas.height);
        cx.drawImage(poster,(canvas.width-dw)/2,(canvas.height-dh)/2,dw,dh);
        // Progress line conveys remaining clip duration without injecting text.
        cx.fillStyle="rgba(15,47,86,.24)";
        cx.fillRect(0,canvas.height-8,canvas.width,8);
        cx.fillStyle="#90c3ff";
        cx.fillRect(0,canvas.height-8,canvas.width*progress,8);
        if(progress<1)animation=requestAnimationFrame(draw);
      };
      draw();
      const recorded=new Promise((resolve,reject)=>{
        media.ondataavailable=e=>{if(e.data?.size)blobs.push(e.data);};
        media.onerror=()=>reject(Error("Video encoding failed on this device."));
        media.onstop=()=>{
          const blob=new Blob(blobs,{type:codec});
          if(blob.size<10_000)reject(Error("Video recording was incomplete."));
          else resolve(blob);
        };
      });
      // Starts streaming the generated frames and actual decoded WAV/MP3 audio.
      media.start(1000);
      src.start();
      message("Recording the narrated video locally. Keep this tab open.");
      stopper=window.setTimeout(()=>{
        if(media?.state==="recording")media.stop();
        try{src?.stop()}catch{}
      },Math.ceil(duration*1000)+250);
      const blob=await recorded;
      generatedURL=URL.createObjectURL(blob);
      preview.src=generatedURL;preview.hidden=false;
      link.href=generatedURL;link.hidden=false;
      link.download="metaautomate-narrated-"+size.value+".webm";
      message("Narrated video created. Play it to check voice clarity, then download.");
    }catch(err){
      message(err instanceof Error ? err.message : "Unable to create video.");
      if(media?.state==="recording"){try{media.stop()}catch{}}
    }finally{
      if(animation)cancelAnimationFrame(animation);
      if(stopper)clearTimeout(stopper);
      try{src?.disconnect()}catch{}
      try{await audioCtx.close()}catch{}
      if(media?.stream)media.stream.getTracks().forEach(t=>t.stop());
      busy=false;run.disabled=false;
    }
  }
  audioInput.addEventListener("change",()=>{
    if(previewURL){URL.revokeObjectURL(previewURL);previewURL=null;}
    audioPreview.pause();audioPreview.removeAttribute("src");
    const file=audioInput.files?.[0];
    if(file && file.size<=18_000_000){
      previewURL=URL.createObjectURL(file);
      audioPreview.src=previewURL;
      audioPreview.hidden=false;
      message("Listen to your narration. The video will be created only after you select Make narrated WebM video.");
    }else{
      audioPreview.hidden=true;
      if(file)message("Please choose a narration file under 18 MB.");
    }
  });
  form.addEventListener("submit",produce);
  // File is never submitted; decoded and encoded only inside this page.
  window.addEventListener("pagehide",()=>{
    if(generatedURL)URL.revokeObjectURL(generatedURL);
    if(previewURL)URL.revokeObjectURL(previewURL);
  });
})();
