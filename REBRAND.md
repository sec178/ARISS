# ARISS Rebrand Summary

## Official Name Change

**Old:** Aggregate Representative Internet Sentiment Score
**New:** Aggregate Real-time Internet Sentiment Score

---

## Why the Change?

### "Representative" Was Misleading

The old name suggested we were creating a **representative sample** like traditional polling does — implying:
- Demographic weighting
- Filtered for quality/reliability
- Approximating general population opinion

But that's not what ARISS actually does.

### "Real-time" Is More Accurate

ARISS actually:
- Measures what's being said on the internet **right now**
- Includes passionate reactions, extreme viewpoints, and strong emotions
- Reflects online discourse as it actually is, not as a filtered proxy for general opinion
- Updates on-demand to capture current sentiment

---

## What Changed in the Code

### Files Updated:
- ✅ `ariss_scorer.py` - Header and docstring
- ✅ `ariss_database.py` - Header and docstring
- ✅ `ariss_app.py` - Header, subtitle, sidebar, landing page
- ✅ `demo_ariss.py` - Header and print statements
- ✅ `setup.py` - Header
- ✅ `.env.template` - Comment
- ✅ `README.md` - Title, description, features, how it works
- ✅ `CHANGELOG.md` - Version history and rebrand notes

### What Stayed the Same:
- Acronym: **ARISS** (still catchy, still memorable)
- File names: All files keep `ariss_` prefix
- Functionality: No breaking changes to the actual scoring system
- Database: Existing data remains compatible

---

## What ARISS Actually Measures

### ✅ ARISS Measures:
- Real-time internet sentiment
- What people are actively saying online right now
- Emotional intensity and passion
- The full spectrum of opinions (from rage to enthusiasm)
- Platform-specific discourse patterns
- Viral moments and trending reactions

### ❌ ARISS Does NOT Measure:
- Representative public opinion (that requires demographic sampling)
- Silent majority (only measures people who comment)
- Offline sentiment
- Future behavior (it's descriptive, not predictive)
- "Truth" or factual accuracy (just sentiment)

---

## How to Talk About ARISS

### Good Descriptions:
- "ARISS shows what the internet is saying right now"
- "Real-time pulse of online sentiment"
- "Track how people are reacting to events as they happen"
- "See how passionate/polarized online discourse is"
- "Monitor shifts in internet opinion over time"

### Avoid:
- "Representative sample of public opinion" ❌
- "What the country thinks" ❌
- "Accurate polling alternative" ❌
- "Unbiased measure of sentiment" ❌

### Instead Say:
- "What the internet thinks" ✅
- "Real-time internet sentiment" ✅
- "Online discourse tracker" ✅
- "Weighted measure of what people are saying online" ✅

---

## User-Facing Changes

### In the App:
1. **Subtitle now says:** "Aggregate Real-time Internet Sentiment Score"
2. **Landing page emphasizes:** Real-time tracking, what people are "actually saying"
3. **About section notes:** Scores weighted by length, credibility, and bias
4. **No claims of being "representative"**

### In Documentation:
1. **README is clear:** This measures internet sentiment, not general public opinion
2. **Note added:** Scores include passionate reactions and extreme viewpoints
3. **"Real-time" emphasized** throughout

---

## Benefits of the Rebrand

### 1. Honesty
We're now honest about what we measure — not overselling it as a polling replacement.

### 2. Sets Correct Expectations
Users understand they're seeing internet discourse, which is:
- More extreme than general opinion
- Dominated by people who feel strongly
- Platform-dependent (Twitter ≠ Reddit ≠ YouTube)

### 3. Highlights Real Value
The real value of ARISS is:
- **Speed**: Real-time, not weeks-old polling
- **Intensity**: Measures how passionate people are
- **Trends**: Track shifts in sentiment over time
- **Platform insights**: See where discourse is happening

### 4. Differentiates from Polling
ARISS is now positioned as complementary to polling, not replacement:
- Polls: "What does America think?" (representative sample)
- ARISS: "What's the internet saying?" (real-time discourse)

---

## Migration Notes

### For Existing Users:
- No action required
- Database files work as-is
- All existing ARISS scores remain valid
- Just a name/philosophy change

### For New Users:
- Updated README clarifies what ARISS measures
- Setup script uses new branding
- Landing page sets correct expectations

---

## Future Considerations

### Potential Additional Metrics:
Consider adding transparency metrics in the UI:
- **Platform breakdown**: "60% Reddit, 30% Twitter, 10% YouTube"
- **Polarization score**: "Highly polarized" vs "Consensus"
- **Sample demographics** (if available): "Mostly tech subreddits"
- **Comparison to polls** (if available): "ARISS: 42/100, Polls: 48% approval"

This helps users understand the limitations and context of ARISS scores.

---

## Summary

**ARISS = Aggregate Real-time Internet Sentiment Score**

A tool for tracking what the internet is saying right now about any topic, weighted for comment quality, source credibility, and bias. Not a replacement for representative polling, but a complement that shows real-time online discourse.

Honest. Fast. Transparent.
