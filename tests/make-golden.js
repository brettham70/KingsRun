// Regenerates golden-hands.json. Only run this on purpose: the file is the fixed answer key for the hand solver,
// and every expected cost comes from the brute-force reference, not from the solver being tested.
const fs = require('fs'), path = require('path');
const { loadEngine, rulesFrom, brute } = require('./lib');
const E = loadEngine();
E.seedRng(20261112);
const CASES = [{ name: 'standard' }, { name: 'seventh', o: { extra: [7] } }, { name: 'threes+kings', o: { extra: [3, 13] } }, { name: 'royal pairs', o: { faceBooks: true } },
  { name: 'usurper (dead jokers)', o: { noJoker: true } }, { name: 'low tide + starlight', o: { low: true, star: true } }, { name: 'heavy purse', o: { heavy: true } }];
const out = [];
for (let i = 0; i < 280; i++) {
  const c = CASES[i % CASES.length], wr = 3 + (i % 11), size = 3 + (i % 7);
  const hand = E.makeDeck().slice(0, size).map(x => [x.s, x.r]);
  const cards = hand.map(([s, r], k) => ({ id: k, s, r }));
  const R = c.o ? rulesFrom(wr, c.o) : wr;
  const cost = brute(cards, R);
  out.push({ rules: c.name, o: c.o || null, wr, hand, cost: Math.round(cost * 1024) / 1024 });
}
fs.writeFileSync(path.join(__dirname, 'golden-hands.json'), JSON.stringify(out));
console.log('wrote', out.length, 'hands');
