const form=document.getElementById('login'), button=document.getElementById('unlock'), password=document.getElementById('password'), error=document.getElementById('login-error');
form.onsubmit=async event=>{
  event.preventDefault();button.disabled=true;error.textContent='';
  try {
    const response=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:password.value})});
    password.value='';
    if(response.ok){location.replace('/');return;}
    error.textContent="You're Larping already";
    if(response.status===429){const note=document.createElement('span');note.textContent=' — Try again in one minute.';error.append(note);}
  }catch(e){error.textContent='Station unavailable. Try again shortly.';}
  finally{button.disabled=false;password.focus();}
};
