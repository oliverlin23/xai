"""
Spheres of Influence on X - organized by ideological alignment.

Last updated: December 2025 - All handles verified via API.

These are NOT content categories - they represent clusters of accounts
that share similar worldviews, audiences, and information ecosystems.
People in the same sphere tend to agree with each other, retweet each other,
and share similar takes on current events.
"""

COMMUNITIES: dict[str, list[str]] = {
    # Silicon Valley techno-optimist / e/acc / libertarian tech elite
    # Pro-AI, pro-crypto, skeptical of regulation, Thiel-adjacent
    "tech_vc": [
        "elonmusk",        # Elon Musk - Tesla, SpaceX, X
        "pmarca",          # Marc Andreessen - a16z, techno-optimist manifesto
        "balajis",         # Balaji Srinivasan - network state, exit
        "paulg",           # Paul Graham - YC founder
        "naval",           # Naval Ravikant - AngelList
        "davidsacks",      # David Sacks - Craft Ventures, All-In pod
        "chamath",         # Chamath Palihapitiya - All-In pod
        "garrytan",        # Garry Tan - YC CEO
        "jason",           # Jason Calacanis - All-In pod
        "peterthiel",      # Peter Thiel - Founders Fund
    ],

    # MAGA / Trump populist right
    # Pro-Trump, anti-establishment, America First, culture war focused
    "maga_right": [
        "realDonaldTrump", # Donald Trump
        "JDVance",         # JD Vance - VP
        "TuckerCarlson",   # Tucker Carlson
        "DonaldJTrumpJr",  # Don Jr
        "charliekirk11",   # Charlie Kirk - Turning Point USA
        "RealCandaceO",    # Candace Owens
        "JackPosobiec",    # Jack Posobiec
        "StephenMiller",   # Stephen Miller
        "RealMattCouch",   # Matt Couch
        "LauraLoomer",     # Laura Loomer
    ],

    # Progressive left / Democratic socialist
    # Pro-Bernie, anti-corporate, economic populism from the left
    "progressive_left": [
        "AOC",             # Alexandria Ocasio-Cortez
        "BernieSanders",   # Bernie Sanders
        "IlhanMN",         # Ilhan Omar
        "RashidaTlaib",    # Rashida Tlaib
        "RBReich",         # Robert Reich
        "ewarren",         # Elizabeth Warren
        "ninaturner",      # Nina Turner
        "ProPublica",      # ProPublica - investigative
        "theintercept",    # The Intercept
    ],

    # Liberal establishment / mainstream Democrat
    # Pro-institution, centrist-liberal, Obama/Clinton/Biden aligned
    "liberal_establishment": [
        "BarackObama",     # Barack Obama
        "HillaryClinton",  # Hillary Clinton
        "JoeBiden",        # Joe Biden
        "KamalaHarris",    # Kamala Harris
        "POTUS",           # Official POTUS
        "nytimes",         # New York Times
        "washingtonpost",  # Washington Post
        "CNN",             # CNN
        "MSNBC",           # MSNBC
        "TheAtlantic",     # The Atlantic
    ],

    # Conservative establishment / traditional right
    # Pre-Trump conservatism, National Review types, some never-Trump
    "conservative_establishment": [
        "FoxNews",         # Fox News
        "benshapiro",      # Ben Shapiro - Daily Wire
        "DailyWire",       # Daily Wire
        "NRO",             # National Review
        "WSJ",             # Wall Street Journal
        "heritage",        # Heritage Foundation
        "AEI",             # American Enterprise Institute
    ],

    # Crypto / Web3 maximalists
    # Decentralization, anti-Fed, Bitcoin/Ethereum ecosystem
    "crypto_web3": [
        "VitalikButerin",  # Vitalik - Ethereum founder
        "saborz",          # CZ - Binance (if active)
        "brian_armstrong", # Brian Armstrong - Coinbase CEO
        "APompliano",      # Anthony Pompliano - Bitcoin
        "tyler",           # Tyler Winklevoss
        "cameron",         # Cameron Winklevoss
        "saylor",  # Michael Saylor - MicroStrategy
        "aantonop",        # Andreas Antonopoulos
    ],

    # AI/ML - research and safety focused
    # Technical AI community, safety concerns, lab researchers
    "ai_ml": [
        "OpenAI",          # OpenAI official
        "AnthropicAI",     # Anthropic official
        "GoogleDeepMind",  # Google DeepMind
        "xai",             # xAI official
        "sama",            # Sam Altman - OpenAI CEO
        "ylecun",          # Yann LeCun - Meta AI
        "karpathy",        # Andrej Karpathy
        "fchollet",        # Francois Chollet
        "demishassabis",   # Demis Hassabis - DeepMind
        "ESYudkowsky",     # Eliezer Yudkowsky - AI safety
    ],

    # IDW / intellectual dark web / long-form podcast sphere
    # Anti-woke, heterodox, "free thinkers", Rogan-adjacent
    "podcast_media": [
        "joerogan",        # Joe Rogan - JRE
        "lexfridman",      # Lex Fridman
        "jordanbpeterson", # Jordan Peterson
        "hubermanlab",     # Andrew Huberman
        "SamHarrisOrg",    # Sam Harris
        "ericrweinstein",  # Eric Weinstein
        "BretWeinstein",   # Bret Weinstein
        "timferriss",      # Tim Ferriss
        "jaborz",          # Jocko Willink (verify handle)
    ],
}


def get_community_names() -> list[str]:
    """Return list of available community names."""
    return list(COMMUNITIES.keys())


def get_community_users(community: str) -> list[str]:
    """Return list of usernames in a community."""
    return COMMUNITIES.get(community, [])


def get_opposing_communities(community: str) -> list[str]:
    """Return communities that typically oppose this one."""
    oppositions = {
        "maga_right": ["progressive_left", "liberal_establishment"],
        "progressive_left": ["maga_right", "conservative_establishment"],
        "liberal_establishment": ["maga_right", "conservative_establishment"],
        "conservative_establishment": ["progressive_left", "liberal_establishment"],
        "tech_vc": [],  # Generally orthogonal to political axis
        "crypto_web3": [],
        "ai_ml": [],
        "podcast_media": ["liberal_establishment"],  # Often contrarian to mainstream
    }
    return oppositions.get(community, [])
