# ARISS Bug Fixes and Updates

## Version 1.2 - Rebranding and Philosophy Shift

### Name Change
**ARISS** now stands for **Aggregate Real-time Internet Sentiment Score** (previously "Representative")

**Rationale:** 
- "Representative" implied filtered/curated data
- The goal is to measure what the internet *actually* says in real-time
- "Real-time" better reflects the live, current nature of the data
- More honest about what we're measuring: internet sentiment, not representative polling

### Philosophy
ARISS measures **raw internet sentiment** — what people are actually saying online, including:
- Strong emotions and reactions
- Extreme viewpoints  
- Passionate fans and critics
- The full spectrum of online discourse

This is different from traditional polling, which filters for representative samples. ARISS shows you the unfiltered pulse of the internet.

---

## Version 1.1 - Bug Fixes

### Fixed Issues

#### 1. Anthropic SDK Compatibility Error
**Error:** `TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`

**Fix:** Updated `ariss_scorer.py` to handle multiple SDK versions:
```python
# Now uses try-except to support both old and new SDK versions
try:
    self.client = anthropic.Anthropic(api_key=anthropic_api_key)
except TypeError:
    os.environ['ANTHROPIC_API_KEY'] = anthropic_api_key
    self.client = anthropic.Anthropic()
```

**Solution:** Run `pip install anthropic --upgrade`

---

#### 2. SQLite Threading Error with Streamlit
**Error:** `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`

**Root Cause:** Streamlit creates new threads on reruns, but SQLite connections aren't thread-safe when stored in session state.

**Fix:** Updated `ariss_database.py` to use thread-local storage:
```python
import threading

class ARISSDatabase:
    def __init__(self, db_path: str = "ariss_data.db"):
        self.db_path = db_path
        self._local = threading.local()  # Thread-local storage
        self._create_tables()
    
    def _get_connection(self):
        # Each thread gets its own connection
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
```

**Updated:** `ariss_app.py` to create fresh database instances instead of storing in session_state:
```python
def get_database():
    """Get database instance (creates new connection per thread)."""
    return ARISSDatabase()

# Changed from:
# st.session_state.db.get_all_subjects()
# To:
# db = get_database()
# db.get_all_subjects()
```

---

### New Features

#### Setup Helper Script
Added `setup.py` to automate installation and configuration:
```bash
python setup.py
```

Features:
- Checks Python version compatibility
- Installs all dependencies automatically
- Downloads NLTK data
- Creates .env file from template
- Shows API key instructions
- Offers to run demo

---

### Updated Files

1. **ariss_scorer.py**
   - Fixed Anthropic SDK initialization
   - Added version compatibility handling

2. **ariss_database.py**
   - Implemented thread-safe connections using threading.local()
   - Added connection timeout
   - Fixed check_same_thread issue

3. **ariss_app.py**
   - Removed database from session_state
   - Created get_database() helper function
   - Updated all database access points

4. **requirements.txt**
   - Removed strict version constraints
   - Added installation notes

5. **README.md**
   - Added troubleshooting section
   - Added common issues and solutions

6. **setup.py** (NEW)
   - Interactive setup wizard
   - Automated installation

---

### Testing Recommendations

After updating, test these key flows:

1. **Basic Flow:**
   ```bash
   streamlit run ariss_app.py
   # Try calculating a score for a new subject
   ```

2. **Multiple Calculations:**
   - Calculate score for Subject A
   - Immediately calculate score for Subject B
   - Verify both appear in database

3. **Refresh Test:**
   - View a subject's score
   - Click "Refresh Score"
   - Verify new score is saved

4. **Historical Data:**
   - Calculate same subject multiple times
   - Check that history chart shows all data points

---

### Known Limitations

1. **API Rate Limits:** 
   - Social media APIs have rate limits
   - May need multiple runs for large datasets

2. **Sample Size:**
   - Minimum 50-100 comments recommended
   - Confidence increases with more data

3. **Language:**
   - Currently optimized for English
   - Non-English content may not analyze well

---

### Future Improvements

- [ ] Add connection pooling for better performance
- [ ] Implement caching for frequently accessed subjects
- [ ] Add background job queue for long-running calculations
- [ ] Support for scheduled automatic score updates
- [ ] Export functionality (CSV, JSON, PDF)
- [ ] API endpoints for external integration

---

### Support

If you encounter issues:

1. Update dependencies: `pip install -r requirements.txt --upgrade`
2. Check .env file has valid API keys
3. Delete `ariss_data.db` and restart (fresh database)
4. Run `python demo_ariss.py` to test core functionality
5. Check README.md troubleshooting section

---

### Version History

**v1.2** (Current)
- Rebranded to "Aggregate Real-time Internet Sentiment Score"
- Philosophy shift: measuring real internet sentiment, not filtered representative samples
- Improved scraping diversity (relevance + new/time sorting)
- Enhanced comment length weighting
- Better bias detection calibration
- Removed regression-to-50 in scoring formula

**v1.1**
- Fixed Anthropic SDK compatibility
- Fixed SQLite threading issues
- Added setup.py helper script
- Improved error handling
- Added troubleshooting documentation

**v1.0** (Initial Release)
- Multi-platform sentiment analysis
- Advanced NLP with Claude AI
- Bias detection and weighting
- Time-series tracking
- Web dashboard
