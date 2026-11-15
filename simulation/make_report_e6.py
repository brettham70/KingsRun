#!/usr/bin/env python3
"""Writes boss_rules_report.md. Usage: python3 simulation/make_report_e6.py <dir>"""
import sys, json
import pandas as pd, numpy as np
D = sys.argv[1]; T = pd.read_csv(f'{D}/tables/e6_summary.csv'); V = json.load(open(f'{D}/validation_results.json')); N = int(T.runs.iloc[0])
pc = lambda x, d=0: f'{100*x:.{d}f}%'
g = lambda sk, ct, rule, col='completion': T[(T.skill == sk) & (T.court == ct) & (T.rule == rule)].iloc[0][col]
ORDER = ['current', 'steal', 'tribute', 'rematch0', 'rematch5', 'rematch10', 'rematch_esc', 'rematch20', 'rematch_pct25', 'rematch5_sym', 'finalgate', 'finalgate_sym', 'gate']
def comp_table(sk):
    rows = []
    for rule in ORDER:
        r = {'Rule': T[T.rule == rule].name.iloc[0]}
        for ct, lab in (('none', 'No purchases'), ('defensive', 'Defensive Court'), ('aggressive', 'Aggressive Court')):
            x = T[(T.skill == sk) & (T.court == ct) & (T.rule == rule)].iloc[0]
            r[lab] = pc(x.completion) if rule == 'current' else f"{pc(x.completion)} ({100*x.diff_vs_current:+.0f})"
        rows.append(r)
    return pd.DataFrame(rows).to_markdown(index=False)
def detail(sk, ct):
    rows = []
    for rule in ['current', 'rematch0', 'rematch5', 'rematch10', 'rematch20', 'rematch_pct25', 'rematch5_sym']:
        x = T[(T.skill == sk) & (T.court == ct) & (T.rule == rule)].iloc[0]
        rows.append({'Rule': x['name'], 'Completed': pc(x.completion), 'Ended at Miser': pc(x.ended_at_miser), 'at Jester': pc(x.ended_at_jester), 'at Usurper': pc(x.ended_at_usurper),
            'Attempts: Miser / Jester / Usurper': '—' if rule == 'current' else f"{x.attempts_miser:.1f} / {x.attempts_jester:.1f} / {x.attempts_usurper:.1f}", 'Runs with 3+ attempts at one boss': pc(x.pct_runs_3plus_attempts),
            'Most attempts seen': int(x.max_attempts), 'Rounds played per run': f"{x.rounds_played:.1f}", 'Gold paid in tolls': f"{x.mean_tolls_paid:.0f}", 'Median final treasury': f"{x.median_final_treasury:.0f}"})
    return pd.DataFrame(rows).to_markdown(index=False)
R = f"""# The Run — Tougher Bosses ("you have to beat them")

*Simulator-only rule variants on the unmodified game code. {T.groupby(['skill','court','rule']).ngroups} conditions, {N} matched deals each. Listed Court policies keep a 10-gold reserve. Nothing has been changed in the game.*

## 1. Short answer

- **A strict gate ends almost every run.** If losing to any boss ends the run, completion falls to {pc(g('best','none','gate'))} with no purchases, {pc(g('best','defensive','gate'))} with the Defensive Court and {pc(g('best','aggressive','gate'))} with the Aggressive Court (best play).
- **Rematch-until-you-win is workable, but only for builds that help you go out.** With a 5-gold toll the Aggressive Court barely notices ({pc(g('best','aggressive','current'))} → {pc(g('best','aggressive','rematch5'))}), while the Defensive Court drops from {pc(g('best','defensive','current'))} to {pc(g('best','defensive','rematch5'))} and no-purchase play from {pc(g('best','none','current'))} to {pc(g('best','none','rematch5'))}.
- **The real price of a rematch is the bill, not the toll.** Even with no toll at all, no-purchase completion falls to {pc(g('best','none','rematch0'))}, because every lost attempt still costs the hand's points in gold.
- **The Miser becomes the wall.** Under the 5-gold rematch rule {pc(g('best','none','rematch5','ended_at_miser'))} of no-purchase runs and {pc(g('best','aggressive','rematch5','ended_at_miser'))} of Aggressive runs end at round 4 (now: {pc(g('best','none','current','ended_at_miser'))} and {pc(g('best','aggressive','current','ended_at_miser'))}), because players arrive there with little gold.
- **The Usurper needs softening under any "must beat" rule.** He takes {g('best','aggressive','rematch5','attempts_usurper'):.1f}–{g('best','defensive','rematch5','attempts_usurper'):.1f} attempts on average. If his dead Jokers applied to everyone, that drops to {g('best','aggressive','rematch5_sym','attempts_usurper'):.1f}–{g('best','defensive','rematch5_sym','attempts_usurper'):.1f}.
- **A toll set as a share of the treasury is the best gold sink.** At 25% per loss, completion is about the same as a flat 5–10 gold, but rich Aggressive runs finish with a median of {g('best','aggressive','rematch_pct25','median_final_treasury'):.0f} gold instead of {g('best','aggressive','rematch5','median_final_treasury'):.0f}.

## 2. Completion by rule

Best play. Figures in brackets are points versus current rules on the same deals (roughly ±4 points of noise).

{comp_table('best')}

A player who slips 20% of the time:

{comp_table('skill80')}

![](charts/e6_completion.png)

*"Softer Usurper" = his dead Jokers apply to every seat, not only the player.*

## 3. What the rematch rule does to a run (best play)

**Aggressive Court**

{detail('best','aggressive')}

**Defensive Court**

{detail('best','defensive')}

**No purchases**

{detail('best','none')}

![](charts/e6_attempts.png)

- **Run length.** Rematches add about {g('best','aggressive','rematch5','rounds_played')-g('best','aggressive','current','rounds_played'):.1f} rounds to an Aggressive run and {g('best','defensive','rematch5','rounds_played')-g('best','defensive','current','rounds_played'):.1f} to a Defensive one (5-gold toll).
- **Long tails.** {pc(g('best','defensive','rematch5','pct_runs_3plus_attempts'))} of Defensive runs need three or more attempts at some boss; the longest single boss fight in any condition was {int(T[T.rule.str.startswith('rematch')].max_attempts.max())} attempts (no-toll rule, weaker player).
- **Defensive builds lose their role.** Regalia that make leftovers cheaper (Starlight, Low Tide, Heavy Purse, Vault) lower the bill but do not help you score below the boss, so under a "must beat" rule they buy time, not wins.

## 4. The other two options

- **Tribute on a loss (10 / 15 / 20 gold):** {100*g('best','aggressive','tribute','diff_vs_current'):+.0f} points for Aggressive, {100*g('best','defensive','tribute','diff_vs_current'):+.0f} for Defensive, {100*g('best','none','tribute','diff_vs_current'):+.0f} for no purchases. Simple, but it hits poor runs hardest and rich runs not at all.
- **Boss takes your priciest Regalia:** the mildest option ({100*g('best','aggressive','steal','diff_vs_current'):+.0f} / {100*g('best','defensive','steal','diff_vs_current'):+.0f} / {100*g('best','none','steal','diff_vs_current'):+.0f} points). With no Regalia to take, the boss takes 10 gold.
- **Final-boss gate (rematch for the first two, one try at the Usurper):** {pc(g('best','none','finalgate'))} / {pc(g('best','defensive','finalgate'))} / {pc(g('best','aggressive','finalgate'))} completion; with the softer Usurper {pc(g('best','none','finalgate_sym'))} / {pc(g('best','defensive','finalgate_sym'))} / {pc(g('best','aggressive','finalgate_sym'))}. Still decided largely by one deal.

## 5. What I'd take from this

| Finding | Class | Option |
|---|---|---|
| Hard gates are too swingy for a single round of cards | Evidence-backed | Don't use a one-try gate, even for the final boss alone |
| Rematch works for go-out builds and crushes everything else | Evidence-backed | If you adopt it, expect the game to reward wild-rank Regalia even more than now |
| Round 4 becomes the wall under rematch | Evidence-backed | Exempt The Miser, give more gold before round 4, or cap the bill on a lost boss attempt |
| The bill on each lost attempt is the true cost | Evidence-backed | Consider a rematch where a lost attempt costs a fixed toll *instead of* the bill (not tested yet) |
| The Usurper takes 2–4 attempts | Evidence-backed | Soften him if he must be beaten (dead Jokers for everyone was the version tested) |
| A percentage toll drains rich runs while being about as hard on poor runs as a flat 10 gold | Evidence-backed (one setting) | Use it if the gold surplus matters to you |

## 6. Limits

- Same best-play AI and hand-written Court policies as before; the 20%-slip player is a stand-in, not measured human play.
- The AI plays a rematch exactly like any other round; a person might play a boss differently (holding cards to block, for example).
- A lost attempt keeps that round's income (tribute, Patron, Interest), as the current settlement code pays it. A real implementation might not.
- Pairing is exact for the first deal only; later deals can drift once purchases differ.

## 7. Validation

{chr(10).join(f"- {'PASS' if v['ok'] else 'FAIL'}: {v['name']}" + (f" ({v['detail']})" if v['detail'] else '') for v in V)}

Files: `e6_*_runs.csv`, `e6_*_rounds.csv`, `tables/e6_summary.csv`, `charts/`, `config_e6_*.json`. Reproduce: `node simulation/experiments.js e6 --skill best --tag e6_best --out <dir>` (and `skill80`), then `python3 simulation/analyze_e6.py <dir>` and `python3 simulation/make_report_e6.py <dir>`.
"""
open(f'{D}/boss_rules_report.md', 'w').write(R); print('written', len(R))
