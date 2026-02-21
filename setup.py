"""
ARISS Setup Helper
Guides user through installation and configuration
"""

import os
import sys
import subprocess

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def check_python_version():
    """Check if Python version is compatible."""
    print_header("Checking Python Version")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ ERROR: Python 3.8 or higher is required")
        print("Please upgrade Python and try again.")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_dependencies():
    """Install required packages."""
    print_header("Installing Dependencies")
    
    print("This will install the following packages:")
    print("  • anthropic (AI sentiment analysis)")
    print("  • praw (Reddit API)")
    print("  • google-api-python-client (YouTube API)")
    print("  • tweepy (Twitter API)")
    print("  • streamlit (Web interface)")
    print("  • plotly (Visualization)")
    print("  • pandas, numpy (Data processing)")
    print("  • textblob, vaderSentiment (Sentiment analysis)")
    print("  • python-dotenv (Configuration)")
    
    response = input("\nProceed with installation? (y/n): ")
    
    if response.lower() != 'y':
        print("⏭️  Skipping dependency installation")
        return True
    
    try:
        print("\n📦 Installing packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("\n✅ All dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Installation failed: {e}")
        print("\nYou can try installing manually with:")
        print("  pip install -r requirements.txt")
        return False

def download_nltk_data():
    """Download required NLTK data."""
    print_header("Downloading NLTK Data")
    
    try:
        import nltk
        print("Downloading required NLTK datasets...")
        nltk.download('brown', quiet=True)
        nltk.download('punkt', quiet=True)
        try:
            nltk.download('punkt_tab', quiet=True)
        except:
            pass  # punkt_tab may not be available in all versions
        print("✅ NLTK data downloaded")
        return True
    except Exception as e:
        print(f"⚠️  NLTK download warning: {e}")
        print("You may need to download manually later")
        return True

def setup_env_file():
    """Create .env file from template."""
    print_header("Setting Up Configuration")
    
    if os.path.exists('.env'):
        print("⚠️  .env file already exists")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("⏭️  Keeping existing .env file")
            return True
    
    if not os.path.exists('.env.template'):
        print("⚠️  .env.template not found")
        print("Creating basic .env file...")
        with open('.env', 'w') as f:
            f.write("# ARISS Configuration\n")
            f.write("ANTHROPIC_API_KEY=your_key_here\n")
            f.write("REDDIT_CLIENT_ID=your_key_here\n")
            f.write("REDDIT_CLIENT_SECRET=your_key_here\n")
            f.write("YOUTUBE_API_KEY=your_key_here\n")
            f.write("TWITTER_BEARER_TOKEN=your_key_here\n")
    else:
        print("Copying .env.template to .env...")
        with open('.env.template', 'r') as src:
            with open('.env', 'w') as dst:
                dst.write(src.read())
    
    print("✅ .env file created")
    print("\n⚠️  IMPORTANT: Edit .env file and add your API keys")
    return True

def show_api_instructions():
    """Show instructions for getting API keys."""
    print_header("API Key Instructions")
    
    print("You need to obtain API keys from the following services:\n")
    
    print("1. ANTHROPIC (Required)")
    print("   • Go to: https://console.anthropic.com/")
    print("   • Create account and navigate to API Keys")
    print("   • Create new key and copy to .env file\n")
    
    print("2. REDDIT (Recommended)")
    print("   • Go to: https://www.reddit.com/prefs/apps")
    print("   • Click 'Create App' or 'Create Another App'")
    print("   • Select 'script' type")
    print("   • Copy client ID and secret to .env file\n")
    
    print("3. YOUTUBE (Recommended)")
    print("   • Go to: https://console.cloud.google.com/")
    print("   • Create project and enable YouTube Data API v3")
    print("   • Create API key and copy to .env file\n")
    
    print("4. TWITTER (Optional)")
    print("   • Apply at: https://developer.twitter.com/")
    print("   • Create app and generate Bearer Token")
    print("   • Copy to .env file\n")

def run_demo():
    """Ask if user wants to run demo."""
    print_header("Run Demo")
    
    print("The demo script shows how ARISS works with sample data.")
    print("You only need the Anthropic API key for the demo.\n")
    
    response = input("Run demo now? (y/n): ")
    
    if response.lower() == 'y':
        try:
            print("\n🚀 Running demo...\n")
            subprocess.call([sys.executable, "demo_ariss.py"])
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            print("\nYou can run it manually with:")
            print("  python demo_ariss.py")
    else:
        print("⏭️  Skipping demo")

def show_next_steps():
    """Show next steps."""
    print_header("Setup Complete!")
    
    print("✅ ARISS is ready to use!\n")
    print("Next steps:\n")
    print("1. Edit .env file and add your API keys")
    print("   • At minimum, add your ANTHROPIC_API_KEY")
    print("   • Add Reddit, YouTube, Twitter keys for full functionality\n")
    print("2. Run the demo to test:")
    print("   python demo_ariss.py\n")
    print("3. Launch the web app:")
    print("   streamlit run ariss_app.py\n")
    print("4. Start calculating ARISS scores!\n")
    print("For help, see README.md or visit the documentation")
    print("=" * 60 + "\n")

def main():
    """Main setup process."""
    print("\n" + "🎯" * 30)
    print("   ARISS - Setup Helper")
    print("   Aggregate Real-time Internet Sentiment Score")
    print("🎯" * 30)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install dependencies
    if not install_dependencies():
        print("\n⚠️  Setup incomplete due to installation errors")
        return
    
    # Download NLTK data
    download_nltk_data()
    
    # Setup .env file
    setup_env_file()
    
    # Show API instructions
    show_api_instructions()
    
    # Offer to run demo
    run_demo()
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Setup error: {e}")
        print("Please check the error and try again")
