// « Participez à l'amélioration du moteur », on Confort's home (between its figures and « À faire / À améliorer ») while the advice engine is in beta (niak-comfort/docs/REGLAGES-3.md
// § 4.1, the validated maquette's first screen). The report comes from Confort (field_report.py, `hestia_comfort/field_report`),
// anonymous; the person sees it, downloads it and decides to share it in a GitHub issue. Nothing is sent from here.
import {html,nothing,type TemplateResult} from 'lit';
import {frame,listRow,listSection,moreRow,noteBox,toggle,t} from './socle/ui';

export interface FieldHelp {key:'sizes'|'history'|'learning';count?:number;rooms?:string[];days?:number;wanted?:number}
export interface FieldReport {report:Record<string,unknown>&{date?:string;versions?:Record<string,unknown>;maison?:Record<string,unknown>;pieces?:unknown[];signalements?:unknown[]};
 helpful:FieldHelp[];beta:boolean;analysis:boolean}

/** The report as a file name and as text: what is downloaded is exactly what is shown. */
const fileName=(r:FieldReport)=>`hestia-confort-rapport-${r.report.date??'rapport'}.json`;
const text=(r:FieldReport)=>JSON.stringify(r.report,null,1);
const size=(r:FieldReport)=>t('{n} Ko',{n:Math.max(1,Math.round(new Blob([text(r)]).size/1024))});

export function downloadReport(r:FieldReport){
 const url=URL.createObjectURL(new Blob([text(r)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download=fileName(r);document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}

/** The GitHub form (.github/ISSUE_TEMPLATE/essai-terrain.yml), its summary filled in: a few lines, the file is dropped by hand. */
export function issueUrl(repository:string,r:FieldReport):string{
 const home=r.report.maison??{},versions=r.report.versions??{};
 const resume=[`${home.pieces??'?'} pièces · chauffage : ${(home.chauffages as string[]|undefined)?.join(', ')||'—'}`,
  `${home.jours_historique??'?'} jours d’historique · outils d’analyse : ${home.outils_analyse?'oui':'non'}`,
  `${r.report.signalements?.length??0} signalement(s) « Ce conseil ne va pas »`].join('\n');
 return `${repository}/issues/new?${new URLSearchParams({template:'essai-terrain.yml',title:`Essai terrain · moteur ${versions.moteur??''}`,
  resume,version:`Hestia Confort ${versions.confort??''} · moteur ${versions.moteur??''}`})}`;
}

function helpLine(h:FieldHelp):TemplateResult{
 const rooms=(h.rooms??[]).join(', ');
 if(h.key==='sizes')return listRow({label:h.count===1?t('1 fenêtre n’a pas de taille.'):t('{n} fenêtres n’ont pas de taille.',{n:h.count??0}),
  sub:t('{rooms} · onglet Ouvertures de la pièce.',{rooms})});
 if(h.key==='history')return listRow({label:t('{days} jours d’historique : {wanted} aideraient.',{days:h.days??0,wanted:h.wanted??30}),
  sub:t('Dans l’enregistreur de Home Assistant : purge_keep_days: {wanted}.',{wanted:h.wanted??30})});
 return listRow({label:t('Encore en apprentissage : {rooms}.',{rooms}),sub:t('Le rapport sera plus parlant après quelques nuits.')});
}

/** The encart. `report` undefined: still loading; `participate` turns the analysis tools on or off (configuration.py set_analysis). */
export function fieldTrialFrame(o:{report?:FieldReport;error?:string;busy:boolean;repository:string;participate:(on:boolean)=>void}):TemplateResult|typeof nothing{
 const r=o.report;
 if(r&&!r.beta)return nothing;
 const body=html`
  <p>${t('Le moteur de conseil est encore en bêta : il apprend de votre maison.')}<br>${t('Vos chiffres l’aident à mieux conseiller toutes les maisons.')}</p>
  <p class="hint">${t('Rien ne part tout seul : vous téléchargez le rapport, puis vous décidez de le partager.')}</p>
  ${listSection(t('Votre participation'),[listRow({label:t('Je participe'),
   sub:r?.analysis?t('Hestia garde le suivi des conseils et le bilan de chaque nuit pour le rapport : environ 50 Mo écrits par jour.')
    :t('Coupé, le rapport ne contient que ce que vos pièces ont appris et vos avis « Ce conseil ne va pas ».'),
   value:toggle(t('Je participe'),!!r?.analysis,o.participate,o.busy||!r)})])}
  ${listSection(t('Ce que contient le rapport'),[
   listRow({label:t('Ce que le moteur a prévu, et ce qui s’est passé, pièce par pièce.')}),
   listRow({label:t('Ce que chaque pièce a appris : inertie, fenêtres, chauffage.')}),
   listRow({label:t('Vos avis « Ce conseil ne va pas », avec la situation du moment.')}),
   listRow({label:t('Le contexte : nombre de pièces, capteurs présents, type de chauffage, jours d’historique, versions.')}),
   listRow({label:t('Jamais dedans : le nom des pièces et des capteurs, la position de la maison, l’historique brut. Les pièces deviennent « Pièce 1, Pièce 2… ».')})])}
  ${r?moreRow(t('Voir le rapport en clair'),size(r),html`<p class="hint">${t('Tel qu’il serait téléchargé.')}</p><pre class="ft-raw">${text(r)}</pre>`)
   :html`<p class="muted" role="status">${o.error??t('Chargement…')}</p>`}
  ${r?.helpful.length?listSection(t('Ce qui le rendrait plus utile'),r.helpful.map(helpLine)):nothing}
  ${noteBox(t('L’issue est publique.'),t('Tout le monde pourra lire le rapport sur GitHub.'))}
  <div class="ft-actions"><button class="primary" type="button" ?disabled=${!r} @click=${()=>r&&downloadReport(r)}>${t('Télécharger mon rapport')}</button>
   ${r?html`<a class="ex-act" href=${issueUrl(o.repository,r)} target="_blank" rel="noreferrer">${t('Préparer une issue sur GitHub')}</a>`:nothing}</div>`;
 return frame(t('Participez à l’amélioration du moteur'),body,{className:'ft-frame',collapsible:true,open:true,count:t('Moteur en bêta')});
}
