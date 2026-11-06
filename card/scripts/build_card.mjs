import {build} from 'esbuild';
import {readFileSync,writeFileSync} from 'node:fs';
import {gzipSync,constants} from 'node:zlib';
import {haCardBuild} from './ha-card-build.mjs';
// Built straight into the integration, which serves the card on every dashboard.
await build({entryPoints:['src/card.ts'],bundle:true,...haCardBuild,target:'es2022',minify:true,
  outfile:'../custom_components/hestia_comfort/frontend/hestia-comfort-card.js',legalComments:'none',loader:{'.css':'text'}});
// Its compressed copy beside it, served in its place to every browser that accepts it (PLAN-OPTIMISATION.md, point 15):
// written at each build, so that it never lags behind the card.
const card='../custom_components/hestia_comfort/frontend/hestia-comfort-card.js';
writeFileSync(card+'.gz',gzipSync(readFileSync(card),{level:constants.Z_BEST_COMPRESSION}));
