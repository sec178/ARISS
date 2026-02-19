"""
ARISS - Aggregate Real-time Internet Sentiment Score
Core scoring engine with web scraping and sentiment analysis

Requirements:
pip install anthropic praw google-api-python-client tweepy beautifulsoup4
         requests pandas numpy python-dotenv textblob vaderSentiment
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

# Third-party imports
import anthropic
import pandas as pd
import numpy as np
from collections import Counter

# Social media APIs
try:
    import praw  # Reddit
except ImportError:
    praw = None

try:
    from googleapiclient.discovery import build  # YouTube
except ImportError:
    build = None

try:
    import tweepy  # Twitter/X
except ImportError:
    tweepy = None

# Sentiment analysis libraries
from textblob import TextBlob
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None


# ---------------------------------------------------------------------------
# Length weighting constants
# ---------------------------------------------------------------------------
MIN_MEANINGFUL_WORDS = 5    # below this = very low signal
MAX_MEANINGFUL_WORDS = 75   # above this = full weight


@dataclass
class Comment:
    """Represents a single comment from social media."""
    text: str
    source: str          # 'reddit', 'youtube', 'twitter', etc.
    platform_id: str     # unique ID from the platform
    timestamp: datetime
    author: str
    upvotes: int = 0
    subreddit: Optional[str] = None
    video_id: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class SentimentScore:
    """Represents sentiment analysis results for a comment."""
    comment_id: str
    text: str
    source: str
    timestamp: datetime

    # Sentiment scores (0-100 scale)
    textblob_score: float
    vader_score: float
    claude_score: float

    # Quality metrics
    bias_score: float           # 0-100, higher = more biased
    source_credibility: float   # 0-100, higher = more credible
    length_weight: float        # 0.1-1.0, higher = more substantive

    # Final weighted score
    weighted_score: float

    # Metadata
    upvotes: int
    author: str
    word_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_count(text: str) -> int:
    return len(text.split())


def _length_weight(text: str) -> float:
    """
    Map comment length to a [0.1, 1.0] weight using a log scale.

    Rationale: "lol", emoji-only, and one-sentence reactions are low-signal.
    A thoughtful 50-word comment carries much more information about true
    sentiment. Weights reach ~1.0 at MAX_MEANINGFUL_WORDS and can never
    drop below 0.1 so short comments still count a little.
    """
    wc = _word_count(text)
    if wc <= 0:
        return 0.0
    raw = np.log1p(wc) / np.log1p(MAX_MEANINGFUL_WORDS)
    return float(np.clip(raw, 0.1, 1.0))


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

class ARISSScorer:
    """Main class for calculating ARISS scores."""

    def __init__(self, anthropic_api_key: str):
        try:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        except TypeError:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_api_key
            self.client = anthropic.Anthropic()
        self.vader = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else None

    # ------------------------------------------------------------------
    # Three independent sentiment analysers (each returns 0-100)
    # ------------------------------------------------------------------

    def analyze_sentiment_textblob(self, text: str) -> float:
        blob = TextBlob(text)
        return float((blob.sentiment.polarity + 1) * 50)

    def analyze_sentiment_vader(self, text: str) -> float:
        if not self.vader:
            return 50.0
        compound = self.vader.polarity_scores(text)['compound']
        return float((compound + 1) * 50)

    def analyze_sentiment_claude(self, text: str, subject: str) -> Tuple[float, float]:
        """
        Calibrated sentiment + bias analysis via Claude.

        Key design decisions:
        - temperature=0.1 for consistent, non-creative scoring
        - Explicit calibration guide prevents drift toward neutral/positive
        - 'word_sentiment_check' forces the model to surface specific
          sentiment-bearing tokens before committing to a number — reduces
          anchoring bias
        - Hard clamp to [0, 100] as a safety net
        """
        prompt = f"""You are a calibrated sentiment analyst. Score this internet comment about "{subject}" objectively.

Comment:
\"\"\"{text}\"\"\"

Rules:
- Do NOT default to 50 (neutral) for ambiguous or mild comments.
- Negative criticism and complaints should score well BELOW 50.
- Positive praise and enthusiasm should score well ABOVE 50.
- Only score near 50 if the comment is genuinely mixed or neutral.
- Strong emotions in either direction are valid signals — preserve them.

Return ONLY this JSON object:

{{
  "word_sentiment_check": "<the 3 most sentiment-bearing words/phrases and whether each is positive or negative>",
  "reasoning": "<one sentence>",
  "sentiment": <integer 0-100>,
  "bias_score": <integer 0-100>
}}

Sentiment scale:
  0-20  : Extremely negative (rage, strong condemnation)
  21-35 : Clearly negative (criticism, disappointment)
  36-45 : Mildly negative (skepticism, mild complaint)
  46-54 : Genuinely neutral or evenly mixed
  55-64 : Mildly positive (cautious optimism, tentative approval)
  65-79 : Clearly positive (praise, approval)
  80-100: Extremely positive (enthusiasm, strong endorsement)

Bias scale:
  0-30  : Objective, factual, balanced
  31-60 : Opinion-based, some emotional language
  61-100: Extreme, conspiratorial, purely emotional/reactionary

Return ONLY valid JSON:"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                sentiment = float(result.get('sentiment', 50))
                bias      = float(result.get('bias_score', 50))
                return float(np.clip(sentiment, 0, 100)), float(np.clip(bias, 0, 100))
        except Exception as e:
            print(f"Claude analysis error: {e}")

        return self.analyze_sentiment_textblob(text), 50.0

    # ------------------------------------------------------------------
    # Source credibility
    # ------------------------------------------------------------------

    def calculate_source_credibility(self, comment: Comment) -> float:
        """
        Platform base score adjusted by community engagement.

        Changes from v1:
        - Upvote boost capped at +10 (was +15) — high upvotes ≠ objectivity
        - Downvoted content gets a credibility *reduction*, not just ignored
        """
        platform_credibility = {
            'reddit': 65,
            'youtube': 55,
            'twitter': 58,
            'news_comments': 70,
            'unknown': 50,
        }
        base = float(platform_credibility.get(comment.source, 50))

        upvotes = comment.upvotes or 0
        if upvotes > 0:
            base += min(10.0, np.log1p(upvotes) * 1.5)
        elif upvotes < -2:
            base += max(-20.0, np.log1p(abs(upvotes)) * -2.0)

        return float(np.clip(base, 5, 100))

    # ------------------------------------------------------------------
    # Per-comment analysis
    # ------------------------------------------------------------------

    def analyze_comment(self, comment: Comment, subject: str) -> SentimentScore:
        """
        Comprehensive per-comment analysis.

        Ensemble weights:
          Claude   60%  — best at contextual/sarcastic language
          VADER    25%  — tuned for social-media slang and punctuation
          TextBlob 15%  — general baseline

        The weighted_score stored here is the raw ensemble sentiment.
        Credibility, bias, and length weights are stored separately and
        applied at aggregation time — this makes it easy to audit.
        """
        textblob_score              = self.analyze_sentiment_textblob(comment.text)
        vader_score                 = self.analyze_sentiment_vader(comment.text)
        claude_score, bias_score    = self.analyze_sentiment_claude(comment.text, subject)
        source_credibility          = self.calculate_source_credibility(comment)
        lw                          = _length_weight(comment.text)
        wc                          = _word_count(comment.text)

        # Ensemble (no regression-to-50 anchor)
        ensemble = claude_score * 0.60 + vader_score * 0.25 + textblob_score * 0.15

        comment_id = hashlib.md5(
            f"{comment.source}:{comment.platform_id}".encode()
        ).hexdigest()

        return SentimentScore(
            comment_id=comment_id,
            text=comment.text,
            source=comment.source,
            timestamp=comment.timestamp,
            textblob_score=textblob_score,
            vader_score=vader_score,
            claude_score=claude_score,
            bias_score=bias_score,
            source_credibility=source_credibility,
            length_weight=lw,
            weighted_score=ensemble,
            upvotes=comment.upvotes,
            author=comment.author,
            word_count=wc,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def calculate_ariss(self, sentiment_scores: List[SentimentScore]) -> Dict[str, Any]:
        """
        Aggregate individual scores into a final ARISS score.

        Per-comment weight = length_weight * credibility_weight * (1 - bias_fraction)

        No regression-to-50. The weighted mean of the ensemble scores IS
        the final score — if opinions are genuinely negative, ARISS is low.
        """
        if not sentiment_scores:
            return {
                'ariss_score': 50.0,
                'confidence': 0.0,
                'sample_size': 0,
                'error': 'No data available',
            }

        raw_scores = [s.weighted_score for s in sentiment_scores]
        weights    = []

        for s in sentiment_scores:
            cred_w = s.source_credibility / 100.0   # 0.05 – 1.0
            bias_w = 1.0 - (s.bias_score / 100.0)   # 0.0  – 1.0
            len_w  = s.length_weight                 # 0.1  – 1.0
            # Floor at 0.01 so no comment is completely silenced
            weights.append(max(0.01, cred_w * bias_w * len_w))

        total_w      = sum(weights)
        norm_weights = [w / total_w for w in weights]
        ariss_score  = float(np.dot(raw_scores, norm_weights))

        variance   = float(np.var(raw_scores))
        n          = len(raw_scores)
        size_conf  = min(100.0, n * 2.0)
        var_conf   = max(0.0, 100.0 - variance)
        confidence = (size_conf + var_conf) / 2.0

        return {
            'ariss_score':        round(ariss_score, 2),
            'confidence':         round(confidence, 2),
            'sample_size':        n,
            'mean_bias':          round(float(np.mean([s.bias_score for s in sentiment_scores])), 2),
            'mean_credibility':   round(float(np.mean([s.source_credibility for s in sentiment_scores])), 2),
            'mean_length_weight': round(float(np.mean([s.length_weight for s in sentiment_scores])), 3),
            'mean_word_count':    round(float(np.mean([s.word_count for s in sentiment_scores])), 1),
            'variance':           round(variance, 2),
            'std_dev':            round(float(np.std(raw_scores)), 2),
            'min_score':          round(min(raw_scores), 2),
            'max_score':          round(max(raw_scores), 2),
            'timestamp':          datetime.now().isoformat(),
            'source_breakdown':   dict(Counter([s.source for s in sentiment_scores])),
        }


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

class RedditScraper:
    """Scraper for Reddit comments and posts."""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        if not praw:
            raise ImportError("praw not installed: pip install praw")
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    def search_comments(
        self,
        query: str,
        limit: int = 100,
        time_filter: str = 'month',
    ) -> List[Comment]:
        """
        Search Reddit for comments about a subject.

        v2 design choices:
        - Searches with BOTH 'relevance' and 'new' sort — relevance skews
          toward highly-upvoted (popular = positive) posts; 'new' gives
          more recent, unfiltered opinion.
        - Collects top-level AND second-level replies (3 per parent) for
          diversity within each thread.
        - No body-text keyword filter (the old filter biased toward posts
          where the subject is mentioned admiringly by name).
        - Skips deleted/removed/very short comments (< 3 words).
        - time_filter default = 'month' (broader than 'week').
        """
        comments: List[Comment] = []
        seen_ids: set = set()
        per_page = max(5, limit // 10)

        try:
            subreddit = self.reddit.subreddit('all')

            for sort_method in ['relevance', 'new']:
                if len(comments) >= limit:
                    break

                for submission in subreddit.search(
                    query,
                    sort=sort_method,
                    time_filter=time_filter,
                    limit=per_page,
                ):
                    if len(comments) >= limit:
                        break

                    submission.comments.replace_more(limit=0)
                    pool = list(submission.comments)
                    for top in list(submission.comments):
                        pool.extend(list(top.replies)[:3])

                    for comment in pool:
                        if len(comments) >= limit:
                            break
                        if not hasattr(comment, 'body'):
                            continue
                        if comment.id in seen_ids:
                            continue
                        body = comment.body.strip()
                        if body in ('[deleted]', '[removed]', '') or len(body.split()) < 3:
                            continue

                        seen_ids.add(comment.id)
                        comments.append(Comment(
                            text=body,
                            source='reddit',
                            platform_id=comment.id,
                            timestamp=datetime.fromtimestamp(comment.created_utc),
                            author=str(comment.author) if comment.author else '[deleted]',
                            upvotes=comment.score,
                            subreddit=submission.subreddit.display_name,
                        ))

        except Exception as e:
            print(f"Reddit scraping error: {e}")

        return comments[:limit]


class YouTubeScraper:
    """Scraper for YouTube comments."""

    def __init__(self, api_key: str):
        if not build:
            raise ImportError("google-api-python-client not installed")
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def search_comments(self, query: str, limit: int = 100) -> List[Comment]:
        """
        Search YouTube for comments.

        v2 design choices:
        - Fetches from more videos (15) for source diversity.
        - Pulls both 'relevance' and 'time' ordered comments per video.
        - Skips comments < 4 words.
        """
        comments: List[Comment] = []
        seen_ids: set = set()

        try:
            search_resp = self.youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=15,
                type='video',
                order='relevance',
            ).execute()

            n_videos  = max(1, len(search_resp.get('items', [])))
            per_video = max(5, limit // n_videos)

            for item in search_resp.get('items', []):
                if len(comments) >= limit:
                    break
                video_id = item['id']['videoId']

                for order in ['relevance', 'time']:
                    if len(comments) >= limit:
                        break
                    try:
                        resp = self.youtube.commentThreads().list(
                            part='snippet',
                            videoId=video_id,
                            maxResults=min(per_video, 50),
                            order=order,
                        ).execute()

                        for ci in resp.get('items', []):
                            if len(comments) >= limit:
                                break
                            if ci['id'] in seen_ids:
                                continue
                            data = ci['snippet']['topLevelComment']['snippet']
                            text = data['textDisplay'].strip()
                            if len(text.split()) < 4:
                                continue
                            seen_ids.add(ci['id'])
                            comments.append(Comment(
                                text=text,
                                source='youtube',
                                platform_id=ci['id'],
                                timestamp=datetime.fromisoformat(
                                    data['publishedAt'].replace('Z', '+00:00')
                                ),
                                author=data['authorDisplayName'],
                                upvotes=data['likeCount'],
                                video_id=video_id,
                            ))
                    except Exception as e:
                        print(f"YouTube comment error (video {video_id}): {e}")

        except Exception as e:
            print(f"YouTube scraping error: {e}")

        return comments[:limit]


class TwitterScraper:
    """Scraper for Twitter/X posts."""

    def __init__(self, bearer_token: str):
        if not tweepy:
            raise ImportError("tweepy not installed")
        self.client = tweepy.Client(bearer_token=bearer_token)

    def search_tweets(self, query: str, limit: int = 100) -> List[Comment]:
        """
        Search Twitter for tweets.

        v2 changes:
        - Excludes retweets — they inflate counts with no new sentiment.
        - Excludes replies (off-topic threads).
        - English-only filter for consistent NLP.
        - Skips tweets < 5 words.
        """
        comments: List[Comment] = []
        clean_query = f"{query} -is:retweet -is:reply lang:en"

        try:
            tweets = self.client.search_recent_tweets(
                query=clean_query,
                max_results=min(100, limit),
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
            )
            if tweets.data:
                for tweet in tweets.data:
                    text = tweet.text.strip()
                    if len(text.split()) < 5:
                        continue
                    comments.append(Comment(
                        text=text,
                        source='twitter',
                        platform_id=str(tweet.id),
                        timestamp=tweet.created_at,
                        author=str(tweet.author_id),
                        upvotes=tweet.public_metrics['like_count'],
                    ))
        except Exception as e:
            print(f"Twitter scraping error: {e}")

        return comments[:limit]


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    scorer  = ARISSScorer(api_key)

    samples = [
        Comment("This policy is an absolute disaster. Worst decision in years.",
                "reddit", "s1", datetime.now(), "u1", upvotes=312),
        Comment("Mixed results so far. Some good points but the implementation seems rushed.",
                "reddit", "s2", datetime.now(), "u2", upvotes=89),
        Comment("👍", "youtube", "y1", datetime.now(), "u3", upvotes=5),
        Comment("Genuinely impressed. Strong leadership.",
                "reddit", "s3", datetime.now(), "u4", upvotes=44),
        Comment("I read the full 40-page report. The data clearly shows a 12% improvement in "
                "outcomes with no meaningful rise in costs. Cautiously optimistic but want to "
                "see 6-month follow-up before calling it a success.",
                "reddit", "s4", datetime.now(), "u5", upvotes=901),
    ]

    print(f"\n{'='*70}")
    print(f"{'Comment':<45} {'Words':>5} {'LenW':>5} {'Score':>6} {'Bias':>5}")
    print(f"{'='*70}")

    scores = []
    for c in samples:
        sc = scorer.analyze_comment(c, "the policy")
        scores.append(sc)
        preview = c.text[:44]
        print(f"{preview:<45} {sc.word_count:>5} {sc.length_weight:>5.2f} "
              f"{sc.claude_score:>6.1f} {sc.bias_score:>5.1f}")

    result = scorer.calculate_ariss(scores)
    print(f"\nARISS SCORE : {result['ariss_score']:.1f}/100")
    print(f"Confidence  : {result['confidence']:.1f}%")
    print(f"Mean words  : {result['mean_word_count']:.1f}")
    print(f"Mean len_w  : {result['mean_length_weight']:.3f}")
    print(f"{'='*70}\n")
