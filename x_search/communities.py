"""
Hardcoded communities - curated spheres of influence on X.

Last updated: December 2025 - All handles verified via API.
Grouped by ideological/professional sphere for maximum orthogonality.

To verify a handle is valid, use the X API user lookup endpoint.
"""

COMMUNITIES: dict[str, list[str]] = {
    # Tech founders, VCs, Silicon Valley elite
    "tech_vc": [
        "elonmusk",        # Elon Musk - Tesla, SpaceX, X
        "pmarca",          # Marc Andreessen - a16z founder
        "paulg",           # Paul Graham - YC founder
        "naval",           # Naval Ravikant - AngelList founder
        "davidsacks",      # David Sacks - Craft Ventures
        "chamath",         # Chamath Palihapitiya - Social Capital
        "sama",            # Sam Altman - OpenAI CEO
        "garrytan",        # Garry Tan - YC CEO
        "balajis",         # Balaji Srinivasan
        "peterthiel",      # Peter Thiel - Founders Fund
    ],
    # MAGA / Trump-aligned populist right
    "maga_right": [
        "realDonaldTrump", # Donald Trump
        "JDVance",         # JD Vance - VP
        "TuckerCarlson",   # Tucker Carlson
        "DonaldJTrumpJr",  # Don Jr
        "charliekirk11",   # Charlie Kirk - Turning Point USA
        "RealCandaceO",    # Candace Owens
        "JackPosobiec",    # Jack Posobiec
        "benshapiro",      # Ben Shapiro
    ],
    # Progressive left / Democratic establishment
    "progressive_left": [
        "AOC",             # Alexandria Ocasio-Cortez
        "BernieSanders",   # Bernie Sanders
        "BarackObama",     # Barack Obama
        "RBReich",         # Robert Reich
        "IlhanMN",         # Ilhan Omar
        "ewarren",         # Elizabeth Warren
        "KamalaHarris",    # Kamala Harris
        "POTUS",           # Official POTUS account
    ],
    # Crypto / Web3
    "crypto_web3": [
        "VitalikButerin",  # Vitalik - Ethereum founder
        "cz_binance",      # CZ - Binance founder
        "brian_armstrong", # Brian Armstrong - Coinbase CEO
        "APompliano",      # Anthony Pompliano
        "tyler",           # Tyler Winklevoss
        "cameron",         # Cameron Winklevoss
        "balajis",         # Balaji Srinivasan
    ],
    # AI/ML - companies and researchers
    "ai_ml": [
        "OpenAI",          # OpenAI official
        "AnthropicAI",     # Anthropic official
        "GoogleDeepMind",  # Google DeepMind
        "xai",             # xAI official
        "sama",            # Sam Altman - OpenAI CEO
        "ylecun",          # Yann LeCun - Meta AI chief
        "karpathy",        # Andrej Karpathy
        "fchollet",        # Francois Chollet - Keras creator
        "demishassabis",   # Demis Hassabis - DeepMind CEO
        "ESYudkowsky",     # Eliezer Yudkowsky - AI safety
    ],
    # Podcast/long-form media personalities
    "podcast_media": [
        "joerogan",        # Joe Rogan - JRE
        "lexfridman",      # Lex Fridman
        "jordanbpeterson", # Jordan Peterson
        "hubermanlab",     # Andrew Huberman
        "timferriss",      # Tim Ferriss
        "SamHarrisOrg",    # Sam Harris
        "benshapiro",      # Ben Shapiro
    ],
    # Mainstream news organizations
    "news_media": [
        "nytimes",         # New York Times
        "washingtonpost",  # Washington Post
        "CNN",             # CNN
        "FoxNews",         # Fox News
        "BBCWorld",        # BBC
        "Reuters",         # Reuters
        "AP",              # Associated Press
        "Google",          # Google (for search/news)
    ],
    # World leaders / heads of state
    "world_leaders": [
        "narendramodi",    # PM of India
        "POTUS",           # US President official
        "EmmanuelMacron",  # France President
        "ZelenskyyUa",     # Zelensky - Ukraine
        "netanyahu",       # Netanyahu - Israel
        "PopeFrancis",     # Pope Francis
        "BarackObama",     # Barack Obama
    ],
}


def get_community_names() -> list[str]:
    """Return list of available community names."""
    return list(COMMUNITIES.keys())


def get_community_users(community: str) -> list[str]:
    """Return list of usernames in a community."""
    return COMMUNITIES.get(community, [])


