# ====================================================================
# NLP QUERY PROCESSING MODULE FOR AI TRAVEL PLANNER
# ====================================================================
# Purpose: Natural Language Processing for travel-related user queries
# Features: Intent extraction, entity recognition, preference detection,
#           budget/duration parsing, region matching
# ====================================================================

# -------- Imports --------
import re
from difflib import get_close_matches

import spacy

# -------- Constants --------

# Complete list of Pakistan destinations for entity recognition
PAKISTAN_DESTINATIONS = [
    "hunza",
    "skardu",
    "murree",
    "naran",
    "kaghan",
    "swat",
    "gilgit",
    "lahore",
    "karachi",
    "islamabad",
    "peshawar",
    "quetta",
    "gwadar",
    "fairy meadows",
    "attabad lake",
    "shogran",
    "neelum valley",
    "azad kashmir",
    "chitral",
    "kalash",
    "bahawalpur",
    "multan",
    "taxila",
    "mohenjo daro",
    "ratti gali",
    "rush lake",
    "deosai",
]

# Maps Pakistan regions to their common aliases and destination names
REGION_ALIASES = {
    "Gilgit Baltistan": ["gilgit", "gilgit baltistan", "hunza", "skardu", "deosai"],
    "Khyber Pakhtunkhwa": ["kpk", "khyber pakhtunkhwa", "swat", "naran", "kaghan", "chitral", "kalash"],
    "Punjab": ["punjab", "lahore", "multan", "bahawalpur", "taxila", "murree"],
    "Sindh": ["sindh", "karachi", "mohenjo daro"],
    "Balochistan": ["balochistan", "quetta", "gwadar"],
    "Azad Kashmir": ["azad kashmir", "neelum valley", "ratti gali"],
    "Islamabad Capital Territory": ["islamabad"],
}

# Keywords for detecting travel preference styles (adventure, relaxation, cultural)
PREFERENCE_KEYWORDS = {
    "adventure": ["adventure", "trekking", "hiking", "camping", "rafting", "climbing", "extreme", "outdoor", "mountain", "valley"],
    "relax": ["relax", "relaxing", "relaxation", "honeymoon", "peaceful", "family", "resort", "spa", "beach", "lake", "scenic", "chill"],
    "culture": ["culture", "cultural", "historical", "heritage", "museum", "ancient", "fort", "city", "architecture", "art"],
}

# Keywords for detecting user query intent (planning, recommendation, search)
INTENT_KEYWORDS = {
    "travel_planning": ["plan", "itinerary", "trip", "tour", "travel", "schedule", "book", "arrange"],
    "recommendation": ["recommend", "suggest", "best", "ideal", "top", "good", "great"],
    "search": ["search", "find", "look for", "show me", "explore", "where", "what"],
}

# ====================================================================
# AI MODULE FUNCTIONS - SPACY NLP MODEL MANAGEMENT
# ====================================================================

def load_nlp_model():
    
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        # Fallback to blank model if trained model not available
        return spacy.blank("en")


# Global NLP model instance used across all extraction functions
nlp = load_nlp_model()


# ====================================================================
# HELPER FUNCTIONS - DURATION & UNIT CONVERSION
# ====================================================================

def convert_duration_to_days(number, unit):
   
    if unit in {"week", "weeks"}:
        return number * 7
    if unit in {"month", "months"}:
        return number * 30
    return number


# ====================================================================
# EXTRACTION FUNCTIONS - INTENT DETECTION
# ====================================================================

def extract_intent(text):
    
    lowered_text = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in lowered_text for keyword in keywords):
            return intent
    return "search"


# ====================================================================
# EXTRACTION FUNCTIONS - DESTINATION DETECTION
# ====================================================================

def extract_destination(text, doc):
   
    # Strategy 1: Use spaCy Named Entity Recognition
    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            return ent.text.strip()

    # Strategy 2: Exact keyword match against known destinations
    lowered_text = text.lower()
    for destination in sorted(PAKISTAN_DESTINATIONS, key=len, reverse=True):
        if destination in lowered_text:
            return destination.title()

    # Strategy 3: Fuzzy matching for typos/alternate spellings
    close_matches = get_close_matches(lowered_text, PAKISTAN_DESTINATIONS, n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0].title()

    return None


# ====================================================================
# EXTRACTION FUNCTIONS - BUDGET DETECTION
# ====================================================================

def extract_budget(text):
   
    lowered_text = text.lower()
    
    # Strategy 1: Try to extract spaCy MONEY entities
    for ent in nlp(text).ents:
        if ent.label_ == "MONEY":
            num_match = re.search(r"([0-9,]+)", ent.text)
            if num_match:
                return int(num_match.group(1).replace(",", ""))
    
    # Strategy 2: Regex patterns for various budget formats
    patterns = [
        r"(?:pkr|rs\.?|rupees?)\s*([0-9,]+)",      # Currency prefix format
        r"([0-9,]+)\s*(?:pkr|rs\.?|rupees?)",      # Currency suffix format
        r"(?:under|within|budget|max(?:imum)?)\s*([0-9,]+)",  # Budget constraint format
    ]

    for pattern in patterns:
        match = re.search(pattern, lowered_text)
        if match:
            return int(match.group(1).replace(",", ""))

    # Strategy 3: Heuristic budget estimates from keywords
    if "cheap" in lowered_text or "budget" in lowered_text:
        return 50000  # Estimated minimum budget
    if "expensive" in lowered_text or "luxury" in lowered_text:
        return 200000  # Estimated premium budget

    return None


# ====================================================================
# EXTRACTION FUNCTIONS - DURATION DETECTION
# ====================================================================

def extract_duration(text):
    
    
    doc = nlp(text)
    for token in doc:
        if token.like_num:  # Token is a number
            num = int(token.text)
            # Look ahead up to 2 tokens for time unit
            for i in range(1, 3):
                if token.i + i < len(doc):
                    next_token = doc[token.i + i]
                    unit = next_token.text.lower()
                    if unit in ["day", "days", "night", "nights"]:
                        return num
                    elif unit in ["week", "weeks", "month", "months"]:
                        return convert_duration_to_days(num, unit)
    
    # Strategy 2: Regex pattern matching for various duration formats
    lowered_text = text.lower()
    match = re.search(r"(\d+)\s*(day|days|night|nights|week|weeks|month|months)", lowered_text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        return convert_duration_to_days(num, unit)
    
    return None


# ====================================================================
# EXTRACTION FUNCTIONS - PREFERENCE DETECTION
# ====================================================================

def extract_preference(text):
   
    lowered_text = text.lower()
    # Initialize scores for all preference types
    scores = {preference: 0 for preference in PREFERENCE_KEYWORDS}

    # Count keyword matches for each preference type
    for preference, keywords in PREFERENCE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered_text:
                scores[preference] += 1

    # Select preference with highest score
    best_preference = max(scores, key=scores.get)
    # Return preference only if it has at least one keyword match
    return best_preference if scores[best_preference] > 0 else None


# ====================================================================
# EXTRACTION FUNCTIONS - REGION DETECTION
# ====================================================================

def extract_region(text):
   
    lowered_text = text.lower()
    for region, aliases in REGION_ALIASES.items():
        if any(alias in lowered_text for alias in aliases):
            return region
    return None


# ====================================================================
# MAIN QUERY PROCESSING FUNCTION
# ====================================================================
def extract_destination(text, doc):
    # Strategy 1: Use spaCy Named Entity Recognition
    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            return ent.text.strip()

    # Strategy 2: Exact keyword match against known destinations
    lowered_text = text.lower()
    for destination in sorted(PAKISTAN_DESTINATIONS, key=len, reverse=True):
        if destination in lowered_text:
            return destination.title()

    # Strategy 3: Fuzzy matching for typos/alternate spellings
    close_matches = get_close_matches(lowered_text, PAKISTAN_DESTINATIONS, n=1, cutoff=0.6)
    if close_matches:
        return close_matches[0].title()

    return None


def extract_budget(text):
    lowered_text = text.lower()
    
    # Strategy 1: Try to extract spaCy MONEY entities
    for ent in nlp(text).ents:
        if ent.label_ == "MONEY":
            num_match = re.search(r"([0-9,]+)", ent.text)
            if num_match:
                return int(num_match.group(1).replace(",", ""))
    
    # Strategy 2: Regex patterns for various budget formats
    patterns = [
        r"(?:pkr|rs\.?|rupees?)\s*([0-9,]+)",      # Currency prefix format
        r"([0-9,]+)\s*(?:pkr|rs\.?|rupees?)",      # Currency suffix format
        r"(?:under|within|budget|max(?:imum)?)\s*([0-9,]+)",  # Budget constraint format
    ]

    for pattern in patterns:
        match = re.search(pattern, lowered_text)
        if match:
            return int(match.group(1).replace(",", ""))

    # Strategy 3: Heuristic budget estimates from keywords
    if "cheap" in lowered_text or "budget" in lowered_text:
        return 50000  # Estimated minimum budget
    if "expensive" in lowered_text or "luxury" in lowered_text:
        return 200000  # Estimated premium budget

    return None


def extract_duration(text):
    # Strategy 1: spaCy tokenization with lookahead for time units
    doc = nlp(text)
    for token in doc:
        if token.like_num:  # Token is a number
            num = int(token.text)
            # Look ahead up to 2 tokens for time unit
            for i in range(1, 3):
                if token.i + i < len(doc):
                    next_token = doc[token.i + i]
                    unit = next_token.text.lower()
                    if unit in ["day", "days", "night", "nights"]:
                        return num
                    elif unit in ["week", "weeks", "month", "months"]:
                        return convert_duration_to_days(num, unit)
    
    # Strategy 2: Regex pattern matching for various duration formats
    lowered_text = text.lower()
    match = re.search(r"(\d+)\s*(day|days|night|nights|week|weeks|month|months)", lowered_text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        return convert_duration_to_days(num, unit)
    
    return None


def extract_preference(text):
    lowered_text = text.lower()
    # Initialize scores for all preference types
    scores = {preference: 0 for preference in PREFERENCE_KEYWORDS}

    # Count keyword matches for each preference type
    for preference, keywords in PREFERENCE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered_text:
                scores[preference] += 1

    # Select preference with highest score
    best_preference = max(scores, key=scores.get)
    # Return preference only if it has at least one keyword match
    return best_preference if scores[best_preference] > 0 else None


def extract_region(text):
    lowered_text = text.lower()
    for region, aliases in REGION_ALIASES.items():
        if any(alias in lowered_text for alias in aliases):
            return region
    return None


def process_query(text):
    """
    Main NLP entry point. Returns:
    {
        "intent": str,
        "entities": {
            "destination": str|None,
            "location": str|None,
            "budget": int|None,
            "duration": int|None,
            "preference": str|None,
            "region": str|None,
        }
    }
    """
    text = (text or "").strip()
    doc = nlp(text)
    lowered_text = text.lower()

    intent = extract_intent(text)
    destination = extract_destination(text, doc)
    region = extract_region(text)
    budget = extract_budget(text)
    duration = extract_duration(text)
    preference = extract_preference(text)

    # Fallback 1: additional spaCy entity types
    if not destination:
        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC", "FAC"}:
                destination = ent.text.strip()
                break

    # Fallback 2: compact duration formats like "3-day"
    if duration is None:
        duration_match = re.search(
            r"\b(\d+)\s*[-]?\s*(day|days|night|nights|week|weeks|month|months)\b",
            lowered_text,
        )
        if duration_match:
            count = int(duration_match.group(1))
            unit = duration_match.group(2)
            duration = convert_duration_to_days(count, unit)

    # Fallback 3: lemmatization-based preference
    if preference is None:
        lemma_tokens = {token.lemma_.lower() for token in doc if token.is_alpha}
        for pref_name, keywords in PREFERENCE_KEYWORDS.items():
            if any(keyword in lowered_text or keyword in lemma_tokens for keyword in keywords):
                preference = pref_name
                break

    location = destination or region

    return {
        "intent": intent,
        "entities": {
            "destination": destination,
            "location": location,
            "budget": budget,
            "duration": duration,
            "preference": preference,
            "region": region,
        },
    }


