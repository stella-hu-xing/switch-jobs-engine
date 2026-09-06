---
name: pitch-converter
description: >-
  Rewrites drafts into a more persuasive version using point-first structure
  (SCR or Pyramid) and a certainty pass. Use when the user asks to make text
  more persuasive, convert a pitch, tighten Slack/email/PR/status copy, or run
  pitch-converter.
---

# Pitch converter

Rewrite the user's draft into **one** more persuasive version. Persuasion is a finite set of patterns, not a personality trait. Pick **one** structure per rewrite. Do not stack SCR + Pyramid + all six Cialdini principles in one pass.

Do not lecture, dump checklists, or run pushback roleplay unless the user asks.

For framework cards and a worked example, see [reference.md](reference.md).

## Workflow

1. **Infer context** if missing: channel (Slack / email / PR / spoken), audience, desired action. Default to the same channel as the input. Ask only if the draft is unusable.

2. **Classify once** (then stop):
   - Problem to frame before an ask → **SCR** (Situation, Complication, Resolution).
   - Recommendation or explanation to land → **Pyramid** (answer first, then grouped support).
   - Do not use MEDDIC or Challenger in the default rewrite.

3. **Write the point first**, before anything else: `My point is ___.` Fill that blank. A channel-native version of that sentence becomes the **first sentence** of the rewrite.

4. **Build supporting reasoning after** the point. Break the default of context → evidence → reasoning → conclusion.

5. **Delivery pass** (sound certain, not "native"):
   - Cut qualifiers: "I think maybe," "it could possibly," "this might potentially," "up to around… in some cases."
   - State the claim; add nuance only if the user asked for caveats.
   - Split any sentence that would run out of breath when read aloud.

6. **Cialdini, silent:** after drafting, add **at most 1–2** signals that already fit (social proof, authority, a small next commitment). Do not force all six. Do not name Cialdini in the rewrite.

7. **Self-check:** if someone only heard the first sentence, would they know what to do or believe? If not, restructure before returning.

## Output

```markdown
## Rewrite
[Full rewritten message. First sentence is the point.]

## First-sentence check
- First sentence: "..."
- If someone only heard this, they would [do X / believe Y]. Pass / restructure note if it still fails.
```

No framework names, no hedge-audit, no alternative versions unless the user asks for another pass.
