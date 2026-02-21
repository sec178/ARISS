"""
ARISS Web Application
Streamlit app for searching subjects and viewing ARISS scores over time

ARISS = Aggregate Real-time Internet Sentiment Score

Run with: streamlit run ariss_app.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

# Import our modules
from ariss_scorer import (
    ARISSScorer, RedditScraper, YouTubeScraper, 
    TwitterScraper, Comment
)
from ariss_database import ARISSDatabase

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ARISS - Internet Sentiment Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .score-number {
        font-size: 4rem;
        font-weight: bold;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scorer' not in st.session_state:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        st.session_state.scorer = ARISSScorer(api_key)
    else:
        st.session_state.scorer = None
if 'current_subject' not in st.session_state:
    st.session_state.current_subject = None


def get_database():
    """Get database instance (creates new connection per thread)."""
    return ARISSDatabase()


def get_score_color(score: float) -> str:
    """Get color based on sentiment score."""
    if score >= 70:
        return "#10b981"  # Green
    elif score >= 55:
        return "#3b82f6"  # Blue
    elif score >= 45:
        return "#6b7280"  # Gray
    elif score >= 30:
        return "#f59e0b"  # Orange
    else:
        return "#ef4444"  # Red


def get_sentiment_label(score: float) -> str:
    """Get sentiment label based on score."""
    if score >= 70:
        return "Very Positive"
    elif score >= 55:
        return "Positive"
    elif score >= 45:
        return "Neutral"
    elif score >= 30:
        return "Negative"
    else:
        return "Very Negative"


def calculate_new_ariss(subject: str, category: str = None):
    """Calculate a new ARISS score for a subject."""
    if not st.session_state.scorer:
        st.error("⚠️ ANTHROPIC_API_KEY not found. Please set it in your .env file.")
        return None
    
    # Get database instance
    db = get_database()
    
    all_comments = []
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Fetch context for subject
    status_text.text(f"🔍 Understanding context for '{subject}'...")
    context = st.session_state.scorer._get_current_context(subject)
    
    # Reddit scraping
    reddit_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
    
    if reddit_id and reddit_secret:
        try:
            status_text.text("🔍 Searching Reddit...")
            scraper = RedditScraper(
                reddit_id, 
                reddit_secret, 
                "ARISS_Bot/1.0"
            )
            reddit_comments = scraper.search_comments(subject, limit=100)
            all_comments.extend(reddit_comments)
            progress_bar.progress(0.33)
        except Exception as e:
            st.warning(f"Reddit scraping failed: {e}")
    
    # YouTube scraping
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    if youtube_key:
        try:
            status_text.text("🔍 Searching YouTube...")
            scraper = YouTubeScraper(youtube_key)
            youtube_comments = scraper.search_comments(subject, limit=50)
            all_comments.extend(youtube_comments)
            progress_bar.progress(0.66)
        except Exception as e:
            st.warning(f"YouTube scraping failed: {e}")
    
    # Twitter scraping
    twitter_token = os.getenv("TWITTER_BEARER_TOKEN")
    if twitter_token:
        try:
            status_text.text("🔍 Searching Twitter...")
            scraper = TwitterScraper(twitter_token)
            twitter_comments = scraper.search_tweets(subject, limit=50)
            all_comments.extend(twitter_comments)
        except Exception as e:
            st.warning(f"Twitter scraping failed: {e}")
    
    progress_bar.progress(1.0)
    status_text.text(f"✅ Found {len(all_comments)} comments")
    
    if not all_comments:
        st.error("No comments found. Try a different subject or check API credentials.")
        return None
    
    # Analyze comments with context
    status_text.text(f"🤖 Analyzing sentiment with context: {context[:100]}...")
    sentiment_results = []
    
    analysis_progress = st.progress(0)
    for i, comment in enumerate(all_comments):
        result = st.session_state.scorer.analyze_comment_with_context(
            comment, subject, context
        )
        sentiment_results.append(result)
        analysis_progress.progress((i + 1) / len(all_comments))
    
    # Calculate ARISS
    ariss_result = st.session_state.scorer.calculate_ariss(sentiment_results)
    
    # Save to database - adapt v3 SentimentResult to old format for compatibility
    # Convert SentimentResults to dict-like objects with expected fields
    class SentimentScoreAdapter:
        def __init__(self, result):
            self.comment_id = result.comment_id
            self.text = result.text
            self.source = result.source
            self.timestamp = result.timestamp
            self.textblob_score = 50.0  # v3 doesn't use these, provide defaults
            self.vader_score = 50.0
            self.claude_score = result.sentiment_score
            self.bias_score = 50.0  # v3 tracks this differently
            self.source_credibility = 65.0  # default
            self.length_weight = 1.0
            self.word_count = result.word_count
            self.weighted_score = result.sentiment_score
            self.upvotes = result.upvotes
            self.author = result.author
    
    adapted_results = [SentimentScoreAdapter(r) for r in sentiment_results]
    
    # Save to database
    db.save_ariss_score(subject, ariss_result, category)
    db.save_sentiment_scores(subject, adapted_results, category)
    
    progress_bar.empty()
    status_text.empty()
    analysis_progress.empty()
    
    return ariss_result, sentiment_results


def display_score_gauge(score: float, label: str = "ARISS Score"):
    """Display a gauge chart for the score with properly centered number."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={
            'text': label, 
            'font': {'size': 24},
            'align': 'center'
        },
        number={
            'font': {'size': 60},
            'valueformat': '.0f',
            'suffix': '',
            'prefix': ''
        },
        gauge={
            'axis': {
                'range': [0, 100], 
                'tickwidth': 1, 
                'tickcolor': "darkgray",
                'tickmode': 'linear',
                'tick0': 0,
                'dtick': 20
            },
            'bar': {'color': get_score_color(score), 'thickness': 0.75},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#fee2e2'},
                {'range': [30, 45], 'color': '#fef3c7'},
                {'range': [45, 55], 'color': '#e5e7eb'},
                {'range': [55, 70], 'color': '#dbeafe'},
                {'range': [70, 100], 'color': '#d1fae5'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def display_history_chart(df: pd.DataFrame):
    """Display historical trend chart."""
    if df.empty:
        st.info("No historical data available yet. Check back after collecting more data points.")
        return
    
    fig = go.Figure()
    
    # Main score line
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['score'],
        mode='lines+markers',
        name='ARISS Score',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8),
        hovertemplate='<b>%{x|%Y-%m-%d %H:%M}</b><br>Score: %{y:.1f}<extra></extra>'
    ))
    
    # Add neutral line
    fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                  annotation_text="Neutral", annotation_position="right")
    
    fig.update_layout(
        title="ARISS Score Over Time",
        xaxis_title="Date",
        yaxis_title="ARISS Score",
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        height=400,
        showlegend=True
    )
    
    return fig


def display_source_breakdown(source_breakdown: dict):
    """Display pie chart of source distribution."""
    if not source_breakdown:
        return None
    
    labels = list(source_breakdown.keys())
    values = list(source_breakdown.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=px.colors.qualitative.Set3)
    )])
    
    fig.update_layout(
        title="Data Sources",
        height=300,
        showlegend=True
    )
    
    return fig


def main():
    """Main application."""
    
    # Header
    st.markdown('<div class="main-header">📊 ARISS</div>', unsafe_allow_html=True)
    st.markdown("""
    <p style="text-align: center; font-size: 1.2rem; color: #666; margin-top: -1rem;">
    Aggregate Real-time Internet Sentiment Score
    </p>
    <p style="text-align: center; font-size: 1.5rem; color: #667eea; font-weight: 600; margin-top: -0.5rem;">
    What does the internet think?
    </p>
    """, unsafe_allow_html=True)
    
    # Initialize analyzer
    if not st.session_state.scorer:
        st.error("⚠️ ANTHROPIC_API_KEY not found. Please set it in your .env file.")
        st.stop()
    
    # Get database instance (before sidebar uses it)
    db = get_database()
    
    # Sidebar
    with st.sidebar:
        st.header("🔍 Search")
        
        # Search or new subject
        search_mode = st.radio(
            "Mode",
            ["Search Existing", "New Subject"],
            horizontal=True
        )
        
        if search_mode == "Search Existing":
            # Get all subjects
            subjects = db.get_all_subjects()
            
            if subjects:
                subject_names = [s['name'] for s in subjects]
                selected = st.selectbox(
                    "Select Subject",
                    options=subject_names,
                    index=0 if subject_names else None
                )
                
                if st.button("View", type="primary", use_container_width=True):
                    st.session_state.current_subject = selected
                    st.rerun()
                
                # Show trending subjects
                st.divider()
                st.subheader("📈 Trending")
                trending = db.get_trending_subjects(days=7, min_change=5.0)
                
                if trending:
                    for item in trending[:5]:
                        change = item['change']
                        arrow = "🔺" if change > 0 else "🔻"
                        st.write(f"{arrow} **{item['name']}** ({change:+.1f})")
                else:
                    st.caption("No trending subjects yet")
            else:
                st.info("No subjects tracked yet. Add one using 'New Subject' mode.")
        
        else:  # New Subject
            subject_input = st.text_input(
                "Subject Name",
                placeholder="e.g., Donald Trump, Bitcoin, Taylor Swift"
            )
            
            category_input = st.selectbox(
                "Category",
                ["Politics", "Economics", "Entertainment", "Sports", 
                 "Technology", "Other"]
            )
            
            if st.button("Calculate ARISS", type="primary", use_container_width=True):
                if subject_input:
                    with st.spinner(f"Calculating ARISS for '{subject_input}'..."):
                        result = calculate_new_ariss(
                            subject_input, 
                            category_input.lower()
                        )
                        if result:
                            st.session_state.current_subject = subject_input
                            st.success("✅ ARISS calculated!")
                            st.rerun()
                else:
                    st.error("Please enter a subject name")
        
        st.divider()
        
        st.header("📋 About This Tool")
        st.write("""
        This tool helps you:
        - 📄 Track real-time internet sentiment
        - 🚨 Understand public opinion
        - 💰 Monitor sentiment trends over time
        - ✏️ Get context-aware analysis
        - ⚖️ See distribution of opinions
        """)
        
        st.divider()
        
        st.header("ℹ️ About ARISS")
        st.caption("""
        ARISS (Aggregate Real-time Internet Sentiment Score) aggregates sentiment 
        from Reddit, YouTube, and Twitter to create a real-time score (0-100) of 
        internet opinion using context-aware AI analysis.
        
        - **0-30**: Very Negative
        - **30-45**: Negative  
        - **45-55**: Neutral
        - **55-70**: Positive
        - **70-100**: Very Positive
        """)
    
    # Main content
    if st.session_state.current_subject:
        subject = st.session_state.current_subject
        
        # Get latest score
        latest = db.get_latest_score(subject)
        
        if latest:
            # Header with subject name
            col1, col2 = st.columns([3, 1])
            with col1:
                st.title(subject)
                if latest.get('category'):
                    st.caption(f"Category: {latest['category'].title()}")
            
            with col2:
                if st.button("🔄 Refresh Score"):
                    with st.spinner("Recalculating..."):
                        result = calculate_new_ariss(
                            subject, 
                            latest.get('category')
                        )
                        if result:
                            st.success("Updated!")
                            st.rerun()
            
            st.divider()
            
            # Current score display
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                # Gauge chart
                st.plotly_chart(
                    display_score_gauge(latest['score']),
                    use_container_width=True
                )
            
            with col2:
                st.markdown("### Metrics")
                st.metric(
                    "Sentiment",
                    get_sentiment_label(latest['score']),
                    f"{latest['score']:.1f}/100"
                )
                st.metric(
                    "Confidence",
                    f"{latest.get('confidence', 0):.0f}%"
                )
                st.metric(
                    "Sample Size",
                    f"{latest.get('sample_size', 0)}"
                )
            
            with col3:
                st.markdown("### Distribution")
                st.metric(
                    "Positive",
                    f"{latest.get('positive_pct', 0):.0f}%",
                    delta=None,
                    delta_color="normal"
                )
                st.metric(
                    "Neutral",
                    f"{latest.get('neutral_pct', 0):.0f}%"
                )
                st.metric(
                    "Negative",
                    f"{latest.get('negative_pct', 0):.0f}%"
                )
            
            # Source breakdown
            if latest.get('source_breakdown'):
                import json
                source_breakdown = json.loads(latest['source_breakdown'])
                st.plotly_chart(
                    display_source_breakdown(source_breakdown),
                    use_container_width=True
                )
            
            st.divider()
            
            # Historical trends
            st.header("📈 Historical Trends")
            
            # Time range selector
            time_range = st.selectbox(
                "Time Range",
                ["7 Days", "30 Days", "90 Days", "1 Year", "All Time"],
                index=1
            )
            
            days_map = {
                "7 Days": 7,
                "30 Days": 30,
                "90 Days": 90,
                "1 Year": 365,
                "All Time": 10000
            }
            
            history_df = db.get_score_history(
                subject, 
                days=days_map[time_range]
            )
            
            if not history_df.empty:
                st.plotly_chart(
                    display_history_chart(history_df),
                    use_container_width=True
                )
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Average Score", f"{history_df['score'].mean():.1f}")
                with col2:
                    st.metric("Highest", f"{history_df['score'].max():.1f}")
                with col3:
                    st.metric("Lowest", f"{history_df['score'].min():.1f}")
                with col4:
                    score_change = history_df['score'].iloc[-1] - history_df['score'].iloc[0]
                    st.metric(
                        "Change", 
                        f"{score_change:+.1f}",
                        delta=f"{score_change:+.1f}"
                    )
            else:
                st.info("No historical data available yet. Refresh the score a few times to build history.")
            
            # Recent comments analysis
            st.divider()
            st.header("💬 Recent Comments Analysis")
            
            # Get sentiment details from database
            sentiment_df = db.get_sentiment_details(subject, limit=100)
            
            if not sentiment_df.empty:
                # Show distribution histogram
                fig = px.histogram(
                    sentiment_df,
                    x='claude_score',
                    nbins=20,
                    title="Sentiment Distribution",
                    labels={'claude_score': 'Sentiment Score', 'count': 'Number of Comments'},
                    color_discrete_sequence=['#667eea']
                )
                fig.add_vline(x=50, line_dash="dash", line_color="gray", annotation_text="Neutral")
                st.plotly_chart(fig, use_container_width=True)
                
                # Show sample comments
                st.subheader("Sample Comments")
                
                # Filter options
                col1, col2 = st.columns(2)
                with col1:
                    filter_sentiment = st.selectbox(
                        "Filter by Sentiment",
                        ["All", "Positive (>60)", "Neutral (40-60)", "Negative (<40)"]
                    )
                
                with col2:
                    filter_source = st.selectbox(
                        "Filter by Source",
                        ["All"] + list(sentiment_df['source'].unique())
                    )
                
                # Apply filters
                filtered_df = sentiment_df.copy()
                
                if filter_sentiment != "All":
                    if filter_sentiment == "Positive (>60)":
                        filtered_df = filtered_df[filtered_df['claude_score'] > 60]
                    elif filter_sentiment == "Neutral (40-60)":
                        filtered_df = filtered_df[
                            (filtered_df['claude_score'] >= 40) & 
                            (filtered_df['claude_score'] <= 60)
                        ]
                    else:  # Negative
                        filtered_df = filtered_df[filtered_df['claude_score'] < 40]
                
                if filter_source != "All":
                    filtered_df = filtered_df[filtered_df['source'] == filter_source]
                
                # Display comments
                for idx, row in filtered_df.head(10).iterrows():
                    score = row['claude_score']
                    upvotes = row.get('upvotes', 0)
                    
                    # Color-code by sentiment
                    if score >= 60:
                        sentiment_emoji = "😊"
                        sentiment_color = "#10b981"
                    elif score >= 40:
                        sentiment_emoji = "😐"
                        sentiment_color = "#6b7280"
                    else:
                        sentiment_emoji = "😠"
                        sentiment_color = "#ef4444"
                    
                    with st.expander(
                        f"{sentiment_emoji} **{row['source'].title()}** — Score: {score:.0f}/100 "
                        f"| {row.get('word_count', 0)} words "
                        f"({'↑' if upvotes > 0 else ''}{upvotes})"
                    ):
                        # Display comment text
                        st.markdown(f"**Comment:**")
                        st.write(row['text'])
                        
                        # Display metrics
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.caption(f"**Sentiment Score**")
                            st.markdown(f"<span style='color: {sentiment_color}; font-size: 1.5rem; font-weight: bold;'>{score:.0f}/100</span>", unsafe_allow_html=True)
                        
                        with col2:
                            st.caption(f"**Credibility**")
                            st.write(f"{row.get('source_credibility', 50):.0f}/100")
                        
                        with col3:
                            st.caption(f"**Bias**")
                            bias = row.get('bias_score', 50)
                            bias_label = "Low" if bias < 30 else "Medium" if bias < 60 else "High"
                            st.write(f"{bias:.0f}/100 ({bias_label})")
                        
                        with col4:
                            st.caption(f"**Posted**")
                            st.write(row['timestamp'].strftime('%Y-%m-%d'))
                
                if len(filtered_df) == 0:
                    st.info("No comments match the selected filters.")
                elif len(filtered_df) > 10:
                    st.caption(f"Showing 10 of {len(filtered_df)} filtered comments")
            else:
                st.info("No comment data available. Calculate a new score to see individual comments.")
        
        else:
            st.error(f"No data found for '{subject}'. Try calculating a new score.")
    
    else:
        # Landing page
        st.markdown("""
        ## Welcome to ARISS
        
        **Track real-time public sentiment across the internet.**
        
        ARISS analyzes thousands of comments from Reddit, YouTube, and Twitter to provide 
        a real-time measure of what people are actually saying online about any topic.
        
        ### How it works:
        
        1. **Context**: Fetch recent news/events about the subject
        2. **Scrape**: Collect recent comments from social platforms
        3. **Analyze**: Use context-aware AI to understand sentiment
        4. **Score**: Calculate net sentiment score from 0-100
        
        ### Get Started:
        
        👈 Use the sidebar to search for existing subjects or calculate a new ARISS score.
        
        ### Popular Subjects:
        """)
        
        # Show some subjects if they exist
        subjects = db.get_all_subjects()
        
        if subjects:
            cols = st.columns(3)
            for i, subject in enumerate(subjects[:6]):
                with cols[i % 3]:
                    latest = db.get_latest_score(subject['name'])
                    if latest:
                        score = latest['score']
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>{subject['name']}</h3>
                            <div style="font-size: 2rem; color: {get_score_color(score)}; font-weight: bold;">
                                {score:.0f}
                            </div>
                            <div style="color: #666;">
                                {get_sentiment_label(score)}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("View Details", key=f"view_{i}"):
                            st.session_state.current_subject = subject['name']
                            st.rerun()
        else:
            st.info("No subjects tracked yet. Use the sidebar to add your first one!")


if __name__ == "__main__":
    main()
