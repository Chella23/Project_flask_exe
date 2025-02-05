# app/seeds.py

from .models import db, DefaultCategory, DefaultWebsite

def init_default_categories():
    """
    Initializes the default categories and associated websites into the database.
    Only runs if no default category is already present.
    """
    # Check if any default category already exists.
    if DefaultCategory.query.first():
        print("Default categories already initialized.")
        return

    default_data = {
        "Social Media 🟢": [
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
        "Streaming 🎥": [
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
        "Shopping 🛒": [
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
        "News 📰": [
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
        "Gaming 🎮": [
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
        "Education 📚": [
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
        "AI Tools 🤖": [
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
        "Finance 💰": [
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
        "Health 🏥": [
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
        "Productivity 📌": [
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

        # For each website, add both the base URL and a "www" version.
        for name, base_url in websites:
            # Without www
            website1 = DefaultWebsite(
                category_id=category.id,
                name=name,
                url=base_url
            )
            # With www prepended
            website2 = DefaultWebsite(
                category_id=category.id,
                name=f"{name} (www)",
                url=f"www.{base_url}" if not base_url.startswith("www.") else base_url
            )
            db.session.add(website1)
            db.session.add(website2)

    db.session.commit()
    print("Default categories and websites have been initialized.")
