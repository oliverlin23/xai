"""
X Communities / Spheres of Influence

This module defines curated spheres of influence on X, organized by ideological
alignment, worldview, and shared discourse patterns. These spheres represent
clusters of accounts and conversations that tend to:
- Share similar perspectives and takes on current events
- Engage with and amplify each other
- Appeal to overlapping audiences
- Use distinctive language and framing

Use these sphere descriptions for semantic filtering when searching for
sentiment on prediction market questions.

Last updated: December 2025
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# =============================================================================
# SPHERE DATA MODEL
# =============================================================================

@dataclass
class Sphere:
    """
    A sphere of influence on X.
    
    Attributes:
        key: Unique identifier for the sphere
        name: Human-readable name
        vibe: Overall tone and character of the sphere
        followers: Types of people who participate in this sphere
        core_beliefs: Foundational beliefs that unite the sphere
    """
    key: str
    name: str
    vibe: str
    followers: str
    core_beliefs: str
    
    def to_prompt_description(self) -> str:
        """Generate a description suitable for LLM prompts."""
        return f"""**{self.name}**
Vibe: {self.vibe}
Typical participants: {self.followers}
Core beliefs: {self.core_beliefs}"""
    
    def to_search_context(self) -> str:
        """Generate context for semantic search filtering."""
        return f"{self.name}: {self.vibe} Participants include {self.followers.lower()}. They believe: {self.core_beliefs}"


# =============================================================================
# SPHERE DEFINITIONS
# =============================================================================

SPHERES: dict[str, Sphere] = {
    # -------------------------------------------------------------------------
    # e/acc & SOVEREIGN INDIVIDUAL
    # -------------------------------------------------------------------------
    "eacc_sovereign": Sphere(
        key="eacc_sovereign",
        name='The "e/acc" & Sovereign Individual Sphere',
        vibe=(
            "Techno-optimist, libertarian, and high-agency. This sphere believes "
            "that technology—not politics—is the solution to humanity's problems. "
            "They adhere to 'effective accelerationism' (e/acc), believing we should "
            "rush toward the technological singularity (AI, Mars, longevity) as fast "
            "as possible."
        ),
        followers=(
            "Venture capitalists, startup founders, crypto whales, and Silicon "
            "Valley engineers."
        ),
        core_beliefs=(
            "The 'Woke Mind Virus' destroys civilizations; the state is incompetent "
            "while meritocracy is paramount; and 'exit' (leaving failing jurisdictions) "
            "is always superior to 'voice' (voting)."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # AMERICA FIRST & RIGHT WING
    # -------------------------------------------------------------------------
    "america_first": Sphere(
        key="america_first",
        name='The "America First" & Right Wing Sphere',
        vibe=(
            "Nationalist, populist, and anti-establishment. This sphere is deeply "
            "suspicious of global institutions, legacy media, and 'the deep state.' "
            "The tone is often combative, focused on culture war battles and preserving "
            "traditional values against perceived moral decay."
        ),
        followers=(
            "The MAGA base, rural working class, religious conservatives, and "
            "anti-institutionalists."
        ),
        core_beliefs=(
            "Borders must be sealed; the 2020 election was irregular; mainstream "
            "media is 'fake news'; and 'globalists' are actively undermining "
            "national sovereignty."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # BLUE ESTABLISHMENT
    # -------------------------------------------------------------------------
    "blue_establishment": Sphere(
        key="blue_establishment",
        name='The "Blue No Matter Who" Establishment Sphere',
        vibe=(
            "Institutionalist, credentialist, and decorum-focused. This sphere "
            "values norms, experts, and the 'rules-based international order.' "
            "They consume legacy media (NYT, CNN) and view politics as a battle "
            "between competent professionals and dangerous disruptors."
        ),
        followers=(
            "Coastal professionals, suburban moderates, policy wonks, and legacy "
            "media consumers."
        ),
        core_beliefs=(
            "Democracy is under threat; we must trust the science; institutions "
            "can be reformed from within; and civility in politics is essential."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # PROGRESSIVE & LABOR LEFT
    # -------------------------------------------------------------------------
    "progressive_left": Sphere(
        key="progressive_left",
        name="The Progressive & Labor Left Sphere",
        vibe=(
            "Systemic critique, activist, and egalitarian. This sphere views the "
            "world through the lens of power dynamics, wealth inequality, and social "
            "justice. They are often as critical of the Democratic establishment "
            "(for being too corporate) as they are of the Right."
        ),
        followers=(
            "Young urbanites, union organizers, academics, and social justice activists."
        ),
        core_beliefs=(
            "Billionaires should not exist; healthcare is a human right; climate "
            "change requires radical action like the Green New Deal; and capitalism "
            "is the root of most societal ills."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # OPTIMIZER & IDW (INTELLECTUAL DARK WEB)
    # -------------------------------------------------------------------------
    "optimizer_idw": Sphere(
        key="optimizer_idw",
        name='The "Optimizer" & IDW (Intellectual Dark Web) Sphere',
        vibe=(
            "Masculine, stoic, and 'heterodox.' This sphere revolves around "
            "self-improvement, physical fitness, and long-form conversation "
            "(3+ hour podcasts). They value 'first principles' thinking and are "
            "skeptical of both mainstream narratives and 'cancel culture.'"
        ),
        followers=(
            "Men aged 18-45 interested in bio-hacking, MMA, evolutionary psychology, "
            "and financial independence."
        ),
        core_beliefs=(
            "Personal responsibility trumps victimhood; physical strength equals "
            "mental strength; and free speech is absolute, even for controversial ideas."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # FINTWIT & MARKET
    # -------------------------------------------------------------------------
    "fintwit_market": Sphere(
        key="fintwit_market",
        name='The "FinTwit" & Market Sphere',
        vibe=(
            "Cynical, data-obsessed, and high-risk/high-reward. This sphere treats "
            "the entire world as a trade. They oscillate between extreme nihilism "
            "('the fiat system is collapsing') and extreme euphoria ('we are going "
            "to the moon'). They speak a language of charts, tickers, and Fed liquidity."
        ),
        followers=(
            "Day traders, crypto hodlers, macro-economists, and finance professionals."
        ),
        core_beliefs=(
            "The Federal Reserve manipulates markets; 'Cash is trash'; ignore what "
            "politicians say and watch where the money flows; and volatility is an "
            "opportunity, not a risk."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # BUILDER & ENGINEERING
    # -------------------------------------------------------------------------
    "builder_engineering": Sphere(
        key="builder_engineering",
        name='The "Builder" & Engineering Sphere',
        vibe=(
            "Pragmatic, technical, and solution-oriented. Unlike the 'e/acc' sphere "
            "which talks about tech philosophy, this sphere talks about code. They "
            "care about shipping products, learning new frameworks, and debugging. "
            "They generally dislike politics because it distracts from building."
        ),
        followers=(
            "Software engineers, indie hackers, open-source maintainers, and "
            "product designers."
        ),
        core_beliefs=(
            "Talk is cheap, show me the code; 'shipping' solves all problems; open "
            "source is a public good; and complexity is the enemy of execution."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # GLOBAL LAB MEETING (ACADEMIC)
    # -------------------------------------------------------------------------
    "academic_research": Sphere(
        key="academic_research",
        name='The "Global Lab Meeting" (Academic) Sphere',
        vibe=(
            "Pedantic, citation-heavy, and fiercely analytical. This sphere operates "
            "like a massive, global peer-review session. Arguments are won with data "
            "sets and historical precedents. It transforms based on the crisis: during "
            "COVID it was 'MedTwit,' during inflation it becomes 'EconTwit.'"
        ),
        followers=(
            "Professors, scientists, doctors, and data journalists."
        ),
        core_beliefs=(
            "Anecdotes are not data; correlation is not causation; policy should be "
            "evidence-based; and expertise matters more than opinion."
        ),
    ),
    
    # -------------------------------------------------------------------------
    # OSINT & INTEL
    # -------------------------------------------------------------------------
    "osint_intel": Sphere(
        key="osint_intel",
        name="The OSINT & Intel Sphere",
        vibe=(
            "Detached, observant, and forensic. This sphere focuses on 'Open Source "
            "Intelligence'—using satellite imagery, flight tracking, and raw footage "
            "to verify what is actually happening in war zones and geopolitical "
            "hotspots. They often debunk mainstream reporting in real-time."
        ),
        followers=(
            "Intelligence analysts, military enthusiasts, cybersecurity experts, "
            "and conflict watchers."
        ),
        core_beliefs=(
            "Trust, but verify; the truth is found in raw metadata, not press "
            "releases; and information warfare is as important as kinetic warfare."
        ),
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_sphere_names() -> list[str]:
    """Return list of available sphere keys."""
    return list(SPHERES.keys())


def get_sphere(sphere_key: str) -> Optional[Sphere]:
    """
    Return a sphere by its key.
    
    Args:
        sphere_key: Sphere key (e.g., "eacc_sovereign", "fintwit_market")
        
    Returns:
        Sphere object, or None if not found
    """
    return SPHERES.get(sphere_key)


def get_all_spheres() -> list[Sphere]:
    """Return list of all sphere objects."""
    return list(SPHERES.values())


def get_sphere_description(sphere_key: str) -> str:
    """
    Return the full prompt description for a sphere.
    
    Args:
        sphere_key: Sphere key
        
    Returns:
        Formatted description suitable for LLM prompts
    """
    sphere = SPHERES.get(sphere_key)
    if sphere is None:
        return "Unknown sphere"
    return sphere.to_prompt_description()


def get_all_spheres_context() -> str:
    """
    Generate a combined context string describing all spheres.
    
    Useful for providing an LLM with the full landscape of X discourse.
    """
    descriptions = []
    for sphere in SPHERES.values():
        descriptions.append(sphere.to_prompt_description())
    return "\n\n".join(descriptions)


def get_opposing_spheres(sphere_key: str) -> list[str]:
    """
    Return spheres that typically hold opposing views.
    
    Useful for getting contrarian perspectives on a topic.
    
    Args:
        sphere_key: Sphere key
        
    Returns:
        List of opposing sphere keys
    """
    oppositions = {
        "eacc_sovereign": ["progressive_left", "blue_establishment"],
        "america_first": ["progressive_left", "blue_establishment"],
        "blue_establishment": ["america_first", "eacc_sovereign"],
        "progressive_left": ["america_first", "eacc_sovereign", "fintwit_market"],
        "optimizer_idw": ["blue_establishment", "progressive_left"],
        "fintwit_market": ["progressive_left"],  # Often at odds on regulation
        "builder_engineering": [],  # Generally apolitical
        "academic_research": ["america_first"],  # Expertise vs populism tension
        "osint_intel": [],  # Facts-focused, less ideological
    }
    return oppositions.get(sphere_key, [])


def get_spheres_for_topic(topic: str) -> list[str]:
    """
    Suggest relevant spheres based on a topic.
    
    Args:
        topic: A topic or question (e.g., "bitcoin price", "election results")
        
    Returns:
        List of sphere keys likely to have opinions on this topic
    """
    topic_lower = topic.lower()
    
    # Topic-to-sphere mappings
    mappings = {
        # Financial/Economic
        ("bitcoin", "crypto", "ethereum", "defi", "nft"): ["fintwit_market", "eacc_sovereign"],
        ("stock", "market", "fed", "inflation", "interest rate", "recession"): ["fintwit_market", "academic_research"],
        ("trade", "tariff", "economy"): ["fintwit_market", "america_first", "progressive_left"],
        
        # Tech
        ("ai", "artificial intelligence", "gpt", "llm", "openai", "anthropic"): ["eacc_sovereign", "builder_engineering", "academic_research"],
        ("startup", "venture", "vc", "funding"): ["eacc_sovereign", "builder_engineering"],
        ("open source", "github", "code", "programming"): ["builder_engineering"],
        
        # Politics
        ("trump", "maga", "republican", "gop"): ["america_first", "blue_establishment", "progressive_left"],
        ("biden", "democrat", "dnc"): ["blue_establishment", "america_first", "progressive_left"],
        ("election", "vote", "ballot"): ["america_first", "blue_establishment", "osint_intel"],
        ("immigration", "border", "migrant"): ["america_first", "progressive_left", "blue_establishment"],
        
        # Geopolitics
        ("ukraine", "russia", "war", "nato"): ["osint_intel", "america_first", "blue_establishment"],
        ("china", "taiwan", "ccp"): ["osint_intel", "america_first", "eacc_sovereign"],
        ("israel", "gaza", "palestine", "hamas"): ["osint_intel", "progressive_left", "america_first"],
        
        # Social
        ("climate", "environment", "green"): ["progressive_left", "academic_research", "eacc_sovereign"],
        ("healthcare", "medicare", "insurance"): ["progressive_left", "blue_establishment"],
        ("union", "labor", "worker", "strike"): ["progressive_left"],
        
        # Culture/Media
        ("podcast", "joe rogan", "lex fridman"): ["optimizer_idw"],
        ("fitness", "health", "biohacking"): ["optimizer_idw", "eacc_sovereign"],
        ("media", "journalism", "news"): ["osint_intel", "america_first", "blue_establishment"],
    }
    
    relevant = set()
    for keywords, spheres in mappings.items():
        if any(kw in topic_lower for kw in keywords):
            relevant.update(spheres)
    
    # If no matches, return a diverse default set
    if not relevant:
        return ["fintwit_market", "blue_establishment", "america_first", "academic_research"]
    
    return list(relevant)


# =============================================================================
# LEGACY COMPATIBILITY
# Preserved for backwards compatibility during migration
# =============================================================================

def get_community_names() -> list[str]:
    """DEPRECATED: Use get_sphere_names() instead."""
    return get_sphere_names()


def get_community_description(community: str) -> str:
    """DEPRECATED: Use get_sphere_description() instead."""
    return get_sphere_description(community)


# =============================================================================
# SPHERE METADATA (for UI/documentation)
# =============================================================================

SPHERE_SUMMARIES: dict[str, str] = {
    "eacc_sovereign": "Techno-optimist VCs, e/acc, libertarian tech elite",
    "america_first": "MAGA populists, nationalist right, anti-establishment",
    "blue_establishment": "Mainstream Democrats, institutionalists, legacy media",
    "progressive_left": "Democratic socialists, labor activists, systemic critics",
    "optimizer_idw": "Self-improvement bros, long-form podcasts, heterodox thinkers",
    "fintwit_market": "Traders, macro analysts, market cynics",
    "builder_engineering": "Software engineers, indie hackers, shippers",
    "academic_research": "Scientists, professors, evidence-based policy advocates",
    "osint_intel": "Intelligence analysts, OSINT investigators, geopolitical watchers",
}


def get_sphere_summary(sphere_key: str) -> str:
    """Return a brief one-line summary of a sphere."""
    return SPHERE_SUMMARIES.get(sphere_key, "Unknown sphere")
