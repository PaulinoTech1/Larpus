// Audio stays in this browser session; STT/TTS use the offline worker only.
window.larpusVoice = (() => {
  const el=id=>document.getElementById(id), button=el('mic'), notice=el('notice');
  let enabled=false, starting=false, stream, context, source, processor, sink;
  let chunks=[], lead=[], speaking=false, quiet=0, length=0, voiced=0, onset=0;
  let recording=false, processing=false, session=0, resumeAt=0, noise=0.006;
  let playback=null, playToken=0, lastText='', lastAudio=null;
  let speechQueue=[],queueActive=false,queueRunning=false,queueToken=0;
  let preparedSpeech=null;
  const speed=()=>Number(el('voice-speed').value);
  const status=text=>{el('voice-status').textContent=text;};
  const label=text=>{button.querySelector('span').textContent=text;};
  function clearAudio(){chunks=[];lead=[];speaking=false;quiet=0;length=0;voiced=0;onset=0;}
  function labels(){
    el('voice-record').disabled=!enabled || processing || !!playback || queueActive || queueRunning || el('voice-mode').value!=='push';
    el('voice-record').textContent=recording?'STOP RECORDING':'RECORD';
    el('voice-pause').disabled=!playback;
    el('voice-pause').textContent=playback?.audio.paused?'RESUME AUDIO':'PAUSE AUDIO';
    el('voice-repeat').disabled=!lastText;
    label(!enabled?'VOICE OFF':playback?(playback.audio.paused?'AUDIO PAUSED':'SPEAKING'):processing?'TRANSCRIBING':recording?'RECORDING':el('voice-mode').value==='push'?'MIC READY':'LISTENING');
  }
  function stopPlayback(){
    playToken++;
    speechQueue=[];preparedSpeech=null;queueActive=false;queueToken++;
    if(playback){const old=playback;playback=null;old.audio.onended=null;old.audio.onerror=null;old.audio.pause();URL.revokeObjectURL(old.url);old.resolve();}
    resumeAt=performance.now()+1000;clearAudio();labels();
  }
  function stopCapture(){
    session++;enabled=false;recording=false;processing=false;
    stream?.getTracks().forEach(track=>track.stop());
    processor?.disconnect();source?.disconnect();sink?.disconnect();context?.close();
    stream=context=source=processor=sink=null;clearAudio();
    button.setAttribute('aria-pressed','false');labels();
  }
  function stop(){stopCapture();stopPlayback();}
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
    if(text==='larpus mute' || text==='mute voice'){stopCapture();status('Microphone muted.');return true;}
    if(text==='larpus repeat'){repeat(lastText);return true;}
    if(text==='larpus reset chat'){el('clear').click();return true;}
    const prefix='larpus switch to ';
    if(text.startsWith(prefix)){
      const select=el('persona'),option=[...select.options].find(o=>o.text.toLowerCase()===text.slice(prefix.length));
      if(option){select.value=option.value;select.dispatchEvent(new Event('change'));return true;}
    }
    return false;
  }
  async function send(rate){
    const captured=chunks, active=session, speechDuration=voiced;
    recording=false;clearAudio();
    if(speechDuration<0.25){status('No clear speech captured. Try RECORD again.');labels();return;}
    processing=true;labels();
    try{
      const total=captured.reduce((n,c)=>n+c.length,0),samples=new Float32Array(total);
      let offset=0;for(const chunk of captured){samples.set(chunk,offset);offset+=chunk.length;}
      const response=await api('/api/voice',{action:'transcribe',audio:wav(samples,rate)});
      if(!enabled || active!==session)return;
      const transcript=(response.transcript||'').trim();
      if(!transcript){status('No confident speech detected. Nothing was sent.');return;}
      // Never replace a typed draft or execute a command before review by default.
      if(el('voice-review').checked || el('prompt').value.trim()){
        const draft=[el('prompt').value.trim(),transcript].filter(Boolean).join('\n');
        if(draft.length>8000){status('Draft is full. Send or shorten it before recording again.');return;}
        el('prompt').value=draft;
        el('prompt').focus();status('Transcript ready. Correct it if needed, then SEND.');return;
      }
      if(response.audio && el('voice-output').checked)play(response);
      if(!command(transcript)){el('prompt').value=transcript;el('chat').requestSubmit();}
    }catch(error){notice.textContent=error.message;}
    finally{if(active===session){processing=false;resumeAt=performance.now()+700;labels();}}
  }
  async function devices(){
    if(!navigator.mediaDevices?.enumerateDevices)return;
    const selected=el('mic-device').value,items=await navigator.mediaDevices.enumerateDevices();
    const inputs=items.filter(d=>d.kind==='audioinput');
    el('mic-device').replaceChildren(new Option('System default microphone',''),...inputs.map((d,i)=>new Option(d.label||`Microphone ${i+1} (enable VOICE for names)`,d.deviceId)));
    if(inputs.some(d=>d.deviceId===selected))el('mic-device').value=selected;
    else if(selected && enabled){stopCapture();status('Selected microphone disconnected. Choose another mic, then enable VOICE.');}
  }
  async function start(){
    if(!navigator.mediaDevices?.getUserMedia)throw Error('Microphone needs localhost or trusted HTTPS.');
    const active=++session,device=el('mic-device').value;
    const acquired=await navigator.mediaDevices.getUserMedia({audio:{...(device?{deviceId:{exact:device}}:{}),channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:false},video:false});
    if(active!==session){acquired.getTracks().forEach(t=>t.stop());return;}
    stream=acquired;
    try{
      context=new AudioContext();await context.resume();source=context.createMediaStreamSource(stream);
      processor=context.createScriptProcessor(2048,1,1);sink=context.createGain();sink.gain.value=0;
      source.connect(processor);processor.connect(sink);sink.connect(context.destination);
      enabled=true;noise=0.006;button.setAttribute('aria-pressed','true');await devices();labels();
      status(el('voice-mode').value==='push'?'Mic ready. Click RECORD, speak, then STOP RECORDING.':'Listening locally. Pause after speaking; transcripts appear for review.');
      processor.onaudioprocess=event=>{
        if(!enabled || processing || busy || playback || queueActive || queueRunning || performance.now()<resumeAt || (el('voice-mode').value==='push' && !recording)){clearAudio();return;}
        const frame=new Float32Array(event.inputBuffer.getChannelData(0)),seconds=frame.length/context.sampleRate;
        const rms=Math.sqrt(frame.reduce((sum,x)=>sum+x*x,0)/frame.length);
        const threshold=Math.max(0.018,noise*3);
        if(el('voice-mode').value==='push'){
          chunks.push(frame);length+=seconds;if(rms>Math.max(0.01,noise*2))voiced+=seconds;
        }else{
          if(!speaking){
            lead.push(frame);if(lead.length>7)lead.shift();
            if(rms<threshold){noise=noise*0.97+Math.min(rms,0.02)*0.03;onset=0;return;}
            onset+=seconds;if(onset<0.18)return;
            speaking=true;chunks=lead;lead=[];
          }else chunks.push(frame);
          length+=seconds;if(rms>Math.max(0.012,noise*2))voiced+=seconds;
          quiet=rms<Math.max(0.012,noise*2)?quiet+seconds:0;
          if(quiet>0.75 && voiced>=0.25)send(context.sampleRate);
        }
        if(length>=29)send(context.sampleRate);
      };
    }catch(error){stopCapture();throw error;}
  }
  function audioPlay(audioData,token){
    const raw=atob(audioData),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
    const url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'})),audio=new Audio(url);
    audio.playbackRate=speed();audio.preservesPitch=true;clearAudio();recording=false;
    return new Promise(resolve=>{
      const finish=()=>{
        if(playback?.audio===audio){playback=null;URL.revokeObjectURL(url);resumeAt=performance.now()+1000;labels();}
        resolve();
      };
      playback={audio,url,resolve};audio.onended=finish;audio.onerror=()=>{notice.textContent='Audio could not play. The reply is still displayed.';finish();};
      audio.onplay=labels;audio.onpause=labels;
      labels();audio.play().catch(()=>{if(token===playToken)notice.textContent='Click REPEAT to allow browser audio playback.';finish();});
    });
  }
  async function play(result){
    if(result.content){lastText=result.content;lastAudio=result.content.length<=2000?result.audio:null;labels();}
    if(!el('voice-output').checked || !result.audio)return;
    stopPlayback();const token=playToken;
    await audioPlay(result.audio,token);
  }
  function parts(text){
    const out=[];
    while(text.length>2000){let cut=text.lastIndexOf(' ',2000);if(cut<1)cut=2000;out.push(text.slice(0,cut));text=text.slice(cut).trimStart();}
    if(text.trim())out.push(text);return out;
  }
  function beginReply(){stopPlayback();queueActive=el('voice-output').checked;labels();}
  function enqueueSpeech(text){
    if(!queueActive || !el('voice-output').checked)return;
    speechQueue.push(...parts(text));pumpSpeech();
    if(playback)prepareSpeech();
  }
  function finishReply(text){lastText=text;lastAudio=null;queueActive=false;labels();}
  function prepareSpeech(){
    if(!preparedSpeech && speechQueue.length){
      // At most one prepared WAV ahead of playback, CPU synthesis stays serial.
      const token=playToken,text=speechQueue.shift();
      preparedSpeech={token,promise:api('/api/voice',{action:'synthesize',text}).then(result=>({result}),error=>({error}))};
    }
  }
  async function pumpSpeech(){
    // One FIFO consumer; later sentences never interrupt earlier audio.
    if(queueRunning)return;
    queueRunning=true;const token=playToken,qtoken=queueToken;
    try{
      while((speechQueue.length || preparedSpeech) && token===playToken){
        status('Preparing speech locally...');
        prepareSpeech();const pending=preparedSpeech;preparedSpeech=null;
        const {result,error}=await pending.promise;
        if(token!==playToken)return;
        if(error)throw error;
        const playing=audioPlay(result.audio,token);prepareSpeech();
        await playing;
      }
    }catch(error){if(token===playToken){speechQueue=[];preparedSpeech=null;notice.textContent='Reply is shown; '+error.message;}}
    finally{
      queueRunning=false;
      // A new reply may have queued text while an old synthesis was cancelled.
      if(speechQueue.length && (qtoken!==queueToken || token===playToken))pumpSpeech();
      labels();
    }
  }
  async function repeat(text=lastText){
    if(!text)return;
    stopPlayback();const token=playToken;
    try{
      if(text===lastText && lastAudio){await audioPlay(lastAudio,token);return;}
      status('Preparing replay locally...');
      for(const part of parts(text)){
        const result=await api('/api/voice',{action:'synthesize',text:part});
        if(token!==playToken)return;
        await audioPlay(result.audio,token);
        if(token!==playToken)return;
      }
    }catch(error){notice.textContent=error.message;}
    finally{labels();}
  }
  function pause(){
    if(!playback)return;
    const audio=playback.audio;
    if(audio.paused)audio.play().catch(()=>{notice.textContent='Click RESUME AUDIO to enable sound.';});else audio.pause();
    labels();
  }
  button.setAttribute('aria-label','Toggle local microphone');button.setAttribute('aria-pressed','false');
  button.onclick=async()=>{
    if(starting)return;
    if(enabled){stopCapture();status('Microphone off. Playback controls still work.');return;}
    starting=true;try{await start();}catch(error){notice.textContent=error.message;}finally{starting=false;}
  };
  el('voice-record').onclick=()=>{if(!enabled || processing || playback || queueActive || queueRunning)return;if(recording)send(context.sampleRate);else {clearAudio();recording=true;status('Recording locally. Click STOP RECORDING when finished.');labels();}};
  el('voice-pause').onclick=pause;el('voice-repeat').onclick=()=>repeat();
  el('voice-speed').oninput=()=>{el('voice-speed-label').textContent=`${speed().toFixed(2)}×`;if(playback)playback.audio.playbackRate=speed();};
  el('voice-output').onchange=()=>{if(!el('voice-output').checked)stopPlayback();};
  el('voice-mode').onchange=()=>{recording=false;clearAudio();labels();};
  el('mic-refresh').onclick=()=>devices().catch(e=>{notice.textContent=e.message;});
  el('mic-device').onchange=async()=>{if(!enabled)return;stopCapture();starting=true;try{await start();}catch(e){notice.textContent=e.message;}finally{starting=false;}};
  navigator.mediaDevices?.addEventListener('devicechange',()=>devices().catch(()=>{}));
  window.addEventListener('pagehide',()=>{stop();lastAudio=null;lastText='';});
  labels();devices().catch(()=>{});
  return {get enabled(){return enabled;},get speakEnabled(){return el('voice-output').checked;},play,repeat,pause,stop,stopPlayback,beginReply,enqueueSpeech,finishReply};
})();
