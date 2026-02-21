# ARISS - Aggregate Real-time Internet Sentiment Score

Enterprise-grade sentiment analysis system that tracks public opinion across social media platforms in real-time using context-aware AI.

![ARISS Dashboard](https://via.placeholder.com/800x400?text=ARISS+Dashboard)

## 🎯 What is ARISS?

ARISS analyzes thousands of comments from Reddit, YouTube, and Twitter to provide real-time sentiment scores (0-100) for any subject. Unlike basic sentiment tools, ARISS uses **context-aware AI** to understand what events people are reacting to, making scores dramatically more accurate.

### Key Innovation: Context-Aware Analysis

**Example:**
- **Comment:** "Finally ditched it!"
- **Without context:** Unclear → scores ~50 (neutral)
- **With context** (iPhone 15 titanium design): Understands this is praise → scores 78 (positive)

This is the same methodology used by enterprise tools like Hootsuite ($249/mo) and Sprout Social ($399/mo).

---

## ✨ Features

- **Context-Aware AI**: Fetches recent news/events to properly interpret comments
- **Multi-Platform Scraping**: Reddit, YouTube, Twitter
- **Advanced NLP**: Handles sarcasm, slang, negations, comparisons
- **Named Entity Recognition**: Identifies brands, people, products mentioned
- **Aspect-Based Sentiment**: Tracks sentiment about specific features
- **Industry-Standard Formula**: Same aggregation method as Hootsuite/Sprout Social
- **Historical Tracking**: Monitor sentiment trends over time
- **Beautiful Dashboard**: Interactive Streamlit web interface
- **Real-Time Updates**: Refresh scores on-demand

---

## 📊 ARISS Score Scale

| Score | Sentiment | Description |
|-------|-----------|-------------|
| 70-100 | Very Positive | Strong approval, enthusiasm |
| 55-69 | Positive | General approval with some criticism |
| 45-54 | Neutral | Balanced or mixed opinions |
| 30-44 | Negative | General disapproval, criticism |
| 0-29 | Very Negative | Strong disapproval, condemnation |

**Note:** Scores reflect real internet sentiment including passionate reactions and strong opinions.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get API Keys

**Required:**
- **Anthropic API** - For Claude AI sentiment analysis
  - Get from: https://console.anthropic.com/
  - Cost: ~$0.005 per comment

**Optional (Recommended):**
- **Reddit API** - https://www.reddit.com/prefs/apps
- **YouTube API** - https://console.cloud.google.com/
- **Twitter API** - https://developer.twitter.com/

### 3. Configure
```bash
cp .env.template .env
# Edit .env and add your API keys
```

### 4. Run
```bash
# Quick demo
python demo_ariss.py

# Web app
streamlit run ariss_app.py
```

---

## 🔬 How It Works

### Step 1: Context Fetching
```python
context = "iPhone 15 recently launched with titanium design, 
          Action Button, priced $100 higher. Mixed reactions to price."
```

### Step 2: Context-Aware Sentiment Analysis
For each comment, Claude analyzes:
- **What event** is being discussed
- **Sarcasm detection** ("Great, another delay!" → negative)
- **Slang handling** ("This slaps" → positive)
- **Negations** ("Not bad" → mildly positive)
- **Comparisons** ("Better than iPhone 14" → contextual)
- **Emojis** (🔥 → positive, 🙄 → sarcasm)

### Step 3: Industry-Standard Aggregation
```python
# Classify comments
positive = count where score > 60
negative = count where score < 40
neutral = count where score 40-60

# Calculate net sentiment
net = (positive - negative) / total

# Convert to 0-100 scale
ARISS = (net + 1.0) × 50
```

This is exactly how Hootsuite and Sprout Social work.

---

## 📈 Example Output

```json
{
  "ariss_score": 68.5,
  "sentiment": "Positive",
  
  "distribution": {
    "positive": 65,
    "neutral": 13,
    "negative": 22
  },
  
  "sample_size": 100,
  "confidence": 82.3,
  
  "insights": {
    "top_context": "Price increase announcement",
    "sarcasm_detected": 12.0,
    "emotional_intensity": 68.4
  }
}
```

---

## 📂 Project Structure

```
ariss/
├── ariss_scorer.py       # Core sentiment engine (context-aware)
├── ariss_database.py     # SQLite storage
├── ariss_app.py          # Streamlit web dashboard
├── demo_ariss.py         # Quick demo script
├── setup.py              # Installation wizard
├── requirements.txt      # Dependencies
├── .env.template         # API key template
└── README.md             # This file
```

---

## 🎓 Advanced Usage

### Calculate Score Programmatically

```python
from ariss_scorer import ARISSScorer
from datetime import datetime
import os

# Initialize
scorer = ARISSScorer(os.getenv("ANTHROPIC_API_KEY"))

# Fetch context
context = scorer._get_current_context("Tesla")

# Analyze comments with context
results = []
for comment in comments:
    result = scorer.analyze_comment_with_context(
        comment, 
        subject="Tesla",
        context=context
    )
    results.append(result)

# Calculate ARISS
ariss = scorer.calculate_ariss(results)
print(f"ARISS Score: {ariss['ariss_score']:.1f}/100")
```

### Batch Analysis

```python
subjects = ["Bitcoin", "ChatGPT", "Climate Change"]

for subject in subjects:
    # Scrape comments (your logic)
    comments = get_comments(subject)
    
    # Get context
    context = scorer._get_current_context(subject)
    
    # Analyze
    results = [
        scorer.analyze_comment_with_context(c, subject, context)
        for c in comments
    ]
    
    # Calculate
    ariss = scorer.calculate_ariss(results)
    print(f"{subject}: {ariss['ariss_score']:.1f}")
```

---

## 🔧 Configuration

### .env File
```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
YOUTUBE_API_KEY=your_key_here
TWITTER_BEARER_TOKEN=your_token_here
```

### Adjusting Sample Size
In `ariss_app.py`, change the `limit` parameter:
```python
reddit_comments = scraper.search_comments(subject, limit=200)  # default: 100
youtube_comments = scraper.search_comments(subject, limit=100) # default: 50
```

---

## 📊 What Gets Analyzed

### Detected Patterns

✅ **Sarcasm**: "Great, another bug!" → negative
✅ **Slang**: "This slaps", "mid", "it's giving"
✅ **Negations**: "not bad", "can't complain"
✅ **Comparisons**: "better than X but..."
✅ **Emojis**: 🔥💯 (positive), 😡🙄 (negative)
✅ **Aspects**: "love camera, hate battery"

### Example Contexts Understood

- Product launches (iPhone 15 titanium design)
- Scandals (company controversy)
- Policy changes (new regulations)
- Price changes (subscription increase)
- Achievements (earnings beat, awards)
- Failures (recall, lawsuit, outage)

---

## ⚠️ Limitations

1. **Recent Events Only** - Context fetching works best for events within 2 weeks
2. **English Language** - Optimized for English comments
3. **API Costs** - ~$0.005 per comment (with context fetching)
4. **Sample Bias** - Reflects active commenters, not silent majority
5. **Platform Bias** - Reddit ≠ Twitter ≠ YouTube demographics

---

## 🆚 vs. Traditional Polling

| Feature | ARISS | Traditional Polls |
|---------|-------|-------------------|
| **Speed** | Real-time | Weeks |
| **Cost** | $5-20/calc | $1000s |
| **Sample** | Internet users | Representative |
| **Emotions** | Captures passion | Neutral questions |
| **Trends** | Track shifts | Point-in-time |
| **Bias** | Platform-dependent | Methodology-dependent |

**Best Use:** ARISS complements polling - use for real-time pulse, not replacement.

---

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
cp .env.template .env
# Edit .env and add your key
```

### "Reddit/YouTube/Twitter errors"
- Check API credentials in .env
- Verify API rate limits
- Try reducing `limit` parameter

### "Scores seem wrong"
- Verify subject spelling matches discussions
- Check sample size (need 50+ comments)
- Review "top_context" in results to see what AI understood
- Try refreshing score for more recent data

### "Database errors"
- Delete `ariss_data.db` and restart
- Update to latest `ariss_database.py`

---

## 📈 Performance Tips

### Speed Up
- Reduce sample size (`limit=50`)
- Use single platform (Reddit only)

### Reduce Costs
- Batch similar subjects together
- Cache context for 6 hours
- Use lower sample sizes

### Improve Accuracy
- Increase sample size (`limit=200`)
- Use all three platforms
- Refresh multiple times for trends

---

## 🔮 Future Roadmap

- [ ] Context caching (reduce API costs)
- [ ] Batch comment analysis
- [ ] Additional platforms (TikTok, Instagram)
- [ ] Export to CSV/PDF
- [ ] API endpoints
- [ ] Scheduled automated tracking
- [ ] Multi-language support
- [ ] Custom context injection

---

## 📝 License

This project is provided as-is for educational and research purposes.

## 🙏 Credits

- Anthropic Claude for context-aware AI analysis
- VADER Sentiment for social media optimization
- Methodology inspired by Hootsuite, Sprout Social, Talkwalker

---

## 📧 Support

**Getting Started:**
1. Run `python setup.py` for interactive setup
2. Try `python demo_ariss.py` to test
3. Launch `streamlit run ariss_app.py`

**Need Help?**
- Check this README
- Review error messages carefully
- Verify API keys in .env
- Try demo first to isolate issues

---

**ARISS - Know what the internet thinks, right now.**
