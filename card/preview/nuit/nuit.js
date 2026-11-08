// La vraie carte, pièce endormie : la lune vient du moteur (advice3.nuit + reveil), sans rien poser par-dessus.
await import('../../../custom_components/hestia_comfort/frontend/hestia-comfort-card.js?'+Date.now());
const fixtures=await (await fetch('../card-fixtures.json')).json();
const wake=new Date();wake.setDate(wake.getDate()+1);wake.setHours(7,0,0,0);

const CASES=[
  {id:'nuit',title:'La nuit, rien à faire',text:'Pièce endormie jusqu’à 7 h : la lune se pose sur l’image du conseil. Le « i » explique.',
   advice:{title:'Rien à faire',phrase:'21,1 °C, dans votre plage',geste:'nothing',regle:'nothing',nuit:true,reveil:wake.toISOString()}},
  {id:'ferme',title:'La nuit, une fenêtre restée ouverte',text:'Le geste reste proposé ; la lune reste là.',
   advice:{title:'Refermez',phrase:'La fenêtre est ouverte depuis 40 min.',geste:'close',regle:'best',nuit:true,reveil:wake.toISOString()}},
  {id:'jour',title:'Le jour',text:'Pas de lune.',
   advice:{title:'Rien à faire',phrase:'21,1 °C, dans votre plage',geste:'nothing',regle:'nothing',nuit:false,reveil:null}},
];

const scene=fixtures.find(f=>f.id==='calm')??fixtures[0];
const hassFor=c=>({connection:{async subscribeMessage(cb){const v=structuredClone(scene.view);v.entry_id='demo-salon';v.area_id='demo-salon';v.title='Chambre P';
    v.computed_at=new Date().toISOString();if(c.id!=='jour')v.assessment.sun={...(v.assessment.sun||{}),elevation:-25};v.advice3=c.advice;cb({version:1,view:v});return ()=>{};}},
  themes:{darkMode:true},async callWS(){return [{entry_id:'demo-salon',area_id:'demo-salon',title:'Chambre P'}];}});

const main=document.getElementById('main');
let theme='dark';
function build(){
  main.innerHTML=CASES.map(c=>`<section class="prop"><h2>${c.title}</h2><p>${c.text}</p><div class="pair">
    <figure><figcaption>Tuile (repliée)</figcaption><hestia-comfort-card data-c="${c.id}" data-f="tile"></hestia-comfort-card></figure>
    <figure><figcaption>Carte complète (haut)</figcaption><div class="crop"><hestia-comfort-card data-c="${c.id}" data-f="full"></hestia-comfort-card></div></figure>
  </div></section>`).join('');
  for(const el of main.querySelectorAll('hestia-comfort-card')){
    el.setConfig({type:'custom:hestia-comfort-card',entry_id:'demo-salon',format:el.dataset.f,theme,animations:false});
    el.hass=hassFor(CASES.find(c=>c.id===el.dataset.c));
  }
}
build();
document.getElementById('theme').addEventListener('change',e=>{theme=e.target.value;document.documentElement.dataset.theme=theme;build();});
