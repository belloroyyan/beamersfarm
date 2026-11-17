(()=>{
 const button=document.querySelector("[data-install-app]");if(!button)return;let deferredPrompt=null;
 const standalone=()=>window.matchMedia("(display-mode: standalone)").matches||window.navigator.standalone===true;
 if(standalone()){button.hidden=true;return;}button.textContent="Install Beamers";
 window.addEventListener("beforeinstallprompt",event=>{event.preventDefault();deferredPrompt=event;button.hidden=false;});
 button.addEventListener("click",async()=>{if(!deferredPrompt)return;const promptEvent=deferredPrompt;deferredPrompt=null;button.disabled=true;promptEvent.prompt();try{const choice=await promptEvent.userChoice;if(choice&&choice.outcome==="accepted")button.hidden=true;}finally{button.disabled=false;}});
 window.addEventListener("appinstalled",()=>{button.hidden=true;deferredPrompt=null;});
})();
