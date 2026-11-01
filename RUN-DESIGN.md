# Kingsrun: The Run

A single-player roguelike mode for Kingsrun. The usual 11 rounds (3s wild up to Kings wild) become one **run**. Between rounds you shape your own rules by buying perks, and the run ends the moment your Treasury runs dry.

## Design goals

- **Turn luck into decisions.** A bad deal still hurts, but what decides a run is the string of choices: what to buy, when to save, and which strategy to build around.
- **Keep the card game intact.** Every round is still normal Kingsrun: draw, discard, group into books and runs, go out. The run only bends the rules around the edges.
- **Short and replayable.** A run takes about as long as a normal game (11 rounds), and every run plays out differently.
- **Readable at a glance.** Everything that changes the rules for you is visible on the table.

---

## 1. The Treasury (core loop)

Your gold is both your **health** and your **money**.

| Event | Gold |
|---|---|
| Start of run | **25** |
| End of each round: every point left in your hand | **−1 per point** (rounds 1–3: a bill is never more than 10) |
| You went out first | **+10** |
| Lowest score at the table that round (including going out) | **+4** |
| Royal tribute at the end of each round | **+3** |
| You beat a boss (scored fewer points than the boss) | **+12**, and your first pick in the next Court is free |

- If the Treasury can't cover the round's bill, you're **bankrupt** and the run ends.
- Survive round 11 (Kings wild) and you've **won the run**. Your score is the gold left in the Treasury.
- Every purchase makes you poorer, so each Court visit asks the same question: spend now to get stronger, or bank gold in case you get caught with a big hand?

Because of the Act 1 cap, nobody goes bankrupt in rounds 1–3 unless they overspend at the Court. The first real wall is the Miser in round 4.

## 2. Round structure

| Round | Wild | Cards | Table |
|---|---|---|---|
| 1–3 | 3s–5s | 3–5 | You + 2 **Squires** (make mistakes) |
| 4 | 6s | 6 | **Boss: The Miser** |
| 5–7 | 7s–9s | 7–9 | You + 2 **Knights** (rarely make mistakes) |
| 8 | 10s | 10 | **Boss: The Jester** |
| 9–10 | Js–Qs | 11–12 | You + 2 **Barons** (full strength) |
| 11 | Ks | 13 | **Final boss: The Usurper** |

After every round except the last, you visit **the Court** (the shop).

## 3. The Court (shop)

- Shows **3 offers** drawn from the pools below, usually 2 Regalia and 1 Decree.
- **Reroll** for 2 gold. Each further reroll in the same visit costs 1 more.
- You can hold up to **5 Regalia** and **3 Decrees**.
- The Court previews the next round: its wild rank, its hand size and, before a boss, the boss's rule.

## 4. Regalia (permanent perks)

Regalia last for the rest of the run. Prices come from simulation: each one's price is roughly a third to a half of the gold it saves or earns over rounds 4–11.

### Wild builds
| Regalia | Effect | Price | Worth over a run |
|---|---|---|---|
| Commoner's Crown | 3s are wild for you | 22 | ≈ 60 |
| Seventh Heaven | 7s are wild for you | 24 | ≈ 60 |
| Crown Jewels | Kings are wild for you | 24 | ≈ 60 |
| Court Fool | You're dealt an extra Joker every round (not against the Usurper) | 15 | ≈ 30 |
| Twin Crowns | Pairs of J, Q or K count as books for you | 16 | ≈ 33 |

### Suit and card builds
| Regalia | Effect | Price | Worth over a run |
|---|---|---|---|
| Starlight | ★ cards left in your hand cost nothing | 13 | ≈ 28 |
| Low Tide | 3s, 4s and 5s left in your hand cost nothing | 13 | ≈ 27 |
| Heavy Purse | J, Q and K left in your hand cost 5 each | 9 | ≈ 21 |
| Royal Mint | +1 gold for every ♦ in your groups at round end | 6 | ≈ 12 |

### Information
| Regalia | Effect | Price |
|---|---|---|
| Spyglass | You can always see the top card of the deck | 10 |
| Eavesdropper | See how many unmatched points each opponent holds | 5 |

### Tempo
| Regalia | Effect | Price |
|---|---|---|
| Herald | +5 extra gold whenever you go out first | 9 |
| Early Bird | Going out within your first 3 turns doubles your going-out gold | 6 |

### Greed
| Regalia | Effect | Price |
|---|---|---|
| Tax Collector | +1 gold for every 10 points your opponents are caught with | 9 |
| Interest | +1 gold for every 10 in your Treasury at round end (max +5) | 10 |
| Patron | +3 gold every round | 10 |

### Defence and risk
| Regalia | Effect | Price |
|---|---|---|
| Miser's Vault | A single round can never cost you more than 25 (≈ 25 saved per run, and it prevents busts) | 12 |
| Second Wind | Once per run, survive bankruptcy with 10 gold (then it's used up) | 9 |
| Gambler's Hand | Going-out gold is tripled, but points you're caught with cost 1.5× | 4 |

You can **sell** a Regalia at the Court for half its price, to make room or raise gold.

### Changes made during tuning
- *Twin Crowns* was "any books of 2". That cut bills by 80%, so it now covers only J, Q and K.
- *Low Tide* was cards 3–7, worth about 50 gold a run. It's now 3s–5s.
- *Jester's Favour* (wilds cost 5) saved almost nothing and was replaced by *Court Fool* (an extra Joker).
- *Starlight* at "half price" was too weak to notice, so ★ cards now cost nothing.
- *Tax Collector* at 1 gold per 5 points was worth about 40 gold a run, so it's now 1 per 10.
- Leftover cards that cost 0 no longer count as "going out". You still have to group every card.

## 5. Decrees (one-use cards)

You play a Decree from the Court panel during your turn.

| Decree | When | Effect | Price |
|---|---|---|---|
| Pickpocket | Before you draw | Take the second card down in the discard pile | 4 |
| Scout | Before you draw | See the top card of the deck | 3 |
| Redeal | Before you draw | Shuffle your hand into the deck and draw a fresh one | 5 |
| Fog | Any time on your turn | The next player can't take from the discard pile on their turn | 3 |
| Royal Pardon | Any time | This round, your highest-scoring leftover card is free | 4 |
| Insurance | Any time | This round's bill is halved | 5 |

## 6. Bosses

A boss takes one seat at the table. It plays at full strength and brings a rule twist that's shown on the table all round.

| Round | Boss | Twist |
|---|---|---|
| 4 (6s wild) | **The Miser** | Nobody may take from the discard pile |
| 8 (10s wild) | **The Jester** | The wild rank changes after every turn |
| 11 (Kings wild) | **The Usurper** | Jokers aren't wild for you: they're dead cards worth 50 |

Beating a boss means finishing the round with fewer points than it. The reward is **+12 gold**, and your first pick in the next Court is free.

## 7. Monarchs (later phase)

Each Monarch is a starting character with a twist, unlocked by winning runs:

- **The Merchant**: starts with 60 gold, but Court prices are +2.
- **The Scholar**: starts with Spyglass.
- **The Gambler**: starts with Gambler's Hand and 30 gold.
- **The Saint**: starts with Second Wind, but earns no royal tribute.

## 8. Progression (later phase)

- **Ascension levels**: each win unlocks a harder level with one more handicap (smaller tribute, pricier Court, a boss in round 6, and so on).
- **Unlocks**: new Regalia, Decrees and Monarchs, earned by milestones such as "win a run" or "go out in round 1 three times".
- **Daily Run**: the same seed (deals, Court offers, bosses) for everyone each day, with a shared leaderboard for family and friends.
- **Card upgrades** (Gilded = costs you 0, Crowned = wild for you, Twin-suited): change specific cards in the deck. Whoever draws an upgraded card gets it, but only you get the benefit.

## 9. Records

- Runs played, runs won, best final Treasury, and the furthest round reached.
- The Regalia you finished with in each of your recent runs, so you can see which builds work.

---

## Balance (measured)

300 complete runs were played inside the real game code by a full-strength bot that always makes the best discard:

| Strategy | Runs won | Where runs end |
|---|---|---|
| Never buys anything | 57% | Spread over rounds 4–11, most often at the Miser (4) and the Usurper (11) |
| Buys the priciest Regalia it can afford | 63% | Mostly early, from overspending. Few busts after round 6. Median final Treasury about 120 |

A human playing without hints will win less often. With good buying, the late game gets comfortable, which is where Ascension levels come in.

## MVP scope (built)

- [x] Treasury loop with tuned starting gold and income
- [x] Squires, Knights and Barons that get stronger each act
- [x] Three bosses: Miser, Jester, Usurper
- [x] The Court: 3 offers, rerolls and next-round preview
- [x] 19 Regalia (sellable) and 6 Decrees from the tables above
- [x] Run bar on the table (Treasury, Regalia, Decrees) and a Court panel during play
- [x] Run results, run-end screen and run records
- [ ] Monarchs, Ascension, unlocks, Daily Run and card upgrades (later phases)

## How the engine supports it

The engine's hand solver now takes either a plain wild rank (normal and online games, unchanged) or a **rules object** for one player. The rules object covers:

- which cards are wild for them
- what each leftover card costs them
- the smallest book size
- whether Jokers are wild

Each player at the table gets their own rules, so your Regalia change only how *your* hand is grouped and scored. Computer opponents use the same solver with their own rules, plus a skill level that sets how often they make the best play.
