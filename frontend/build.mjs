import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
// The tab takes the socle's pieces from the newest copy on the page (socle 1.22, socle/hub.ts).
import {hubPieces} from './socle/hub-plugin.mjs';
// Socle 1.23: pieces loaded when needed (the English words, the review), then the gzip copy beside each script.
import {DECOUPE,nettoyer,compresser} from './socle/compresser.mjs';
const out='../custom_components/hestia_comfort/frontend';
// The review shared with the card (../card/src/review.ts) uses this package's Lit: one copy in the bundle.
const lit={lit:fileURLToPath(new URL('./node_modules/lit',import.meta.url))};
nettoyer(out);
await build({entryPoints:{panel:'panel.ts'},...DECOUPE,outdir:out,bundle:true,target:'es2022',minify:true,plugins:[hubPieces],alias:lit,
  legalComments:'none',loader:{'.css':'text'}});
// Shared « Hestia-FB » panel (socle), copied from hestia-ecosysteme/socle/ by its copier.sh.
await build({entryPoints:{'hestia-socle':'socle/shell.ts'},...DECOUPE,outdir:out,bundle:true,target:'es2022',minify:true,legalComments:'none'});
compresser(out,['panel.js','hestia-socle.js']);
