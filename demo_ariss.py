"""
ARISS Quick Start Example
Demonstrates basic usage without needing full API setup

ARISS = Aggregate Real-time Internet Sentiment Score
"""

import os
from datetime import datetime
from ariss_scorer import ARISSScorer, Comment
from ariss_database import ARISSDatabase

def demo_ariss():
    """Demonstrate ARISS functionality with sample data."""
    
    print("=" * 60)
    print("ARISS - Aggregate Real-time Internet Sentiment Score")
    print("Quick Start Demo")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  No ANTHROPIC_API_KEY found in environment.")
        print("Please set it in your .env file to run this demo.\n")
        return
    
    # Initialize components
    print("\n📊 Initializing ARISS scorer...")
    scorer = ARISSScorer(api_key)
    
    print("💾 Initializing database...")
    db = ARISSDatabase("demo_ariss.db")
    
    # Sample comments about a hypothetical topic
    subject = "New Climate Policy"
    category = "politics"
    
    print(f"\n🔍 Analyzing sentiment for: '{subject}'")
    print("\nSample comments:")
    
    sample_comments = [
        Comment(
            text="This new climate policy is exactly what we need! Finally some real action on emissions.",
            source="reddit",
            platform_id="comment001",
            timestamp=datetime.now(),
            author="user_eco123",
            upvotes=245,
            subreddit="environment"
        ),
        Comment(
            text="The climate policy will destroy jobs and hurt the economy. Complete disaster.",
            source="reddit",
            platform_id="comment002",
            timestamp=datetime.now(),
            author="user_econ456",
            upvotes=89,
            subreddit="economics"
        ),
        Comment(
            text="Mixed feelings about this. Good intentions but implementation seems rushed and unclear.",
            source="youtube",
            platform_id="comment003",
            timestamp=datetime.now(),
            author="thoughtful_voter",
            upvotes=312
        ),
        Comment(
            text="Best policy decision in decades! Every country should follow this model. 🌍",
            source="twitter",
            platform_id="tweet001",
            timestamp=datetime.now(),
            author="climate_warrior",
            upvotes=567
        ),
        Comment(
            text="I've read the full policy document. It's comprehensive and balances economic and environmental concerns well.",
            source="reddit",
            platform_id="comment004",
            timestamp=datetime.now(),
            author="policy_analyst",
            upvotes=892,
            subreddit="NeutralPolitics"
        ),
        Comment(
            text="TOTAL SCAM! Wake up people! They're just trying to control us!!!",
            source="youtube",
            platform_id="comment005",
            timestamp=datetime.now(),
            author="conspiracy_theorist",
            upvotes=-12
        ),
        Comment(
            text="As a scientist, I appreciate the evidence-based approach. Some concerns about timeline but overall positive.",
            source="reddit",
            platform_id="comment006",
            timestamp=datetime.now(),
            author="climate_scientist",
            upvotes=1203,
            subreddit="science"
        )
    ]
    
    # Display sample comments
    for i, comment in enumerate(sample_comments, 1):
        print(f"\n{i}. [{comment.source}] (+{comment.upvotes})")
        print(f"   \"{comment.text[:80]}{'...' if len(comment.text) > 80 else ''}\"")
    
    # Analyze each comment
    print("\n" + "=" * 60)
    print("🤖 Running Sentiment Analysis...")
    print("=" * 60)
    
    sentiment_scores = []
    for i, comment in enumerate(sample_comments, 1):
        print(f"\nAnalyzing comment {i}/{len(sample_comments)}...")
        score = scorer.analyze_comment(comment, subject)
        sentiment_scores.append(score)
        
        print(f"  • TextBlob:  {score.textblob_score:.1f}/100")
        print(f"  • VADER:     {score.vader_score:.1f}/100")
        print(f"  • Claude:    {score.claude_score:.1f}/100")
        print(f"  • Bias:      {score.bias_score:.1f}/100 (lower = more objective)")
        print(f"  • Credibility: {score.source_credibility:.1f}/100")
        print(f"  • Weighted:  {score.weighted_score:.1f}/100")
    
    # Calculate ARISS
    print("\n" + "=" * 60)
    print("📈 Calculating Final ARISS Score...")
    print("=" * 60)
    
    ariss_result = scorer.calculate_ariss(sentiment_scores)
    
    print(f"\n{'🎯 FINAL ARISS SCORE':^60}")
    print("=" * 60)
    print(f"\n{'SCORE:':<20} {ariss_result['ariss_score']:.1f}/100")
    print(f"{'Confidence:':<20} {ariss_result['confidence']:.1f}%")
    print(f"{'Sample Size:':<20} {ariss_result['sample_size']}")
    print(f"{'Mean Bias:':<20} {ariss_result['mean_bias']:.1f}/100")
    print(f"{'Mean Credibility:':<20} {ariss_result['mean_credibility']:.1f}/100")
    print(f"{'Variance:':<20} {ariss_result['variance']:.2f}")
    print(f"{'Std Deviation:':<20} {ariss_result['std_dev']:.2f}")
    print(f"{'Score Range:':<20} {ariss_result['min_score']:.1f} - {ariss_result['max_score']:.1f}")
    
    # Interpretation
    score = ariss_result['ariss_score']
    if score >= 70:
        sentiment = "Very Positive 🎉"
    elif score >= 55:
        sentiment = "Positive 👍"
    elif score >= 45:
        sentiment = "Neutral ➖"
    elif score >= 30:
        sentiment = "Negative 👎"
    else:
        sentiment = "Very Negative 😞"
    
    print(f"\n{'Interpretation:':<20} {sentiment}")
    
    print("\n" + "=" * 60)
    print("💾 Saving to Database...")
    print("=" * 60)
    
    # Save to database
    db.save_ariss_score(subject, ariss_result, category)
    db.save_sentiment_scores(subject, sentiment_scores, category)
    
    print(f"\n✅ Saved ARISS score for '{subject}' to demo_ariss.db")
    
    # Show database contents
    print("\n" + "=" * 60)
    print("📚 Database Contents:")
    print("=" * 60)
    
    all_subjects = db.get_all_subjects()
    print(f"\nTotal subjects tracked: {len(all_subjects)}")
    
    for subj in all_subjects:
        print(f"\n  • {subj['name']}")
        print(f"    Category: {subj.get('category', 'N/A')}")
        print(f"    Scores recorded: {subj.get('score_count', 0)}")
        print(f"    Last updated: {subj.get('last_updated', 'N/A')}")
    
    # Show how to retrieve data
    print("\n" + "=" * 60)
    print("🔍 Retrieving Latest Score:")
    print("=" * 60)
    
    latest = db.get_latest_score(subject)
    if latest:
        print(f"\nSubject: {latest['name']}")
        print(f"Score: {latest['score']:.1f}/100")
        print(f"Timestamp: {latest['timestamp']}")
    
    print("\n" + "=" * 60)
    print("✨ Demo Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set up API credentials for Reddit, YouTube, Twitter in .env")
    print("2. Run: streamlit run ariss_app.py")
    print("3. Try calculating ARISS for real subjects!")
    print("\nDatabase saved as: demo_ariss.db")
    print("=" * 60 + "\n")
    
    db.close()


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    demo_ariss()
