"""
ARISS v3 - Aggregate Real-time Internet Sentiment Score
Enterprise-grade sentiment analysis with context awareness

Based on methodologies from Hootsuite, Sprout Social, and Talkwalker

Key improvements:
- Context-aware sentiment (understands what event/topic comment refers to)
- Named Entity Recognition (identifies brands, people, products mentioned)
- Aspect-based sentiment (sentiment about specific aspects)  
- Advanced NLP (handles sarcasm, slang, emojis, negations, comparisons)
- Calibrated scoring (no regression to neutral)
- Simplified aggregation formula (industry standard)
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

import anthropic
import pandas as pd
import numpy as np
from collections import Counter
from textblob import TextBlob

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    SentimentIntensityAnalyzer = None

try:
    import praw
except ImportError:
    praw = None

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

try:
    import tweepy
except ImportError:
    tweepy = None


@dataclass
class Comment:
    """Single social media comment."""
    text: str
    source: str
    platform_id: str
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
class SentimentResult:
    """Results from context-aware sentiment analysis."""
    comment_id: str
    text: str
    source: str
    timestamp: datetime
    
    # Core sentiment (polarity: -1 to +1, scaled to 0-100)
    sentiment_score: float  # 0=very negative, 50=neutral, 100=very positive
    
    # Context understanding
    understood_context: str  # What event/topic this refers to
    primary_entity: str      # Main subject (person, brand, product)
    aspects_mentioned: List[str]  # Specific aspects discussed
    
    # Quality indicators
    has_sarcasm: bool
    has_comparison: bool
    emotional_intensity: float  # 0-100, how strong the emotion is
    
    # Metadata
    upvotes: int
    author: str
    word_count: int


class ARISSScorer:
    """
    Enterprise-grade sentiment scorer.
    
    Uses Claude for context-aware analysis similar to Hootsuite/Sprout Social.
    """
    
    def __init__(self, anthropic_api_key: str):
        try:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        except TypeError:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_api_key
            self.client = anthropic.Anthropic()
        
        self.vader = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else None
    
    def _get_current_context(self, subject: str) -> str:
        """
        Fetch recent news/context about the subject.
        
        This helps the sentiment analyzer understand what events people
        are reacting to (critical for accuracy).
        """
        prompt = f"""What are the most significant recent events, news, or developments related to "{subject}" in the past 2 weeks?

Provide a brief 2-3 sentence summary of the TOP event or topic people are likely discussing.

Focus on:
- Breaking news
- Major announcements  
- Controversies or crises
- Product launches
- Policy changes
- Significant achievements or failures

Return ONLY the summary, no preamble."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            print(f"Context fetch error: {e}")
            return f"General discussion about {subject}"
    
    def analyze_comment_with_context(
        self, 
        comment: Comment, 
        subject: str,
        context: str
    ) -> SentimentResult:
        """
        Perform context-aware sentiment analysis on a comment.
        
        This is the KEY INNOVATION: we tell Claude what's happening,
        so it can properly interpret comments.
        
        Example:
        - Context: "iPhone 15 just launched with new titanium design"
        - Comment: "Finally ditched the stainless steel!"
        - Without context: Neutral (50)
        - With context: Positive (72) - understands this is praise
        """
        
        prompt = f"""You are analyzing a social media comment about "{subject}".

**CURRENT CONTEXT:**
{context}

**COMMENT:**
\"\"\"{comment.text}\"\"\"

**SOURCE:** {comment.source} | **ENGAGEMENT:** {comment.upvotes} upvotes

---

Analyze this comment using the context above. Return ONLY this JSON:

{{
  "sentiment_polarity": <-1.0 to +1.0, where -1=extremely negative, 0=neutral, +1=extremely positive>,
  "confidence": <0-100, how confident you are in this score>,
  "understood_context": "<brief: what event/topic is this comment about?>",
  "primary_entity": "<the main person/brand/product mentioned>",
  "aspects_mentioned": ["<aspect 1>", "<aspect 2>"],
  "has_sarcasm": <true/false>,
  "has_comparison": <true/false>,
  "emotional_intensity": <0-100, how emotionally charged is this?>,
  "reasoning": "<one sentence explaining the sentiment>"
}}

**CRITICAL SCORING RULES:**
1. Use the full -1 to +1 range. Don't cluster around 0.
2. "I love this!" should be +0.8 or higher
3. "This is terrible" should be -0.8 or lower  
4. Mild opinions should be ±0.3 to ±0.6
5. Only score near 0 if genuinely neutral or balanced
6. Consider context - a comment about a scandal is different from a product review
7. Detect sarcasm: "Great, another bug" is negative even with "great"
8. Handle slang: "This slaps" = positive, "mid" = neutral/negative
9. Respect negations: "not bad" is mildly positive
10. Emojis matter: 😡 = negative, 🔥 = positive

Return ONLY valid JSON:"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0.05,  # Very low for consistency
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
                
                # Extract values
                polarity = float(result.get('sentiment_polarity', 0))
                polarity = np.clip(polarity, -1.0, 1.0)
                
                # Convert polarity (-1 to +1) to score (0 to 100)
                # This is the industry standard formula
                sentiment_score = (polarity + 1.0) * 50.0
                
                comment_id = hashlib.md5(
                    f"{comment.source}:{comment.platform_id}".encode()
                ).hexdigest()
                
                return SentimentResult(
                    comment_id=comment_id,
                    text=comment.text,
                    source=comment.source,
                    timestamp=comment.timestamp,
                    sentiment_score=sentiment_score,
                    understood_context=result.get('understood_context', 'Unknown'),
                    primary_entity=result.get('primary_entity', subject),
                    aspects_mentioned=result.get('aspects_mentioned', []),
                    has_sarcasm=result.get('has_sarcasm', False),
                    has_comparison=result.get('has_comparison', False),
                    emotional_intensity=float(result.get('emotional_intensity', 50)),
                    upvotes=comment.upvotes,
                    author=comment.author,
                    word_count=len(comment.text.split()),
                )
        
        except Exception as e:
            print(f"Analysis error: {e}")
        
        # Fallback: use VADER if available
        if self.vader:
            vader_result = self.vader.polarity_scores(comment.text)
            polarity = vader_result['compound']
            sentiment_score = (polarity + 1.0) * 50.0
        else:
            sentiment_score = 50.0
        
        comment_id = hashlib.md5(
            f"{comment.source}:{comment.platform_id}".encode()
        ).hexdigest()
        
        return SentimentResult(
            comment_id=comment_id,
            text=comment.text,
            source=comment.source,
            timestamp=comment.timestamp,
            sentiment_score=sentiment_score,
            understood_context="Fallback analysis",
            primary_entity=subject,
            aspects_mentioned=[],
            has_sarcasm=False,
            has_comparison=False,
            emotional_intensity=50.0,
            upvotes=comment.upvotes,
            author=comment.author,
            word_count=len(comment.text.split()),
        )
    
    def calculate_ariss(self, sentiment_results: List[SentimentResult]) -> Dict[str, Any]:
        """
        Calculate final ARISS score using industry-standard formula.
        
        Formula (from Sprout Social / Hootsuite):
        ARISS = (Positive - Negative) / Total
        
        Where:
        - Positive = comments with score > 60
        - Negative = comments with score < 40
        - Neutral = 40-60
        
        Then scale to 0-100.
        """
        if not sentiment_results:
            return {
                'ariss_score': 50.0,
                'confidence': 0.0,
                'sample_size': 0,
                'error': 'No data',
            }
        
        # Classify comments
        positive = [r for r in sentiment_results if r.sentiment_score > 60]
        negative = [r for r in sentiment_results if r.sentiment_score < 40]
        neutral  = [r for r in sentiment_results if 40 <= r.sentiment_score <= 60]
        
        n_pos = len(positive)
        n_neg = len(negative)
        n_neu = len(neutral)
        total = len(sentiment_results)
        
        # Industry standard: Net sentiment
        # Range: -1 (all negative) to +1 (all positive)
        if total > 0:
            net_sentiment = (n_pos - n_neg) / total
        else:
            net_sentiment = 0.0
        
        # Convert to 0-100 scale
        # -1 → 0, 0 → 50, +1 → 100
        ariss_score = (net_sentiment + 1.0) * 50.0
        
        # Confidence based on sample size and agreement
        variance = float(np.var([r.sentiment_score for r in sentiment_results]))
        size_conf = min(100.0, total * 2.0)  # Full confidence at 50+ samples
        var_conf  = max(0.0, 100.0 - variance)
        confidence = (size_conf + var_conf) / 2.0
        
        # Context breakdown
        contexts = Counter([r.understood_context for r in sentiment_results])
        entities = Counter([r.primary_entity for r in sentiment_results])
        
        return {
            'ariss_score': round(ariss_score, 2),
            'net_sentiment': round(net_sentiment, 3),
            'confidence': round(confidence, 2),
            
            # Distribution
            'positive_count': n_pos,
            'negative_count': n_neg,
            'neutral_count': n_neu,
            'positive_pct': round(n_pos / total * 100, 1),
            'negative_pct': round(n_neg / total * 100, 1),
            'neutral_pct': round(n_neu / total * 100, 1),
            
            # Sample stats
            'sample_size': total,
            'mean_score': round(float(np.mean([r.sentiment_score for r in sentiment_results])), 2),
            'median_score': round(float(np.median([r.sentiment_score for r in sentiment_results])), 2),
            'std_dev': round(float(np.std([r.sentiment_score for r in sentiment_results])), 2),
            
            # Context insights
            'top_contexts': dict(contexts.most_common(3)),
            'top_entities': dict(entities.most_common(3)),
            'sarcasm_pct': round(sum(r.has_sarcasm for r in sentiment_results) / total * 100, 1),
            'mean_emotional_intensity': round(float(np.mean([r.emotional_intensity for r in sentiment_results])), 1),
            
            # Metadata
            'timestamp': datetime.now().isoformat(),
            'source_breakdown': dict(Counter([r.source for r in sentiment_results])),
        }


# Scrapers (same as v2, optimized for diversity)
class RedditScraper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        if not praw:
            raise ImportError("praw not installed")
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
                    for c in pool:
                        if len(comments) >= limit:
                            break
                        if not hasattr(c, 'body') or c.id in seen_ids:
                            continue
                        body = c.body.strip()
                        if body in ('[deleted]', '[removed]', '') or len(body.split()) < 3:
                            continue
                        seen_ids.add(c.id)
                        comments.append(Comment(
                            text=body,
                            source='reddit',
                            platform_id=c.id,
                            timestamp=datetime.fromtimestamp(c.created_utc),
                            author=str(c.author) if c.author else '[deleted]',
                            upvotes=c.score,
                            subreddit=submission.subreddit.display_name,
                        ))
        except Exception as e:
            print(f"Reddit error: {e}")
        return comments[:limit]


class YouTubeScraper:
    def __init__(self, api_key: str):
        if not build:
            raise ImportError("google-api-python-client not installed")
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def search_comments(self, query: str, limit: int = 100) -> List[Comment]:
        comments: List[Comment] = []
        seen_ids: set = set()
        try:
            search_resp = self.youtube.search().list(
                q=query, part='id,snippet', maxResults=15, type='video', order='relevance'
            ).execute()
            n_videos = max(1, len(search_resp.get('items', [])))
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
                            part='snippet', videoId=video_id, maxResults=min(per_video, 50), order=order
                        ).execute()
                        for ci in resp.get('items', []):
                            if len(comments) >= limit or ci['id'] in seen_ids:
                                break
                            data = ci['snippet']['topLevelComment']['snippet']
                            text = data['textDisplay'].strip()
                            if len(text.split()) < 4:
                                continue
                            seen_ids.add(ci['id'])
                            comments.append(Comment(
                                text=text, source='youtube', platform_id=ci['id'],
                                timestamp=datetime.fromisoformat(data['publishedAt'].replace('Z', '+00:00')),
                                author=data['authorDisplayName'], upvotes=data['likeCount'], video_id=video_id,
                            ))
                    except Exception as e:
                        print(f"YouTube error (video {video_id}): {e}")
        except Exception as e:
            print(f"YouTube error: {e}")
        return comments[:limit]


class TwitterScraper:
    def __init__(self, bearer_token: str):
        if not tweepy:
            raise ImportError("tweepy not installed")
        self.client = tweepy.Client(bearer_token=bearer_token)
    
    def search_tweets(self, query: str, limit: int = 100) -> List[Comment]:
        comments: List[Comment] = []
        clean_query = f"{query} -is:retweet -is:reply lang:en"
        try:
            tweets = self.client.search_recent_tweets(
                query=clean_query, max_results=min(100, limit),
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
            )
            if tweets.data:
                for tweet in tweets.data:
                    text = tweet.text.strip()
                    if len(text.split()) < 5:
                        continue
                    comments.append(Comment(
                        text=text, source='twitter', platform_id=str(tweet.id),
                        timestamp=tweet.created_at, author=str(tweet.author_id),
                        upvotes=tweet.public_metrics['like_count'],
                    ))
        except Exception as e:
            print(f"Twitter error: {e}")
        return comments[:limit]


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    scorer  = ARISSScorer(api_key)
    
    subject = "iPhone 15"
    context = scorer._get_current_context(subject)
    
    print(f"\n{'='*70}")
    print(f"ARISS v3 - Context-Aware Sentiment Analysis")
    print(f"{'='*70}")
    print(f"\nSubject: {subject}")
    print(f"Context: {context}\n")
    
    samples = [
        Comment("This is a complete disaster. Worst decision ever.", "reddit", "1", datetime.now(), "u1", 50),
        Comment("Finally ditched the stainless steel! Love the titanium.", "reddit", "2", datetime.now(), "u2", 200),
        Comment("Great, another price hike 🙄", "twitter", "3", datetime.now(), "u3", 10),
        Comment("The camera is incredible but battery life is mid tbh", "reddit", "4", datetime.now(), "u4", 80),
    ]
    
    results = []
    for c in samples:
        r = scorer.analyze_comment_with_context(c, subject, context)
        results.append(r)
        print(f"[{r.sentiment_score:5.1f}] {c.text[:60]}")
        print(f"         Context: {r.understood_context}")
        print(f"         Sarcasm: {r.has_sarcasm} | Intensity: {r.emotional_intensity:.0f}\n")
    
    ariss = scorer.calculate_ariss(results)
    print(f"{'='*70}")
    print(f"ARISS SCORE: {ariss['ariss_score']:.1f}/100")
    print(f"Distribution: {ariss['positive_pct']:.0f}% pos | {ariss['neutral_pct']:.0f}% neu | {ariss['negative_pct']:.0f}% neg")
    print(f"Confidence: {ariss['confidence']:.1f}%")
    print(f"{'='*70}\n")
