// Browser tests (need Playwright):   node tests/browser-tests.js
// Plays whole games through the real page code in every mode, checking the cards and scores stay consistent after every
// move, then checks the menus, the walkthrough and what happens to old or damaged saved games.
const { chromium, devices } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const PORT = 8795;
const srv = http.createServer((q, r) => {
  let f = path.join(root, decodeURIComponent(q.url.split('?')[0])); if (f.endsWith('/')) f += 'index.html';
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; }
    r.writeHead(200, { 'content-type': { '.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.png': 'image/png' }[path.extname(f)] || 'application/octet-stream' }); r.end(d); });
}).listen(PORT);
const URL = `http://localhost:${PORT}/`;
let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); passed++; console.log('  ok   ' + name); }
  catch (e) { failed++; console.log('  FAIL ' + name + '\n         ' + String(e.message).split('\n').join('\n         ')); }
}
const ok = (c, m) => { if (!c) throw new Error(m || 'assertion failed'); };
const eq = (a, b, m) => { if (a !== b) throw new Error((m || 'expected equal') + `: got ${JSON.stringify(a)}, expected ${JSON.stringify(b)}`); };

// Code that runs inside the page: a stand-in player that makes sensible moves, so whole games can be played at speed.
const BOT = `
window.__bot = {
  seat(){ // one move for a human seat
    const p = cur(), R = rulesFor(G.turn);
    if (G.phase === 'draw') {
      const top = G.discard[G.discard.length - 1]; let take = false;
      if (top && canTakePile(G.turn)) { if (isWild(top, R)) take = true; else { const d = bestDiscard([...p.hand, top], R); take = d.card !== top && d.cost < solve(p.hand, R).cost; } }
      p.hand.push(take ? G.discard.pop() : drawDeck()); G.phase = 'discard';
    } else { const d = bestDiscard(p.hand, rulesFor(G.turn)); p.hand = p.hand.filter(x => x !== d.card); G.discard.push(d.card); G.log = 'moved'; endTurn(); }
  },
  step(){
    if (G.phase === 'roundEnd') { if (G.mode === 'run') { openCourt(); } else startRound(); return; }
    if (G.phase === 'court') { startRound(); return; }
    if (cur().ai) { if (G.phase === 'draw') aiDraw(); else aiDiscard(); } else this.seat();
  },
  // Play a whole game; returns problems found (empty = fine).
  play(limit = 6000){
    const bad = []; let n = 0;
    while (G.phase !== 'gameEnd' && n++ < limit) {
      this.step();
      if (!validGame(G)) { bad.push('inconsistent state at step ' + n + ' phase ' + G.phase + ' round ' + G.round); break; }
    }
    if (G.phase !== 'gameEnd') bad.push('game did not finish in ' + limit + ' steps');
    return bad;
  }
};`;

(async () => {
  const b = await chromium.launch();
  const fresh = async (o = {}) => {
    const ctx = await b.newContext({ ...devices['Pixel 7'], serviceWorkers: 'block', ...o });
    const p = await ctx.newPage(); p.errs = []; p.on('pageerror', e => p.errs.push(String(e)));
    await p.goto(URL); await p.waitForTimeout(300); await p.evaluate(BOT); return { ctx, p };
  };

  console.log('Whole games (seeded, so any failure can be replayed)');
  {
    const { ctx, p } = await fresh();
    for (const [name, cfg] of [['vs computer, 1 opponent', { mode: 'ai', count: 1 }], ['vs computer, 3 opponents', { mode: 'ai', count: 3 }], ['pass and play, 4 players', { mode: 'pp', count: 4, names: ['A', 'B', 'C', 'D'] }]]) {
      await test(name + ': 12 full games stay consistent and scores add up', async () => {
        const r = await p.evaluate(cfg => {
          clearTimeout(timer); timer = null; const problems = [];
          for (let seed = 1; seed <= 12; seed++) {
            seedRng(seed * 977); newGame({ ...cfg, level: ['easy', 'normal', 'hard'][seed % 3] }); clearTimeout(timer); timer = null;
            const bad = __bot.play(); problems.push(...bad.map(x => 'seed ' + seed + ': ' + x));
            if (G.round !== 11) problems.push('seed ' + seed + ' ended in round ' + G.round);
            for (const pl of G.players) { if (pl.rounds.length !== 11) problems.push('rounds recorded ' + pl.rounds.length); if (pl.rounds.reduce((a, x) => a + x, 0) !== pl.score) problems.push(pl.name + ' score does not equal the sum of its rounds'); if (pl.rounds.some(x => !Number.isInteger(x) || x < 0)) problems.push('bad round score'); }
          }
          clearRng(); return problems;
        }, cfg);
        ok(!r.length, r.slice(0, 3).join('\n'));
      });
    }
    await test('The Run: 40 full runs end in a win or bankruptcy, with sane gold and consistent cards', async () => {
      const r = await p.evaluate(() => {
        clearTimeout(timer); timer = null; const problems = []; let won = 0;
        for (let seed = 1; seed <= 40; seed++) {
          seedRng(seed * 31); newGame({ mode: 'run', count: 2, names: [] }); clearTimeout(timer); timer = null;
          problems.push(...__bot.play().map(x => 'seed ' + seed + ': ' + x));
          if (!['won', 'bust'].includes(G.run.over)) problems.push('seed ' + seed + ': run ended with over=' + G.run.over);
          if (G.run.over === 'won') { won++; if (G.round !== 11 || G.run.gold < 0) problems.push('seed ' + seed + ': a win in round ' + G.round + ' with ' + G.run.gold + ' gold'); }
          if (G.run.over === 'bust' && G.run.gold >= 0) problems.push('seed ' + seed + ': bust with ' + G.run.gold + ' gold');
          if (!Number.isFinite(G.run.gold)) problems.push('gold is not a number');
        }
        clearRng(); return { problems, won };
      });
      ok(!r.problems.length, r.problems.slice(0, 3).join('\n')); ok(r.won > 0 && r.won < 40, 'wins ' + r.won + ' of 40: a run should be neither impossible nor automatic');
    });
    await test('computer levels: the same player does better against Easy than Normal than Hard', async () => {
      const w = await p.evaluate(() => {
        const rate = lvl => { let pts = 0; const N = 120;
          for (let g = 1; g <= N; g++) { seedRng(g * 7919); newGame({ mode: 'ai', count: 2, level: lvl }); clearTimeout(timer); timer = null; __bot.play();
            const s = G.players.map(x => x.score), min = Math.min(...s); if (s[0] === min) pts += 1 / s.filter(x => x === min).length; }
          clearRng(); return pts / N; };
        return { easy: rate('easy'), normal: rate('normal'), hard: rate('hard') };
      });
      console.log(`         player win rate against 2 computers: Easy ${(w.easy * 100).toFixed(0)}%, Normal ${(w.normal * 100).toFixed(0)}%, Hard ${(w.hard * 100).toFixed(0)}%`);
      ok(w.easy > w.normal + 0.04 && w.normal > w.hard + 0.04, 'levels are not clearly ordered');
      ok(w.hard > 0.15 && w.hard < 0.5, 'Hard should be a fair fight, not impossible or easy');
    });
    await test('no page errors during any of that', async () => eq(p.errs.length, 0, p.errs[0]));
    await ctx.close();
  }

  console.log('Menus and walkthrough');
  await test('the menu offers Easy, Normal and Hard, and remembers the choice', async () => {
    const { ctx, p } = await fresh();
    await p.click('#menuBtn');
    ok(await p.$('[data-act="level"][data-l="easy"]') && await p.$('[data-act="level"][data-l="hard"]'), 'level buttons missing');
    eq(await p.getAttribute('[data-l="normal"]', 'aria-pressed'), 'true', 'Normal should be the starting choice');
    await p.click('[data-l="hard"]'); await p.click('[data-act="new"]'); await p.waitForTimeout(100);
    eq(await p.evaluate(() => G.cfg.level), 'hard'); ok(await p.evaluate(() => G.players.slice(1).every(x => x.skill === 1)), 'Hard computers should have skill 1');
    await p.click('#menuBtn'); eq(await p.getAttribute('[data-l="hard"]', 'aria-pressed'), 'true', 'choice should be remembered');
    await p.click('[data-l="easy"]'); await p.click('[data-act="new"]');
    ok(await p.evaluate(() => G.players.slice(1).every(x => x.skill < .6)), 'Easy computers should make mistakes');
    eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });
  await test('the level shows in recent games', async () => {
    const { ctx, p } = await fresh();
    const t = await p.evaluate(() => { seedRng(5); newGame({ mode: 'ai', count: 2, level: 'easy' }); clearTimeout(timer); timer = null; __bot.play(); clearRng(); return recentGames(); });
    ok(/Vs computer · Easy/.test(t), 'recent games should name the level'); await ctx.close();
  });
  await test('the Run walkthrough shows once, pauses the computers, and can be replayed', async () => {
    const { ctx, p } = await fresh();
    await p.click('#menuBtn'); await p.click('[data-m="run"]'); await p.click('[data-act="new"]');
    ok(await p.isVisible('.tour'), 'walkthrough should show on the first Run');
    ok((await p.textContent('.tour')).includes('Gold is your life'));
    const before = await p.evaluate(() => JSON.stringify([G.phase, G.turn, G.deck.length, G.discard.length]));
    await p.waitForTimeout(2200);
    eq(await p.evaluate(() => JSON.stringify([G.phase, G.turn, G.deck.length, G.discard.length])), before, 'the computers moved while the walkthrough was open');
    await p.click('[data-act="tournext"]'); ok((await p.textContent('.tour')).includes('Court')); await p.click('[data-act="tournext"]'); ok((await p.textContent('.tour')).includes('boss'));
    await p.click('[data-act="tournext"]'); ok(!(await p.isVisible('.tour')), 'should close after the last card');
    eq(await p.evaluate(() => localStorage.getItem('kingsrun-tour')), '1');
    await p.click('#menuBtn'); await p.click('[data-act="restartAsk"]'); await p.click('[data-act="restartYes"]'); ok(!(await p.isVisible('.tour')), 'must not show again');
    await p.click('#menuBtn'); await p.click('[data-act="mview"][data-v="rules"]'); await p.click('[data-act="tourshow"]');
    ok(await p.isVisible('.tour'), 'replay button should reopen it'); await p.click('[data-act="tourskip"]'); ok(!(await p.isVisible('.tour')));
    eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });
  await test('Skip also counts as seen', async () => {
    const { ctx, p } = await fresh();
    await p.click('#menuBtn'); await p.click('[data-m="run"]'); await p.click('[data-act="new"]'); await p.click('[data-act="tourskip"]');
    ok(!(await p.isVisible('.tour'))); eq(await p.evaluate(() => localStorage.getItem('kingsrun-tour')), '1'); await ctx.close();
  });

  console.log('Saved games in the browser');
  const KEY = 'kingsrun-v1';
  await test('games are saved with a version number', async () => {
    const { ctx, p } = await fresh(); await p.evaluate(() => commit());
    const s = JSON.parse(await p.evaluate(k => localStorage.getItem(k), KEY)); eq(s.v, 2); ok(s.g && s.g.players); await ctx.close();
  });
  await test('a game saved by the previous version resumes where it was, at Hard', async () => {
    const { ctx, p } = await fresh();
    const legacy = await p.evaluate(() => { seedRng(8); newGame({ mode: 'ai', count: 2, level: 'normal' }); clearTimeout(timer); timer = null; for (let i = 0; i < 9; i++) __bot.step(); clearRng(); const g = JSON.parse(JSON.stringify(G)); delete g.cfg.level; g.players.forEach(x => delete x.skill); return g; });
    await p.evaluate(([k, g]) => localStorage.setItem(k, JSON.stringify(g)), [KEY, legacy]);
    await p.reload(); await p.waitForTimeout(300);
    const r = await p.evaluate(() => ({ round: G.round, turn: G.turn, level: G.cfg.level, hand: G.players[0].hand.length, log: G.log }));
    eq(r.round, legacy.round); eq(r.turn, legacy.turn); eq(r.level, 'hard'); eq(r.hand, legacy.players[0].hand.length); ok(!/couldn/.test(r.log), 'should not claim the save was lost');
    eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });
  for (const [name, mutate] of [['a missing card', g => g.players[1].hand.pop()], ['a made-up phase', g => { g.phase = 'banana'; }]]) {
    await test(`a damaged save (${name}) is set aside and a new game starts, with a note`, async () => {
      const { ctx, p } = await fresh();
      const bad = await p.evaluate(m => { newGame({ mode: 'ai', count: 2 }); clearTimeout(timer); timer = null; const g = JSON.parse(JSON.stringify(G)); return g; }, null);
      mutate(bad); await p.evaluate(([k, g]) => localStorage.setItem(k, JSON.stringify({ v: 2, g })), [KEY, bad]);
      await p.reload(); await p.waitForTimeout(300);
      ok(await p.evaluate(() => /couldn’t be restored/.test(G.log)), 'should say what happened');
      ok(await p.evaluate(() => validGame(G)), 'new game must be valid');
      ok(await p.evaluate(k => !!localStorage.getItem(k + '-unreadable'), KEY), 'the old save should be kept aside');
      eq(p.errs.length, 0, p.errs[0]); await ctx.close();
    });
  }
  await test('a save from a newer app version is not loaded or crashed on', async () => {
    const { ctx, p } = await fresh();
    await p.evaluate(k => localStorage.setItem(k, JSON.stringify({ v: 99, g: { anything: true } })), KEY);
    await p.reload(); await p.waitForTimeout(300);
    ok(await p.evaluate(() => validGame(G))); ok(await p.evaluate(k => !!localStorage.getItem(k + '-unreadable'), KEY)); eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });
  await test('garbage in storage does not stop the game opening', async () => {
    const { ctx, p } = await fresh();
    await p.evaluate(k => localStorage.setItem(k, '{not json'), KEY); await p.reload(); await p.waitForTimeout(300);
    ok(await p.evaluate(() => validGame(G))); eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });
  await test('a saved Run resumes with its gold and Regalia', async () => {
    const { ctx, p } = await fresh();
    await p.evaluate(() => { seedRng(2); newGame({ mode: 'run', count: 2 }); clearTimeout(timer); timer = null; G.run.gold = 77; G.run.regalia = ['patron', 'notarealid']; save(); clearRng(); });
    await p.reload(); await p.waitForTimeout(300);
    const r = await p.evaluate(() => ({ mode: G.mode, gold: G.run.gold, reg: G.run.regalia.join() })); eq(r.mode, 'run'); eq(r.gold, 77); eq(r.reg, 'patron', 'unknown Regalia should be dropped, not crash');
    eq(p.errs.length, 0, p.errs[0]); await ctx.close();
  });

  await b.close(); srv.close();
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('TEST RUNNER ERROR', e); process.exit(1); });
