# ARISS - Aggregate Real-Time Internet Sentiment Score

A comprehensive sentiment analysis system that tracks opinion across social media platforms (Reddit, YouTube, Twitter, etc.) and provides objective, weighted sentiment scores for any subject. 

![ARISS Dashboard](https://via.placeholder.com/800x400?text=ARISS+Dashboard)

## 🎯 Features

- **Multi-Platform Scraping**: Automatically collects comments from Reddit, YouTube, and Twitter
- **Advanced Sentiment Analysis**: Uses multiple NLP techniques including:
  - TextBlob for basic sentiment
  - VADER for social media-specific sentiment
  - Claude AI for nuanced, context-aware analysis
- **Bias Detection**: Identifies and weights down extremely biased or unreliable content
- **Source Credibility Weighting**: Adjusts scores based on platform credibility and engagement
- **Historical Tracking**: Stores scores over time to identify trends
- **Beautiful Web Interface**: Interactive Streamlit dashboard for exploring scores
- **Real-Time Updates**: Refresh scores on-demand to get latest sentiment

## 📊 ARISS Score Scale

- **0-30**: Very Negative - Strong disapproval/negative sentiment
- **30-45**: Negative - General disapproval with some nuance
- **45-55**: Neutral - Balanced or mixed opinions
- **55-70**: Positive - General approval with some criticism
- **70-100**: Very Positive - Strong approval/positive sentiment

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API keys for:
  - Anthropic (required)
  - Reddit (recommended)
  - YouTube (recommended)
  - Twitter (optional)

### Installation

1. **Clone or download the files**

2. **Install dependencies**:
```bash
pip install anthropic praw google-api-python-client tweepy beautifulsoup4 requests pandas numpy sqlalchemy streamlit plotly python-dotenv textblob vaderSentiment
```

3. **Set up API credentials**:
```bash
cp .env.template .env
# Edit .env and add your API keys
```

4. **Download NLTK data** (for TextBlob):
```python
python -c "import nltk; nltk.download('brown'); nltk.download('punkt')"
```

### Getting API Keys

#### Anthropic API (Required)
1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new key and copy it to your `.env` file

#### Reddit API (Recommended)
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" as the app type
4. Fill in name, description, and redirect URI (can be http://localhost)
5. Copy the client ID (under the app name) and secret to your `.env` file

#### YouTube API (Recommended)
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Copy the API key to your `.env` file

#### Twitter API (Optional)
1. Apply for developer account at https://developer.twitter.com/
2. Create a new app
3. Generate Bearer Token
4. Copy to your `.env` file

### Running the App

```bash
streamlit run ariss_app.py
```

The app will open in your browser at http://localhost:8501

## 📖 Usage Guide

### Calculating a New ARISS Score

1. Click **"New Subject"** in the sidebar
2. Enter the subject name (e.g., "Joe Biden", "Tesla", "iPhone 15")
3. Select a category
4. Click **"Calculate ARISS"**
5. Wait for the system to:
   - Scrape comments from social media
   - Analyze sentiment using multiple methods
   - Calculate weighted score
   - Store results in database

### Viewing Historical Data

1. Use **"Search Existing"** in the sidebar
2. Select a subject from the dropdown
3. Click **"View"**
4. Explore:
   - Current ARISS score with confidence metrics
   - Historical trend charts
   - Source distribution
   - Individual comment analysis
   - Sentiment distribution

### Refreshing Scores

Click the **"🔄 Refresh Score"** button to recalculate with latest data. This is useful for:
- Tracking changes after major events
- Building up historical data
- Getting more recent sentiment

## 🔬 How It Works

### 1. Data Collection
The system searches multiple platforms for mentions of the subject:
- **Reddit**: Searches subreddits for posts and comments
- **YouTube**: Finds relevant videos and extracts comments
- **Twitter**: Searches recent tweets

### 2. Sentiment Analysis
Each comment is analyzed using three methods:
- **TextBlob**: General-purpose sentiment (-1 to 1)
- **VADER**: Social media-optimized sentiment
- **Claude AI**: Context-aware, nuanced analysis with bias detection

### 3. Weighting & Scoring
Comments are weighted based on:
- **Source Credibility**: Platform reputation and engagement metrics
- **Bias Score**: Extreme/emotional language is down-weighted
- **Engagement**: Highly upvoted content gets more weight

### 4. Aggregation
The final ARISS score is calculated as:
```
ARISS = Σ(sentiment_i × credibility_i × (1 - bias_i) × engagement_i) / Σ(weights)
```

Converted to 0-100 scale where 50 is neutral.

### 5. Storage & Trending
All scores are stored with timestamps, allowing:
- Historical trend analysis
- Volatility measurement
- Change detection
- Comparative analysis

## 📂 Project Structure

```
ariss/
├── ariss_scorer.py       # Core scoring engine and scrapers
├── ariss_database.py     # SQLite database management
├── ariss_app.py          # Streamlit web interface
├── .env.template         # API credentials template
├── .env                  # Your actual credentials (git-ignored)
├── ariss_data.db         # SQLite database (auto-created)
└── README.md             # This file
```

## 🛠️ Advanced Usage

### Command-Line Scoring

You can use the scorer programmatically:

```python
from ariss_scorer import ARISSScorer, Comment
from datetime import datetime
import os

# Initialize
scorer = ARISSScorer(os.getenv("ANTHROPIC_API_KEY"))

# Create sample comment
comment = Comment(
    text="This policy is fantastic! Really helps everyone.",
    source="reddit",
    platform_id="abc123",
    timestamp=datetime.now(),
    author="user123",
    upvotes=50
)

# Analyze
result = scorer.analyze_comment(comment, "economic policy")
print(f"Sentiment: {result.claude_score}/100")
print(f"Bias: {result.bias_score}/100")
```

### Custom Scrapers

You can add your own data sources:

```python
from ariss_scorer import Comment

def scrape_custom_source(query):
    comments = []
    # Your scraping logic here
    comments.append(Comment(
        text="...",
        source="custom",
        platform_id="...",
        timestamp=datetime.now(),
        author="...",
        upvotes=0
    ))
    return comments
```

### Batch Analysis

```python
from ariss_scorer import ARISSScorer
from ariss_database import ARISSDatabase

scorer = ARISSScorer(api_key)
db = ARISSDatabase()

subjects = ["Bitcoin", "ChatGPT", "Climate Change"]

for subject in subjects:
    # Scrape and analyze (your logic)
    comments = get_comments(subject)
    
    sentiment_scores = [
        scorer.analyze_comment(c, subject) 
        for c in comments
    ]
    
    ariss_result = scorer.calculate_ariss(sentiment_scores)
    db.save_ariss_score(subject, ariss_result)
```

## 📊 Database Schema

### subjects
- `id`: Primary key
- `name`: Subject name (unique)
- `category`: Subject category
- `created_at`: First tracking date

### ariss_scores
- `id`: Primary key
- `subject_id`: Foreign key to subjects
- `score`: ARISS score (0-100)
- `confidence`: Confidence level (0-100)
- `sample_size`: Number of comments analyzed
- `mean_bias`: Average bias score
- `mean_credibility`: Average credibility
- `variance`: Score variance
- `timestamp`: Calculation time

### sentiment_scores
- `id`: Primary key
- `subject_id`: Foreign key to subjects
- `comment_id`: Unique comment identifier
- `text`: Comment text
- `source`: Platform (reddit/youtube/twitter)
- `*_score`: Various sentiment scores
- `timestamp`: Comment timestamp

## ⚠️ Limitations & Considerations

1. **API Rate Limits**: Social media APIs have rate limits. The system respects these but may need multiple runs for large datasets.

2. **Recency Bias**: Most APIs only return recent content (7-30 days). Historical sentiment requires continuous tracking.

3. **Platform Bias**: Different platforms have different user demographics. Results reflect active social media users, not general population.

4. **Sample Size**: Confidence increases with sample size. Minimum 50-100 comments recommended for reliable scores.

5. **Language**: Currently optimized for English. Non-English content may not be accurately analyzed.

6. **Context**: Sentiment analysis can miss sarcasm, irony, and cultural context. Claude helps but isn't perfect.

## 🔐 Privacy & Ethics

- **No Personal Data**: Only public comments are analyzed
- **Aggregated Results**: Individual opinions are aggregated, not exposed
- **Bias Transparency**: Bias scores are calculated and displayed
- **Source Attribution**: All data sources are credited

## 🤝 Contributing

Ideas for improvements:
- Add more social platforms (TikTok, Instagram, Facebook)
- Support for multiple languages
- Real-time streaming updates
- Sentiment forecasting using ML
- Comparative analysis tools
- Export to CSV/PDF
- API endpoints for integration

## 📝 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

- Anthropic Claude for advanced sentiment analysis
- VADER Sentiment for social media optimization
- TextBlob for baseline sentiment
- Reddit, YouTube, Twitter APIs for data access

## 📧 Support

For issues or questions, please check:
1. API credentials are correct in `.env`
2. All dependencies are installed
3. Internet connection is active
4. API rate limits haven't been exceeded

---

**Note**: This tool provides general sentiment analysis for research and informational purposes. It should not be used as the sole basis for important decisions. Always verify with multiple sources and consider professional advice when needed.
