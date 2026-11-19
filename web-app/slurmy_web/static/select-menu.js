'use strict';
// Keep native selects as the data source; paint their menus using theme surfaces.
window.SlurmySelects=(()=>{
 const controls=new Map();let active=null,typed='',typingTimer;
 function close(focus=false){if(!active)return;const current=active;active=null;current.menu.hidePopover();current.button.setAttribute('aria-expanded','false');if(focus)current.button.focus();}
 function sync(control){
  const {select,button,menu,value}=control;
  value.textContent=select.selectedOptions[0]?.textContent||'Choose…';button.disabled=select.disabled;
  if(select.disabled&&active===control)close();
  const signature=JSON.stringify([...select.options].map(option=>[option.value,option.textContent,option.disabled]));
  if(signature!==control.signature){
   control.signature=signature;menu.replaceChildren();
   for(const option of select.options){
    const item=document.createElement('button');item.type='button';item.tabIndex=-1;item.role='option';item.dataset.value=option.value;item.textContent=option.textContent;item.disabled=option.disabled;
    item.addEventListener('click',event=>{event.preventDefault();const changed=select.value!==option.value;select.value=option.value;sync(control);close(true);if(changed)select.dispatchEvent(new Event('change',{bubbles:true}));});
    menu.append(item);
   }
  }
  for(const item of menu.children)item.setAttribute('aria-selected',String(item.dataset.value===select.value));
 }
 function open(control){
  if(active===control){close();return;}close();sync(control);if(control.button.disabled)return;
  const rect=control.button.getBoundingClientRect(),menu=control.menu;
  const below=innerHeight-rect.bottom-12,above=rect.top-12,up=below<180&&above>below;
  menu.style.width=`${Math.min(rect.width,innerWidth-16)}px`;menu.style.left=`${Math.max(8,Math.min(rect.left,innerWidth-rect.width-8))}px`;
  menu.style.maxHeight=`${Math.max(80,Math.min(360,up?above:below))}px`;menu.style.top=up?'auto':`${rect.bottom+7}px`;menu.style.bottom=up?`${innerHeight-rect.top+7}px`:'auto';
  active=control;menu.showPopover();control.button.setAttribute('aria-expanded','true');
  (menu.querySelector('[aria-selected="true"]:not(:disabled)')||menu.querySelector('button:not(:disabled)'))?.focus();
 }
 function enhance(select){
  if(controls.has(select)||select.multiple||select.closest('template'))return;
  const label=select.getAttribute('aria-label')||[...(select.closest('label')?.childNodes||[])].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent.trim()).join(' ')||'Choose an option';
  const wrapper=document.createElement('span');wrapper.className='themed-select';select.replaceWith(wrapper);wrapper.append(select);select.hidden=true;
  const button=document.createElement('button');button.type='button';button.className='secondary themed-select-toggle';button.role='combobox';button.setAttribute('aria-label',label);button.setAttribute('aria-haspopup','listbox');button.setAttribute('aria-expanded','false');
  const value=document.createElement('span'),arrow=document.createElement('span');arrow.textContent='▾';arrow.setAttribute('aria-hidden','true');button.append(value,arrow);
  const menu=document.createElement('div');menu.className='split-menu themed-select-menu';menu.setAttribute('popover','manual');menu.role='listbox';menu.id=`${select.id}-options`;menu.setAttribute('aria-label',label);button.setAttribute('aria-controls',menu.id);
  wrapper.append(button,menu);const control={select,button,menu,value};controls.set(select,control);
  button.addEventListener('click',event=>{event.preventDefault();open(control);});
  button.addEventListener('keydown',event=>{if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();open(control);}});
  menu.addEventListener('keydown',event=>{
   const items=[...menu.children].filter(item=>!item.disabled),index=items.indexOf(document.activeElement);
   if(event.key==='Escape'){event.preventDefault();close(true);}
   else if(event.key==='Tab')close();
   else if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){event.preventDefault();items[event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();}
   else if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&event.key!==' '){clearTimeout(typingTimer);typed+=event.key.toLowerCase();typingTimer=setTimeout(()=>typed='',700);items.find(item=>item.textContent.toLowerCase().startsWith(typed))?.focus();}
  });
  select.addEventListener('change',()=>sync(control));
  new MutationObserver(()=>sync(control)).observe(select,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','selected','label','value'],characterData:true});
  sync(control);
 }
 document.addEventListener('click',event=>{if(active&&!active.menu.contains(event.target)&&!active.button.contains(event.target))close();});
 document.addEventListener('scroll',event=>{if(active&&!active.menu.contains(event.target))close();},true);
 window.addEventListener('resize',()=>close());
 document.querySelectorAll('select').forEach(enhance);
 return {refresh:()=>{for(const control of controls.values())sync(control);}};
})();
