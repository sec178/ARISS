"""
ARISS Database Module
Stores and retrieves ARISS scores over time for trending analysis
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import threading


class ARISSDatabase:
    """Database for storing ARISS scores and sentiment data."""
    
    def __init__(self, db_path: str = "ariss_data.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._local = threading.local()
        self._create_tables()
    
    def _get_connection(self):
        """Get thread-safe database connection."""
        # Each thread gets its own connection
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Table for subjects being tracked
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table for ARISS scores over time
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ariss_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                score REAL NOT NULL,
                confidence REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                mean_bias REAL,
                mean_credibility REAL,
                variance REAL,
                std_dev REAL,
                min_score REAL,
                max_score REAL,
                source_breakdown TEXT,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
        """)
        
        # Table for individual sentiment scores (for detailed analysis)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                comment_id TEXT UNIQUE NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                textblob_score REAL,
                vader_score REAL,
                claude_score REAL,
                bias_score REAL,
                source_credibility REAL,
                weighted_score REAL,
                upvotes INTEGER,
                author TEXT,
                timestamp TIMESTAMP,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ariss_subject_time 
            ON ariss_scores(subject_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_subject_time 
            ON sentiment_scores(subject_id, timestamp)
        """)
        
        conn.commit()
    
    def add_subject(self, name: str, category: Optional[str] = None) -> int:
        """
        Add a new subject to track or get existing subject ID.
        
        Args:
            name: Subject name (e.g., "Donald Trump", "Dow Jones")
            category: Optional category (e.g., "politics", "economics")
            
        Returns:
            Subject ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Try to insert, ignore if exists
        cursor.execute("""
            INSERT OR IGNORE INTO subjects (name, category) 
            VALUES (?, ?)
        """, (name, category))
        conn.commit()
        
        # Get the subject ID
        cursor.execute("SELECT id FROM subjects WHERE name = ?", (name,))
        result = cursor.fetchone()
        return result[0]
    
    def save_ariss_score(self, subject_name: str, ariss_data: Dict[str, Any], 
                        category: Optional[str] = None) -> int:
        """
        Save an ARISS score calculation to the database.
        
        Args:
            subject_name: Name of subject
            ariss_data: Dictionary from ARISSScorer.calculate_ariss()
            category: Optional category
            
        Returns:
            Score ID
        """
        # Get or create subject
        subject_id = self.add_subject(subject_name, category)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Convert source breakdown to JSON
        source_breakdown = json.dumps(ariss_data.get('source_breakdown', {}))
        
        # Store any additional metadata
        metadata_dict = {k: v for k, v in ariss_data.items() 
                        if k not in ['ariss_score', 'confidence', 'sample_size', 
                                    'mean_bias', 'mean_credibility', 'variance',
                                    'std_dev', 'min_score', 'max_score', 
                                    'source_breakdown', 'timestamp']}
        metadata = json.dumps(metadata_dict)
        
        cursor.execute("""
            INSERT INTO ariss_scores (
                subject_id, score, confidence, sample_size,
                mean_bias, mean_credibility, variance, std_dev,
                min_score, max_score, source_breakdown, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subject_id,
            ariss_data.get('ariss_score', 50.0),
            ariss_data.get('confidence', 0.0),
            ariss_data.get('sample_size', 0),
            ariss_data.get('mean_bias'),
            ariss_data.get('mean_credibility'),
            ariss_data.get('variance'),
            ariss_data.get('std_dev'),
            ariss_data.get('min_score'),
            ariss_data.get('max_score'),
            source_breakdown,
            metadata
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def save_sentiment_scores(self, subject_name: str, 
                            sentiment_scores: List[Any],
                            category: Optional[str] = None):
        """
        Save individual sentiment scores to database.
        
        Args:
            subject_name: Name of subject
            sentiment_scores: List of SentimentScore objects
            category: Optional category
        """
        # Get or create subject
        subject_id = self.add_subject(subject_name, category)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for score in sentiment_scores:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO sentiment_scores (
                        subject_id, comment_id, text, source,
                        textblob_score, vader_score, claude_score,
                        bias_score, source_credibility, weighted_score,
                        upvotes, author, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    subject_id,
                    score.comment_id,
                    score.text,
                    score.source,
                    score.textblob_score,
                    score.vader_score,
                    score.claude_score,
                    score.bias_score,
                    score.source_credibility,
                    score.weighted_score,
                    score.upvotes,
                    score.author,
                    score.timestamp.isoformat()
                ))
            except Exception as e:
                print(f"Error saving sentiment score: {e}")
        
        conn.commit()
    
    def get_latest_score(self, subject_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent ARISS score for a subject.
        
        Args:
            subject_name: Name of subject
            
        Returns:
            Dictionary with score data or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, a.*
            FROM ariss_scores a
            JOIN subjects s ON a.subject_id = s.id
            WHERE s.name = ?
            ORDER BY a.timestamp DESC
            LIMIT 1
        """, (subject_name,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_score_history(self, subject_name: str, 
                         days: int = 30) -> pd.DataFrame:
        """
        Get historical ARISS scores for a subject.
        
        Args:
            subject_name: Name of subject
            days: Number of days of history to retrieve
            
        Returns:
            DataFrame with historical scores
        """
        conn = self._get_connection()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                a.timestamp,
                a.score,
                a.confidence,
                a.sample_size,
                a.mean_bias,
                a.mean_credibility,
                a.variance
            FROM ariss_scores a
            JOIN subjects s ON a.subject_id = s.id
            WHERE s.name = ?
            AND a.timestamp >= ?
            ORDER BY a.timestamp ASC
        """
        
        df = pd.read_sql_query(query, conn, params=(subject_name, cutoff_date))
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def get_all_subjects(self) -> List[Dict[str, Any]]:
        """
        Get all subjects being tracked.
        
        Returns:
            List of subject dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, 
                   COUNT(a.id) as score_count,
                   MAX(a.timestamp) as last_updated
            FROM subjects s
            LEFT JOIN ariss_scores a ON s.id = a.subject_id
            GROUP BY s.id
            ORDER BY last_updated DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_trending_subjects(self, days: int = 7, 
                             min_change: float = 5.0) -> List[Dict[str, Any]]:
        """
        Get subjects with significant score changes.
        
        Args:
            days: Number of days to look back
            min_change: Minimum score change to be considered trending
            
        Returns:
            List of trending subjects with change data
        """
        conn = self._get_connection()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            WITH recent_scores AS (
                SELECT 
                    s.name,
                    s.category,
                    a.score,
                    a.timestamp,
                    ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY a.timestamp DESC) as rn_desc,
                    ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY a.timestamp ASC) as rn_asc
                FROM ariss_scores a
                JOIN subjects s ON a.subject_id = s.id
                WHERE a.timestamp >= ?
            ),
            latest AS (
                SELECT name, category, score as latest_score
                FROM recent_scores
                WHERE rn_desc = 1
            ),
            earliest AS (
                SELECT name, score as earliest_score
                FROM recent_scores
                WHERE rn_asc = 1
            )
            SELECT 
                l.name,
                l.category,
                l.latest_score,
                e.earliest_score,
                (l.latest_score - e.earliest_score) as change,
                ABS(l.latest_score - e.earliest_score) as abs_change
            FROM latest l
            JOIN earliest e ON l.name = e.name
            WHERE ABS(l.latest_score - e.earliest_score) >= ?
            ORDER BY abs_change DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(cutoff_date, min_change))
        
        return df.to_dict('records')
    
    def search_subjects(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for subjects by name.
        
        Args:
            search_term: Search string
            
        Returns:
            List of matching subjects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.*, 
                   COUNT(a.id) as score_count,
                   MAX(a.timestamp) as last_updated
            FROM subjects s
            LEFT JOIN ariss_scores a ON s.id = a.subject_id
            WHERE s.name LIKE ?
            GROUP BY s.id
            ORDER BY score_count DESC
        """, (f"%{search_term}%",))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_sentiment_details(self, subject_name: str, 
                             limit: int = 100) -> pd.DataFrame:
        """
        Get detailed sentiment scores for a subject.
        
        Args:
            subject_name: Name of subject
            limit: Maximum number of records
            
        Returns:
            DataFrame with sentiment details
        """
        conn = self._get_connection()
        
        query = """
            SELECT 
                ss.text,
                ss.source,
                ss.claude_score,
                ss.bias_score,
                ss.source_credibility,
                ss.weighted_score,
                ss.upvotes,
                ss.timestamp
            FROM sentiment_scores ss
            JOIN subjects s ON ss.subject_id = s.id
            WHERE s.name = ?
            ORDER BY ss.timestamp DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(subject_name, limit))
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def close(self):
        """Close database connection for current thread."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None


# Example usage
if __name__ == "__main__":
    # Initialize database
    db = ARISSDatabase("test_ariss.db")
    
    # Add a subject
    subject_id = db.add_subject("Test Subject", "test")
    print(f"Subject ID: {subject_id}")
    
    # Save a sample score
    sample_ariss = {
        'ariss_score': 67.5,
        'confidence': 75.0,
        'sample_size': 150,
        'mean_bias': 45.0,
        'mean_credibility': 65.0,
        'variance': 120.5,
        'std_dev': 10.98,
        'min_score': 20.0,
        'max_score': 95.0,
        'source_breakdown': {'reddit': 100, 'youtube': 50},
        'timestamp': datetime.now().isoformat()
    }
    
    score_id = db.save_ariss_score("Test Subject", sample_ariss, "test")
    print(f"Saved score ID: {score_id}")
    
    # Retrieve latest score
    latest = db.get_latest_score("Test Subject")
    print(f"Latest score: {latest}")
    
    # Get all subjects
    subjects = db.get_all_subjects()
    print(f"All subjects: {subjects}")
    
    db.close()
