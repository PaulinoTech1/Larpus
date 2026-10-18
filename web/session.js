(()=>{
function bindSession({element,fetch,onExpired,onRestored}){
 let locked=false,pending=false;
 const panel=element('session-panel'),form=element('session-login'),password=element('session-password'),button=element('session-unlock'),error=element('session-error');
 function unlock(){locked=false;panel.hidden=true;error.textContent='';onRestored();}
 function check(response){
  if(response.status!==401)return response;
  if(!locked){locked=true;panel.hidden=false;error.textContent='';onExpired();password.focus();}
  throw Error('Session expired. Your conversation and draft are retained. Sign in here, then submit again.');
 }
 form.onsubmit=async event=>{
  event.preventDefault();if(pending)return;pending=true;button.disabled=true;error.textContent='';
  try{
   const response=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:password.value})});
   if(response.ok)unlock();else error.textContent=response.status===429?'Too many attempts. Try again in one minute.':"You're Larping already";
  }catch(e){error.textContent='Station unavailable. Your conversation stays here. Try again shortly.';}
  finally{password.value='';pending=false;button.disabled=false;if(locked)password.focus();}
 };
 return {check,get locked(){return locked;}};
}
if(typeof window!=='undefined')window.bindLarpusSession=bindSession;
if(typeof module!=='undefined')module.exports={bindSession};
})();
