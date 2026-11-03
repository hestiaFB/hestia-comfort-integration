import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
// The tab takes the socle's pieces from the newest copy on the page (socle 1.22, socle/hub.ts).
import {hubPieces} from './socle/hub-plugin.mjs';
// The review shared with the card (../card/src/review.ts) uses this package's Lit: one copy in the bundle.
const lit={lit:fileURLToPath(new URL('./node_modules/lit',import.meta.url))};
await build({entryPoints:['panel.ts'],bundle:true,format:'esm',target:'es2022',minify:true,plugins:[hubPieces],alias:lit,
  outfile:'../custom_components/hestia_comfort/frontend/panel.js',legalComments:'none',loader:{'.css':'text'}});
// Shared « Hestia » panel (socle), copied from hestia-ecosysteme/socle/ by its copier.sh.
await build({entryPoints:['socle/shell.ts'],bundle:true,format:'esm',target:'es2022',minify:true,
  outfile:'../custom_components/hestia_comfort/frontend/hestia-socle.js',legalComments:'none'});
