import {html,svg} from 'lit';
import {t} from './socle/ui';

/** The overhang above a window, seen from the side (REGLAGES-3.md § 4.4): A its depth from the wall, B the gap down to
 *  the top of the window. Colours from the hub's theme, so it reads in light and dark. */
export function overhangSketch(){
 return html`<figure class="sketch"><svg viewBox="0 0 340 210" role="img" aria-label=${t('Coupe d’un mur vu de côté : l’avancée dépasse du mur, la fenêtre est en dessous. A : profondeur de l’avancée, depuis le mur. B : écart entre le dessous de l’avancée et le haut de la fenêtre.')}>
  ${svg`<defs><marker id="sk-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="sk-acc-fill"/></marker></defs>
  <g class="sk-sun"><circle cx="300" cy="26" r="11"/><path d="M286 40 L214 110 M298 44 L226 114" stroke-dasharray="4 5"/></g>
  <rect x="40" y="40" width="34" height="160" class="sk-wall"/>
  <rect x="40" y="30" width="170" height="12" rx="2" class="sk-roof"/>
  <rect x="40" y="96" width="34" height="78" class="sk-glass"/>
  <text x="22" y="140" class="sk-txt" transform="rotate(-90 22 140)">${t('mur')}</text>
  <text x="80" y="150" class="sk-txt">${t('fenêtre')}</text>
  <text x="216" y="40" class="sk-txt">${t('avancée')}</text>
  <line x1="74" y1="16" x2="210" y2="16" class="sk-acc" marker-start="url(#sk-arrow)" marker-end="url(#sk-arrow)"/>
  <line x1="74" y1="10" x2="74" y2="30" class="sk-thin"/><line x1="210" y1="10" x2="210" y2="30" class="sk-thin"/>
  <circle cx="142" cy="16" r="9" class="sk-badge"/><text x="142" y="20" class="sk-badge-t">A</text>
  <line x1="118" y1="42" x2="118" y2="96" class="sk-acc" marker-start="url(#sk-arrow)" marker-end="url(#sk-arrow)"/>
  <line x1="74" y1="96" x2="126" y2="96" class="sk-thin"/>
  <circle cx="134" cy="69" r="9" class="sk-badge"/><text x="134" y="73" class="sk-badge-t">B</text>`}
 </svg><figcaption class="hint">${t('Vue de côté, comme si on coupait le mur.')}</figcaption></figure>`;
}
