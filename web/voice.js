// Capture and playback only: recognition/synthesis run in the offline voice worker.
window.larpusVoice = (() => {
  let enabled=false, starting=false, stream, context, source, processor, sink, playback;
  let chunks=[], lead=[], speaking=false, quiet=0, length=0, processing=false, resumeAt=0;
  const button=document.getElementById('mic');
  const notice=document.getElementById('notice');
  function clearAudio(){chunks=[];lead=[];speaking=false;quiet=0;length=0;}
  function label(text){button.querySelector('span').textContent=text;}
  function stop(){
    enabled=false;stream?.getTracks().forEach(track=>track.stop());
    processor?.disconnect();source?.disconnect();sink?.disconnect();context?.close();
    playback?.pause();clearAudio();label('VOICE OFF');button.setAttribute('aria-pressed','false');
  }
  function wav(samples,rate){
    const count=Math.floor(samples.length*16000/rate);
    const bytes=new ArrayBuffer(44+count*2),view=new DataView(bytes);
    const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
    text(0,'RIFF');view.setUint32(4,36+count*2,true);text(8,'WAVE');text(12,'fmt ');
    view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
    text(36,'data');view.setUint32(40,count*2,true);
    for(let i=0;i<count;i++){
      const from=Math.floor(i*rate/16000),to=Math.max(from+1,Math.floor((i+1)*rate/16000));
      let value=0;for(let j=from;j<to;j++)value+=samples[j]||0;
      value=Math.max(-1,Math.min(1,value/(to-from)));view.setInt16(44+i*2,value*(value<0?32768:32767),true);
    }
    let binary='';for(const byte of new Uint8Array(bytes))binary+=String.fromCharCode(byte);
    return btoa(binary);
  }
  function command(transcript){
    const text=transcript.toLowerCase().replace(/[.!?]+$/,'').trim();
    if(text==='larpus mute' || text==='mute voice'){stop();notice.textContent='Voice muted.';return true;}
    if(text==='larpus reset chat'){document.getElementById('clear').click();return true;}
    const prefix='larpus switch to ';
    if(text.startsWith(prefix)){
      const select=document.getElementById('persona');
      const option=[...select.options].find(o=>o.text.toLowerCase()===text.slice(prefix.length));
      if(option){select.value=option.value;select.dispatchEvent(new Event('change'));return true;}
    }
    return false;
  }
  async function send(rate){
    const captured=chunks;clearAudio();processing=true;label('TRANSCRIBING');
    try{
      const total=captured.reduce((n,c)=>n+c.length,0),samples=new Float32Array(total);
      let offset=0;for(const chunk of captured){samples.set(chunk,offset);offset+=chunk.length;}
      const response=await api('/api/voice',{action:'transcribe',audio:wav(samples,rate)});
      if(!enabled)return;
      if(response.audio)await play(response);
      if(!enabled)return;
      if(!command(response.transcript)){
        document.getElementById('prompt').value=response.transcript;
        document.getElementById('chat').requestSubmit();
      }
    }catch(error){notice.textContent=error.message;}
    finally{processing=false;if(enabled)label('LISTENING');}
  }
  async function start(){
    if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone needs localhost or trusted HTTPS.');
    stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
    try{
      context=new AudioContext();await context.resume();source=context.createMediaStreamSource(stream);
      processor=context.createScriptProcessor(2048,1,1);sink=context.createGain();sink.gain.value=0;
      source.connect(processor);processor.connect(sink);sink.connect(context.destination);
      enabled=true;button.setAttribute('aria-pressed','true');label('LISTENING');
      notice.textContent='Listening locally. Speak, then pause. Click VOICE to mute. No audio is retained.';
      processor.onaudioprocess=event=>{
        if(!enabled || processing || busy || playback || performance.now()<resumeAt){clearAudio();return;}
        const frame=new Float32Array(event.inputBuffer.getChannelData(0));
        const seconds=frame.length/context.sampleRate;
        const rms=Math.sqrt(frame.reduce((sum,x)=>sum+x*x,0)/frame.length);
        if(!speaking){lead.push(frame);if(lead.length>7)lead.shift();if(rms<0.018)return;speaking=true;chunks=lead;lead=[];}
        else chunks.push(frame);
        length+=seconds;quiet=rms<0.012?quiet+seconds:0;
        if((quiet>1.1 && length>0.4) || length>=29)send(context.sampleRate);
      };
    }catch(error){stop();throw error;}
  }
  async function play(result){
    if(!enabled || !result.audio)return;
    label('SPEAKING');clearAudio();
    const raw=atob(result.audio),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
    const url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));
    playback=new Audio(url);
    try{await new Promise((resolve,reject)=>{playback.onended=resolve;playback.onpause=resolve;playback.onerror=reject;playback.play().catch(reject);});}
    catch{notice.textContent='Audio playback blocked. Reply is displayed; enable sound in your browser.';}
    finally{playback=null;resumeAt=performance.now()+750;URL.revokeObjectURL(url);if(enabled)label('LISTENING');}
  }
  button.setAttribute('aria-label','Toggle local voice listening');button.setAttribute('aria-pressed','false');
  button.onclick=async()=>{if(starting)return;if(enabled){stop();notice.textContent='Microphone off.';}else {starting=true;try{await start();}catch(error){notice.textContent=error.message;}finally{starting=false;}}};
  window.addEventListener('pagehide',stop);
  return {get enabled(){return enabled;},play,stop};
})();
