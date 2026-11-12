// Kingsrun tests that need nothing installed:   node tests/run-tests.js
// They load the real engine and save logic out of index.html. Browser tests (full games, menus): node tests/browser-tests.js
const { loadEngine, rulesFrom, brute } = require('./lib');
const golden = require('./golden-hands.json');
const E = loadEngine();
let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ok   ' + name); }
  catch (e) { failed++; console.log('  FAIL ' + name + '\n         ' + String(e.message).split('\n').join('\n         ')); }
}
const eq = (a, b, m) => { if (a !== b) throw new Error((m || 'expected equal') + `: got ${a}, expected ${b}`); };
const ok = (c, m) => { if (!c) throw new Error(m || 'assertion failed'); };
const cards = h => h.map(([s, r], k) => ({ id: k, s, r }));
const round = x => Math.round(x * 1024) / 1024;

console.log('Hand solver');
test('matches the answer key on every golden hand (' + golden.length + ')', () => {
  const bad = [];
  for (const g of golden) {
    const R = g.o ? rulesFrom(g.wr, g.o) : g.wr;
    const s = E.solve(cards(g.hand), R);
    if (round(s.cost) !== g.cost) bad.push(`${g.rules} wr${g.wr} ${JSON.stringify(g.hand)} solver ${round(s.cost)} key ${g.cost}`);
  }
  ok(!bad.length, bad.length + ' wrong, e.g. ' + bad[0]);
});
test('agrees with the brute-force reference on fresh seeded hands', () => {
  E.seedRng(7);
  let n = 0;
  for (let t = 0; t < 600; t++) {
    const wr = 3 + (t % 11), hand = E.makeDeck().slice(0, 3 + (t % 6));
    const s = E.solve(hand, wr); n++;
    eq(s.cost, brute(hand, wr), `hand ${JSON.stringify(hand.map(c => [c.s, c.r]))} wild ${wr}`);
  }
  E.clearRng();
});
test('the groups it returns use every card exactly once and add up to the cost it reports', () => {
  E.seedRng(11);
  for (let t = 0; t < 400; t++) {
    const wr = 3 + (t % 11), hand = E.makeDeck().slice(0, 3 + (t % 11));
    const s = E.solve(hand, wr);
    const used = [...s.melds.flatMap(m => m.cards), ...s.dead].map(c => c.id).sort((a, b) => a - b);
    eq(JSON.stringify(used), JSON.stringify(hand.map(c => c.id).sort((a, b) => a - b)), 'cards lost or duplicated');
    eq(s.dead.reduce((x, c) => x + E.pts(c, wr), 0), s.cost, 'dead cards must add up to the cost');
    for (const m of s.melds) ok(m.cards.length >= 3, 'a group has fewer than 3 cards');
  }
  E.clearRng();
});
test('a hand with nothing to match costs the sum of its cards', () => {
  const s = E.solve(cards([[0, 3], [1, 5], [2, 8], [3, 10]]), 13);   // no wild ranks, no pairs, no runs
  eq(s.cost, 3 + 5 + 8 + 10); eq(s.melds.length, 0);
});
test('Jokers and wild ranks make groups', () => {
  eq(E.solve(cards([[0, 5], [1, 5], [-1, 0]]), 9).cost, 0, 'two 5s and a Joker');
  eq(E.solve(cards([[2, 6], [2, 8], [2, 9], [-1, 0]]), 13).cost, 0, 'run 6-_-8-9 with a Joker');
  eq(E.solve(cards([[0, 4], [1, 4], [3, 9]]), 9).cost, 0, 'the wild 9 completes the book of 4s');
  eq(E.solve(cards([[0, 4], [1, 4], [3, 8]]), 9).cost, 16, 'without it the pair of 4s and the 8 are left over');
});
test('runs do not wrap and do not mix suits', () => {
  eq(E.solve(cards([[0, 12], [0, 13], [0, 3]]), 7).cost, 28, 'Q K 3 is not a run');
  eq(E.solve(cards([[0, 5], [1, 6], [2, 7]]), 13).cost, 18, 'mixed suits are not a run');
});
test('scoring: face value, J11 Q12 K13, wild 20, Joker 50', () => {
  eq(E.pts({ s: 0, r: 7 }, 3), 7); eq(E.pts({ s: 0, r: 13 }, 3), 13); eq(E.pts({ s: 0, r: 3 }, 3), 20); eq(E.pts({ s: -1, r: 0 }, 3), 50);
});
test('Run rules: an extra wild rank turns a pair into a book', () => {
  const hand = cards([[0, 7], [1, 7], [2, 4]]);
  eq(E.solve(hand, 9).cost, 18, 'standard rules: 7, 7 and 4 are all left over');
  eq(round(E.solve(hand, rulesFrom(9, { extra: [7] })).cost), round(0), 'with 7s wild they form a book with the 4');
});
test('Run rules: free cards cost nothing but still have to be grouped to go out', () => {
  const R = rulesFrom(13, { low: true });
  const s = E.solve(cards([[0, 3], [1, 4]]), R);
  ok(s.cost > 0 && s.cost < 1, 'cost is a tiny positive amount, so the hand is not "out"');
  eq(Math.floor(s.cost), 0, 'but the bill rounds down to nothing');
});
test('Run rules agree with the reference solver', () => {
  E.seedRng(3);
  const sets = [{ extra: [7] }, { extra: [3, 13] }, { faceBooks: true }, { noJoker: true }, { low: true, star: true }, { heavy: true }];
  for (let t = 0; t < 480; t++) {
    const o = sets[t % sets.length], wr = 3 + (t % 11), R = rulesFrom(wr, o), hand = E.makeDeck().slice(0, 3 + (t % 6));
    eq(round(E.solve(hand, R).cost), round(brute(hand, R)), JSON.stringify(o) + ' ' + JSON.stringify(hand.map(c => [c.s, c.r])));
  }
  E.clearRng();
});
test('a dead Joker never joins a group', () => {
  const R = rulesFrom(13, { noJoker: true });
  const s = E.solve(cards([[0, 5], [1, 5], [2, 5], [-1, 0]]), R);
  ok(s.dead.some(c => c.s < 0), 'the Joker should be left over'); ok(round(s.cost) >= 50);
});
test('Hard AI never throws away a wild card it can keep', () => {
  E.seedRng(5);
  for (let t = 0; t < 200; t++) {
    const wr = 3 + (t % 11), hand = E.makeDeck().slice(0, 4 + (t % 8));
    const d = E.bestDiscard(hand, wr);
    if (hand.some(c => !E.isWild(c, wr))) ok(!E.isWild(d.card, wr), 'discarded a wild');
  }
  E.clearRng();
});

console.log('Randomness');
test('a seed always gives the same deck, and different seeds give different decks', () => {
  E.seedRng(42); const a = E.makeDeck().map(c => c.id).join(); E.seedRng(42); const b = E.makeDeck().map(c => c.id).join(); E.seedRng(43); const c = E.makeDeck().map(c => c.id).join();
  eq(a, b, 'same seed'); ok(a !== c, 'different seed gave the same deck'); E.clearRng();
});
test('without a seed, decks differ every time', () => {
  E.clearRng(); ok(E.makeDeck().map(c => c.id).join() !== E.makeDeck().map(c => c.id).join());
});
test('the deck has 116 cards: two of every card in five suits plus six Jokers', () => {
  const d = E.makeDeck(); eq(d.length, 116); eq(new Set(d.map(c => c.id)).size, 116);
  eq(d.filter(c => c.s < 0).length, 6); for (let s = 0; s < 5; s++) for (let r = 3; r <= 13; r++) eq(d.filter(c => c.s === s && c.r === r).length, 2, `suit ${s} rank ${r}`);
});
test('shuffle puts every card in every position about equally often', () => {
  E.seedRng(99); const N = 12000, k = 6, counts = Array.from({ length: k }, () => Array(k).fill(0));
  for (let i = 0; i < N; i++) { const a = E.shuffle([0, 1, 2, 3, 4, 5]); a.forEach((v, pos) => counts[v][pos]++); }
  const exp = N / k; let chi = 0; for (const row of counts) for (const c of row) chi += (c - exp) ** 2 / exp;
  ok(chi < 60, 'chi-square ' + chi.toFixed(1) + ' is too high (free-fall would be ~25 on average, 60 is far in the tail)'); E.clearRng();
});
test('randInt stays in range and covers every value', () => {
  E.seedRng(1); const seen = new Set(); for (let i = 0; i < 2000; i++) { const v = E.randInt(7); ok(v >= 0 && v < 7); seen.add(v); } eq(seen.size, 7); E.clearRng();
});

console.log('Saved games');
// A genuine game state, built the way newGame builds one.
function makeGame(mode = 'ai', n = 3) {
  const deck = E.makeDeck(), round = 4;
  const players = Array.from({ length: n }, (_, i) => ({ name: i ? 'CPU' + i : 'You', ai: !!i, hand: deck.splice(0, round + 2), score: 5, rounds: [3, 2] }));
  const g = { mode, cfg: { mode, count: n - 1, names: [] }, players, reveal: false, round, dealer: 0, deck, discard: [deck.pop()], turn: 0, phase: 'draw', outBy: null, finalLeft: 0, log: '', fresh: null, result: null };
  if (mode === 'run') g.run = { gold: 30, regalia: ['patron'], decrees: [], shop: [] };
  return g;
}
const clone = x => JSON.parse(JSON.stringify(x));
test('a fresh game is valid', () => { for (const m of ['ai', 'pp', 'run']) ok(E.validGame(makeGame(m)), m); });
test('a version-1 save (the bare game) migrates, and old games keep playing at Hard', () => {
  const g = makeGame('ai'); delete g.cfg.level;
  const m = E.migrateSave(clone(g)); ok(m, 'should migrate'); eq(m.cfg.level, 'hard'); eq(m.round, 4);
});
test('a very old save with no mode or settings still loads', () => {
  const g = makeGame('ai'); delete g.mode; delete g.cfg; const m = E.migrateSave(g); ok(m); eq(m.mode, 'ai'); eq(m.cfg.count, 2);
});
test('a version-2 save round-trips and keeps its level', () => {
  const g = makeGame('ai'); g.cfg.level = 'easy';
  const m = E.migrateSave(JSON.parse(JSON.stringify({ v: E.SAVE_VERSION, g }))); ok(m); eq(m.cfg.level, 'easy');
});
test('a Run save round-trips', () => { const m = E.migrateSave({ v: 2, g: makeGame('run') }); ok(m); eq(m.run.gold, 30); });
test('a save from a newer app is refused, not guessed at', () => { eq(E.migrateSave({ v: E.SAVE_VERSION + 1, g: makeGame() }), null); });
test('damaged saves are refused', () => {
  const dmg = f => { const g = makeGame(); f(g); return E.migrateSave({ v: 2, g }); };
  eq(dmg(g => g.players[1].hand.pop()), null, 'a missing card');
  eq(dmg(g => g.deck.push({ ...g.deck[0] })), null, 'a duplicated card');
  eq(dmg(g => { g.turn = 7; }), null, 'a turn that does not exist');
  eq(dmg(g => { g.phase = 'banana'; }), null, 'an unknown phase');
  eq(dmg(g => { g.round = 12; }), null, 'a round past 11');
  eq(dmg(g => { g.players.length = 1; }), null, 'one player');
  eq(dmg(g => { g.players[0].score = 'x'; }), null, 'a text score');
  eq(dmg(g => { g.deck[0].s = 9; }), null, 'a nonsense suit');
  const r = makeGame('run'); delete r.run.gold; eq(E.migrateSave({ v: 2, g: r }), null, 'a Run with no gold');
});
test('junk is refused without throwing', () => { for (const x of [null, undefined, 5, 'x', [], {}, { v: 2 }, { v: 'a', g: {} }, { v: 0, g: makeGame() }]) eq(E.migrateSave(x), null, JSON.stringify(x)); });
test('migration does not change the original object', () => {
  const g = makeGame('ai'); delete g.cfg.level; const before = JSON.stringify(g); E.migrateSave(g); eq(JSON.stringify(g), before);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
