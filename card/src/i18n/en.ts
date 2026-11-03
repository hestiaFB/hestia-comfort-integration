// The card in English: each French text of the code, and its English words, one part per source file.
// card/tests/i18n.test.mjs checks that none is missing and that none is left unused.
import {EN_ROOM} from './en-room';
import {EN_VIEW} from './en-view';
import {EN_CARDS} from './en-cards';
import {EN_FEEL} from './en-feel';

export const EN:Record<string,string>={...EN_ROOM,...EN_VIEW,...EN_CARDS,...EN_FEEL,
 '{label} : {text}':'{label}: {text}',
};
