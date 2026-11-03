/** A card out of view stops its animations (the « Trait » motion: calm ambiance, never spent where nobody looks):
 *  the attribute `offscreen` is set on the card while it is not visible, and its styles pause every animation.
 *  Hestia Weather's sky does the same. Returns the function that stops watching. */
export function watchOffscreen(el:HTMLElement):()=>void {
  if(typeof IntersectionObserver==='undefined')return ()=>{};
  const seen=new IntersectionObserver(entries=>{for(const e of entries)el.toggleAttribute('offscreen',!e.isIntersecting);});
  seen.observe(el);
  return ()=>{seen.disconnect();el.removeAttribute('offscreen');};
}
