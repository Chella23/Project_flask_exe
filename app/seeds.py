from sqlalchemy import inspect, create_engine
from sqlalchemy.engine.url import make_url
from .models import db, DefaultCategory, DefaultWebsite
import sys

def ensure_database_exists(db_url):
    """
    Checks if the target database exists, and creates it if not.
    """
    try:
        url = make_url(db_url)
        database = url.database
        # Remove the database name from the URL
        url = url.set(database=None)
        engine = create_engine(url)
        with engine.connect() as connection:
            connection.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
        print(f"✅ Database '{database}' exists or has been created successfully.")
    except Exception as e:
        print(f"❌ Error ensuring database exists: {e}")
        sys.exit(1)

def table_exists(table_name):
    """
    Check if a table exists in the database.
    """
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

def create_tables():
    """
    Create tables if they do not exist.
    """
    db.create_all()
    print("✅ All missing tables have been created.")

def init_default_categories():
    """
    Initializes the default categories and associated websites into the database.
    Only runs if no default category is already present.
    """
    if not table_exists("default_categories") or not table_exists("default_websites"):
        print("⚠️ Default tables are missing. Creating tables first...")
        create_tables()

    # Check if default categories already exist
    if DefaultCategory.query.first():
        print("✅ Default categories already exist. Skipping insertion.")
        return

    default_data = {
        "Social Media": [
            ("Facebook", "facebook.com"),
            ("Twitter", "twitter.com"),
            ("Instagram", "instagram.com"),
            ("Snapchat", "snapchat.com"),
            ("TikTok", "tiktok.com"),
            ("Reddit", "reddit.com"),
            ("LinkedIn", "linkedin.com"),
            ("Pinterest", "pinterest.com"),
            ("Quora", "quora.com"),
            ("Tumblr", "tumblr.com")
        ],
        "Streaming": [
            ("YouTube", "youtube.com"),
            ("Netflix", "netflix.com"),
            ("Hulu", "hulu.com"),
            ("Disney+", "disneyplus.com"),
            ("Prime Video", "primevideo.com"),
            ("HBO Max", "hbomax.com"),
            ("Twitch", "twitch.tv"),
            ("Crunchyroll", "crunchyroll.com"),
            ("HBO", "hbo.com"),
            ("Vimeo", "vimeo.com")
        ],
        "Shopping": [
            ("Amazon", "amazon.com"),
            ("eBay", "ebay.com"),
            ("Walmart", "walmart.com"),
            ("AliExpress", "aliexpress.com"),
            ("Etsy", "etsy.com"),
            ("Target", "target.com"),
            ("Flipkart", "flipkart.com"),
            ("BestBuy", "bestbuy.com"),
            ("Zara", "zara.com"),
            ("IKEA", "ikea.com")
        ],
        "News": [
            ("CNN", "cnn.com"),
            ("BBC", "bbc.com"),
            ("NY Times", "nytimes.com"),
            ("Fox News", "foxnews.com"),
            ("The Guardian", "theguardian.com"),
            ("Washington Post", "washingtonpost.com"),
            ("Reuters", "reuters.com"),
            ("Bloomberg", "bloomberg.com"),
            ("Forbes", "forbes.com"),
            ("Time", "time.com")
        ],
        "Gaming": [
            ("Steam", "steampowered.com"),
            ("Epic Games", "epicgames.com"),
            ("Roblox", "roblox.com"),
            ("Minecraft", "minecraft.net"),
            ("PlayStation", "playstation.com"),
            ("Xbox", "xbox.com"),
            ("Nintendo", "nintendo.com"),
            ("Twitch", "twitch.tv"),
            ("Rockstar Games", "rockstargames.com"),
            ("EA", "ea.com")
        ],
        "Education": [
            ("Khan Academy", "khanacademy.org"),
            ("Coursera", "coursera.org"),
            ("Udemy", "udemy.com"),
            ("edX", "edx.org"),
            ("Academia.edu", "academia.edu"),
            ("Duolingo", "duolingo.com"),
            ("MIT", "mit.edu"),
            ("Stanford", "stanford.edu"),
            ("Harvard", "harvard.edu"),
            ("Codecademy", "codecademy.com")
        ],
        "AI Tools": [
            ("ChatGPT", "chat.openai.com"),
            ("Bard", "bard.google.com"),
            ("Hugging Face", "huggingface.co"),
            ("RunwayML", "runwayml.com"),
            ("Midjourney", "midjourney.com"),
            ("Notion AI", "notion.so/ai"),
            ("GitHub Copilot", "github.com/copilot"),
            ("DeepLearning.AI", "deeplearning.ai"),
            ("ElevenLabs", "elevenlabs.io"),
            ("Stability AI", "stability.ai")
        ],
        "Finance": [
            ("PayPal", "paypal.com"),
            ("Stripe", "stripe.com"),
            ("Bank of America", "bankofamerica.com"),
            ("Wells Fargo", "wellsfargo.com"),
            ("Chase", "chase.com"),
            ("HSBC", "hsbc.com"),
            ("Goldman Sachs", "goldmansachs.com"),
            ("Bloomberg", "bloomberg.com"),
            ("Nasdaq", "nasdaq.com"),
            ("Forbes Money", "forbes.com/money")
        ],
        "Health": [
            ("WebMD", "webmd.com"),
            ("Mayo Clinic", "mayoclinic.org"),
            ("Healthline", "healthline.com"),
            ("NIH", "nih.gov"),
            ("WHO", "who.int"),
            ("Cleveland Clinic", "clevelandclinic.org"),
            ("CDC", "cdc.gov"),
            ("Medscape", "medscape.com"),
            ("MedlinePlus", "medlineplus.gov"),
            ("Drugs.com", "drugs.com")
        ],
        "Productivity": [
            ("Notion", "notion.so"),
            ("Trello", "trello.com"),
            ("Asana", "asana.com"),
            ("Monday.com", "monday.com"),
            ("Slack", "slack.com"),
            ("Zoom", "zoom.us"),
            ("Evernote", "evernote.com"),
            ("Google Keep", "googlekeep.com"),
            ("Todoist", "todoist.com"),
            ("ClickUp", "clickup.com")
        ]
    }

    for category_title, websites in default_data.items():
        category = DefaultCategory(title=category_title)
        db.session.add(category)
        db.session.flush()  # Flush to get the new category ID

        # For each website, insert the base URL only if it doesn't already exist.
        for name, base_url in websites:
            existing = DefaultWebsite.query.filter_by(url=base_url).first()
            if not existing:
                website1 = DefaultWebsite(
                    category_id=category.id,
                    name=name,
                    url=base_url
                )
                db.session.add(website1)

    db.session.commit()
    print("Default categories and websites have been initialized.")

def check_and_initialize():
    """
    Ensures all tables exist and inserts default data if needed.
    """
    # Ensure the database exists (pass the SQLALCHEMY_DATABASE_URI from your config)
    from flask import current_app
    db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    ensure_database_exists(db_url)
    create_tables()
    init_default_categories()

def safe_print(s):
    """
    Print text to console, removing or replacing un-encodable characters if needed.
    """
    try:
        print(s)
    except UnicodeEncodeError:
        fallback = s.encode("ascii", "replace").decode("ascii")
        print(fallback)

# Then use safe_print instead of print
safe_print("Operation successful!")
