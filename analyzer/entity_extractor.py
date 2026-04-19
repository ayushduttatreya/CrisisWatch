"""AI-powered entity extraction from news headlines."""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

from services.openrouter_client import generate_json, get_client

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Structured entity extraction result."""
    people: List[str]
    countries: List[str]
    organizations: List[str]
    
    def to_dict(self) -> Dict[str, List[str]]:
        return {
            "people": self.people,
            "countries": self.countries,
            "organizations": self.organizations,
        }
    
    def is_empty(self) -> bool:
        return not (self.people or self.countries or self.organizations)


# Common entities for fallback/partial extraction
COMMON_COUNTRIES = {
    "united states", "usa", "us", "america", "american",
    "china", "chinese", "beijing",
    "russia", "russian", "moscow",
    "ukraine", "ukrainian", "kyiv", "kiev",
    "israel", "israeli", "gaza", "palestine", "palestinian",
    "iran", "iranian", "tehran",
    "north korea", "south korea", "korean",
    "india", "indian", "new delhi",
    "pakistan", "pakistani",
    "afghanistan", "afghan",
    "syria", "syrian",
    "iraq", "iraqi",
    "turkey", "turkish", "erdogan",
    "saudi arabia", "saudi",
    "egypt", "egyptian",
    "germany", "german", "berlin",
    "france", "french", "paris",
    "uk", "united kingdom", "britain", "british", "london",
    "italy", "italian", "rome",
    "japan", "japanese", "tokyo",
    "brazil", "brazilian",
    "mexico", "mexican",
    "canada", "canadian",
    "australia", "australian",
    "nato", "european union", "eu", "un", "united nations",
    "taiwan", "taiwanese",
    "venezuela", "venezuelan",
    "myanmar", "burma",
    "yemen", "yemeni",
    "lebanon", "lebanese",
    "jordan", "jordanian",
    "qatar", "qatari",
    "uae", "emirates", "dubai", "abu dhabi",
    "kuwait",
    "bahrain",
    "oman",
    "morocco", "moroccan",
    "algeria", "algerian",
    "tunisia", "tunisian",
    "libya", "libyan",
    "sudan", "sudanese",
    "ethiopia", "ethiopian",
    "somalia", "somali",
    "kenya", "kenyan",
    "nigeria", "nigerian",
    "south africa",
    "argentina", "argentine",
    "chile", "chilean",
    "colombia", "colombian",
    "peru", "peruvian",
    "ecuador", "ecuadorean",
    "bolivia", "bolivian",
    "paraguay", "paraguayan",
    "uruguay", "uruguayan",
    "poland", "polish", "warsaw",
    "ukraine", "ukrainian",
    "romania", "romanian",
    "bulgaria", "bulgarian",
    "hungary", "hungarian",
    "czech republic", "czech",
    "slovakia", "slovak",
    "serbia", "serbian",
    "croatia", "croatian",
    "bosnia",
    "albania", "albanian",
    "greece", "greek", "athens",
    "spain", "spanish", "madrid",
    "portugal", "portuguese",
    "netherlands", "dutch",
    "belgium", "belgian", "brussels",
    "switzerland", "swiss",
    "austria", "austrian", "vienna",
    "sweden", "swedish", "stockholm",
    "norway", "norwegian",
    "denmark", "danish", "copenhagen",
    "finland", "finnish", "helsinki",
    "ireland", "irish", "dublin",
    "estonia", "estonian",
    "latvia", "latvian",
    "lithuania", "lithuanian",
    "belarus", "belarusian",
    "moldova", "moldovan",
    "armenia", "armenian",
    "azerbaijan", "azerbaijani",
    "georgia", "georgian",
    "kazakhstan", "kazakh",
    "uzbekistan", "uzbek",
    "turkmenistan",
    "tajikistan", "tajik",
    "kyrgyzstan", "kyrgyz",
    "mongolia", "mongolian",
    "bangladesh", "bangladeshi",
    "sri lanka", "sri lankan",
    "nepal", "nepalese",
    "bhutan",
    "maldives",
    "thailand", "thai", "bangkok",
    "vietnam", "vietnamese", "hanoi",
    "cambodia", "cambodian",
    "laos", "lao",
    "malaysia", "malaysian", "kuala lumpur",
    "singapore", "singaporean",
    "indonesia", "indonesian", "jakarta",
    "philippines", "philippine", "manila",
    "brunei",
    "east timor", "timor",
    "papua new guinea",
    "fiji",
    "new zealand",
    "solomon islands",
    "vanuatu",
    "samoa",
    "tonga",
    "kiribati",
    "tuvalu",
    "nauru",
    "palau",
    "marshall islands",
    "micronesia",
    "guam",
    "puerto rico",
    "cuba", "cuban", "havana",
    "haiti", "haitian",
    "dominican republic", "dominican",
    "jamaica", "jamaican",
    "trinidad and tobago",
    "barbados",
    "guyana", "guyanese",
    "suriname",
    "french guiana",
    "belize",
    "guatemala", "guatemalan",
    "honduras", "honduran",
    "el salvador", "salvadoran",
    "nicaragua", "nicaraguan",
    "costa rica", "costa rican",
    "panama", "panamanian",
}

COMMON_ORGANIZATIONS = {
    "nato", "nato.",
    "un", "un.", "united nations",
    "eu", "european union",
    "wto", "world trade organization",
    "imf", "international monetary fund",
    "world bank",
    "who", "world health organization",
    "opec",
    "g7", "g20",
    "asean",
    "african union",
    "arab league",
    "mercosur",
    "nafta", "usmca",
    "fed", "federal reserve",
    "ecb", "european central bank",
    "boe", "bank of england",
    "boj", "bank of japan",
    "rbi", "reserve bank of india",
    "sec", "securities and exchange commission",
    "fbi", "cia", "nsa",
    "pentagon", "white house", "congress", "senate", "house",
    "downing street", "parliament",
    "kremlin",
    "google", "alphabet",
    "microsoft",
    "apple",
    "amazon",
    "meta", "facebook",
    "tesla",
    "spacex",
    "twitter", "x corp",
    "netflix",
    "intel",
    "nvidia",
    "amd",
    "ibm",
    "oracle",
    "salesforce",
    "uber", "lyft",
    "airbnb",
    "goldman sachs", "goldman",
    "morgan stanley",
    "jpmorgan", "jp morgan",
    "citi", "citigroup",
    "bank of america", "bofa",
    "wells fargo",
    "deutsche bank",
    "barclays",
    "hsbc",
    "ubs",
    "credit suisse",
    "blackrock",
    "vanguard",
    "fidelity",
    "charles schwab",
    "mcdonald", "mcdonald's",
    "starbucks",
    "coca-cola", "coca cola", "coke",
    "pepsico", "pepsi",
    "walmart",
    "target",
    "costco",
    "home depot",
    "lowe's", "lowes",
    "exxon", "exxonmobil", "exxon mobil",
    "chevron",
    "bp", "british petroleum",
    "shell", "royal dutch shell",
    "total",
    "aramco", "saudi aramco",
    "boeing",
    "airbus",
    "lockheed martin",
    "northrop grumman",
    "raytheon",
    "general dynamics",
    "bae systems",
    "rothschild",
    "roche",
    "novartis",
    "pfizer",
    "moderna",
    "johnson & johnson",
    "astrazeneca",
    "sanofi",
    "merck",
    "bayer",
    "glaxosmithkline", "gsk",
    "toyota",
    "honda",
    "nissan",
    "hyundai",
    "kia",
    "volkswagen", "vw",
    "bmw",
    "mercedes", "mercedes-benz", "mercedes benz",
    "audi",
    "porsche",
    "ferrari",
    "lamborghini",
    "volvo",
    "saab",
    "renault",
    "peugeot",
    "citroen",
    "fiat",
    "chrysler",
    "gm", "general motors",
    "ford",
    "tesla",
    "byd",
    "nio",
    "xiao mi", "xiaomi",
    "alibaba",
    "tencent",
    "baidu",
    "jd.com", "jd",
    "pinduoduo",
    "meituan",
    "didi",
    "huawei",
    "zte",
    "lenovo",
    "samsung",
    "lg",
    "sony",
    "panasonic",
    "toshiba",
    "hitachi",
    "fujitsu",
    "nec",
    "canon",
    "nikon",
    "olympus",
    "seiko",
    "casio",
    "nintendo",
    "softbank",
    "rakuten",
    "line",
    "kakao",
    "naver",
    " Coupang",
    "ola",
    "flipkart",
    "swiggy",
    "zomato",
    "paytm",
    "phonepe",
    "byju's", "byjus",
    "infosys",
    "tcs", "tata consultancy services",
    "wipro",
    "hcl",
    "tech mahindra",
    "lti", "ltimindtree",
    "mindtree",
    "mphasis",
    "cognizant",
    "genpact",
    "wns",
    "exl",
    "firstsource",
    "hexaware",
    "zensar",
    "persistent",
    "cyient",
    "oracle financial services",
    "3i-infotech",
    " Rolta",
    "polaris",
    "niit technologies",
    "mastek",
    "e-clerx",
    "allsec",
    "serco",
    "spanco",
    "aptara",
    "crisil",
    "icra",
    "care ratings",
    "brickwork",
    "smera",
    "onicra",
}


def _fallback_entity_extraction(text: str) -> ExtractedEntities:
    """Fallback extraction using keyword matching."""
    text_lower = text.lower()
    
    countries = []
    orgs = []
    
    for country in COMMON_COUNTRIES:
        if country in text_lower:
            # Avoid duplicates
            normalized = country.replace("united states", "US").replace("usa", "US").replace("america", "US")
            if normalized not in countries:
                countries.append(normalized.title() if len(normalized) > 2 else normalized.upper())
    
    for org in COMMON_ORGANIZATIONS:
        if org in text_lower:
            if org not in orgs:
                orgs.append(org.upper() if len(org) <= 4 else org.title())
    
    return ExtractedEntities(
        people=[],  # People extraction requires more complex NLP
        countries=countries[:10],  # Limit to top matches
        organizations=orgs[:10],
    )


def _build_entity_prompt(headline: str) -> str:
    """Build prompt for entity extraction."""
    prompt = f"""Extract entities from this news headline. Return ONLY a JSON object.

Headline: "{headline}"

Extract:
1. People (politicians, leaders, celebrities mentioned by name)
2. Countries/nations (including alternate names like "US" for "United States")
3. Organizations (companies, government agencies, international bodies, political parties)

Return format:
{{
    "people": ["Name 1", "Name 2"],
    "countries": ["Country 1", "Country 2"],
    "organizations": ["Org 1", "Org 2"]
}}

Rules:
- Use official/common names
- Include full names when known (e.g., "Joe Biden" not just "Biden")
- For organizations, include well-known acronyms when applicable
- If no entities of a type are found, return empty array for that type
- Be precise - only include entities actually mentioned

JSON output:"""
    
    return prompt


async def extract_entities(headline: str, use_fallback: bool = True) -> ExtractedEntities:
    """
    Extract entities from a headline using AI.
    
    Args:
        headline: News headline text
        use_fallback: Use keyword fallback if AI fails
    
    Returns:
        ExtractedEntities object
    """
    if not headline or not isinstance(headline, str):
        return ExtractedEntities(people=[], countries=[], organizations=[])
    
    prompt = _build_entity_prompt(headline)
    
    system_prompt = """You are a precise entity extraction system. Extract only entities explicitly mentioned in the text. Return valid JSON only."""
    
    try:
        result = await generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.1,  # Low temperature for consistent extraction
        )
        
        if result:
            entities = ExtractedEntities(
                people=result.get("people", []) or [],
                countries=result.get("countries", []) or [],
                organizations=result.get("organizations", []) or [],
            )
            
            # If AI returned empty, optionally try fallback
            if entities.is_empty() and use_fallback:
                fallback = _fallback_entity_extraction(headline)
                return fallback
            
            return entities
        
    except Exception as e:
        logger.error(f"Entity extraction failed for '{headline[:50]}...': {e}")
    
    # Fallback
    if use_fallback:
        return _fallback_entity_extraction(headline)
    
    return ExtractedEntities(people=[], countries=[], organizations=[])


async def extract_entities_batch(
    headlines: List[str],
    max_concurrent: int = 5,
) -> List[ExtractedEntities]:
    """
    Extract entities from multiple headlines with concurrency control.
    
    Args:
        headlines: List of headlines to process
        max_concurrent: Maximum concurrent extractions
    
    Returns:
        List of ExtractedEntities
    """
    if not headlines:
        return []
    
    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_with_limit(headline: str) -> ExtractedEntities:
        async with semaphore:
            return await extract_entities(headline)
    
    tasks = [extract_with_limit(h) for h in headlines]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions gracefully
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Batch entity extraction error: {result}")
            processed_results.append(ExtractedEntities(people=[], countries=[], organizations=[]))
        else:
            processed_results.append(result)
    
    return processed_results


def aggregate_entities(
    entities_list: List[ExtractedEntities],
    top_n: int = 10,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Aggregate and rank entities across multiple articles.
    
    Args:
        entities_list: List of extracted entities
        top_n: Number of top entities per category
    
    Returns:
        Dictionary with ranked entities per category
    """
    from collections import Counter
    
    all_people = []
    all_countries = []
    all_orgs = []
    
    for entities in entities_list:
        all_people.extend([p.lower() for p in entities.people])
        all_countries.extend([c.lower() for c in entities.countries])
        all_orgs.extend([o.lower() for o in entities.organizations])
    
    # Count occurrences
    people_counter = Counter(all_people)
    countries_counter = Counter(all_countries)
    orgs_counter = Counter(all_orgs)
    
    # Get top N with counts
    top_people = [
        {"name": name.title(), "mentions": count}
        for name, count in people_counter.most_common(top_n)
    ]
    top_countries = [
        {"name": name.title(), "mentions": count}
        for name, count in countries_counter.most_common(top_n)
    ]
    top_orgs = [
        {"name": name.upper() if len(name) <= 4 else name.title(), "mentions": count}
        for name, count in orgs_counter.most_common(top_n)
    ]
    
    return {
        "people": top_people,
        "countries": top_countries,
        "organizations": top_orgs,
    }
