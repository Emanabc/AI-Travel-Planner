# -------- Imports --------
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from scipy.sparse import csr_matrix
import importlib

# Optional TensorFlow ranking model support
TF_AVAILABLE = False
keras = None
try:
    tf = importlib.import_module("tensorflow")
    keras = importlib.import_module("tensorflow.keras")
    TF_AVAILABLE = True
except ImportError:
    tf = None
    keras = None
    

# -------- Constants --------
PREFERENCE_TO_TYPE = {
    "adventure": ["mountain", "valley", "lake", "trek", "camp"],
    "relax": ["hill station", "resort", "beach", "lake", "scenic"],
    "culture": ["heritage", "historical", "museum", "fort", "city"],
}


# -------- Helper Functions --------

# Build a matrix for collaborative filtering from user ratings
def build_user_item_matrix(user_ratings_list):
    """
    Build user-item matrix for collaborative filtering.
    user_ratings_list: list of dicts with 'user_id', 'destination_id', 'rating'
    Returns: cf_matrix (csr_matrix), user_to_idx (dict), dest_to_idx (dict)
    """
    if not user_ratings_list:
        return None, {}, {}
    users = sorted(set(r['user_id'] for r in user_ratings_list))
    destinations = sorted(set(r['destination_id'] for r in user_ratings_list))
    user_to_idx = {u: i for i, u in enumerate(users)}
    dest_to_idx = {d: i for i, d in enumerate(destinations)}
    matrix = np.zeros((len(users), len(destinations)))
    for r in user_ratings_list:
        u_idx = user_to_idx[r['user_id']]
        d_idx = dest_to_idx[r['destination_id']]
        matrix[u_idx, d_idx] = r['rating']
    return csr_matrix(matrix), user_to_idx, dest_to_idx


def get_collaborative_scores(user_id, cf_matrix, user_to_idx, dest_to_idx, candidate_dest_ids, k=5):
    """
    Get collaborative filtering scores for user on candidate destinations.
    Returns dict dest_id -> normalized score (0-1)
    """
    if cf_matrix is None or user_id not in user_to_idx:
        return {dest_id: 0.0 for dest_id in candidate_dest_ids}
    user_idx = user_to_idx[user_id]
    user_vector = cf_matrix[user_idx].toarray().flatten()
    if np.sum(user_vector) == 0:  # cold start
        return {dest_id: 0.0 for dest_id in candidate_dest_ids}
    # user-user CF
    similarities = cosine_similarity([user_vector], cf_matrix).flatten()
    similarities[user_idx] = -1  # exclude self
    top_k_indices = np.argsort(similarities)[-k:]
    cf_scores = {}
    for dest_id in candidate_dest_ids:
        if dest_id not in dest_to_idx:
            cf_scores[dest_id] = 0.0
            continue
        dest_idx = dest_to_idx[dest_id]
        ratings = []
        for u_idx in top_k_indices:
            rating = cf_matrix[u_idx, dest_idx]
            if rating > 0:
                ratings.append(rating)
        cf_scores[dest_id] = np.mean(ratings) / 5.0 if ratings else 0.0
    return cf_scores


# Optional TensorFlow ranking model helper
def build_tf_ranking_model(input_dim):
    if not TF_AVAILABLE:
        return None
    model = keras.Sequential([
        keras.layers.Dense(64, activation='relu', input_shape=(input_dim,)),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dense(1, activation='sigmoid')  # Output score 0-1
    ])
    model.compile(optimizer='adam', loss='mse')
    return model


def get_tf_score(model, features):
    if model is None:
        return 0.0
    features = np.array(features).reshape(1, -1)
    return model.predict(features)[0][0]
# END ADDED FEATURE


def normalize_preference(preference):
    if not preference:
        return ""

    normalized = str(preference).strip().lower()
    if normalized in {"relaxation", "family"}:
        return "relax"
    return normalized


# This function creates text content from destination data for ML processing
def build_content_text(destination):
    parts = [
        str(destination.get("name", "")),
        str(destination.get("type", "")),
        str(destination.get("region", "")),
        str(destination.get("weather", "")),
        str(destination.get("best_season", "")),
        str(destination.get("activities", "")),
        str(destination.get("tags", "")),
    ]
    return " ".join(part for part in parts if part).lower()


# This function trains the ML model with destination data
def train_model(destinations):
    df = pd.DataFrame(destinations).copy()

    if df.empty:
        return df, None

    for column in ("cost", "safety_rating", "user_rating"):
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["content_text"] = df.apply(build_content_text, axis=1)

    vectorizer = TfidfVectorizer(stop_words="english")
    content_matrix = vectorizer.fit_transform(df["content_text"])
    similarity_matrix = cosine_similarity(content_matrix)

    scaler = MinMaxScaler()
    df["normalized_user_rating"] = scaler.fit_transform(df[["user_rating"]]).ravel()

    return df, similarity_matrix


def build_query_text(query_data):
    entities = query_data.get("entities", {})
    preference = normalize_preference(entities.get("preference"))
    preference_terms = " ".join(PREFERENCE_TO_TYPE.get(preference, []))

    parts = [
        query_data.get("intent", ""),
        query_data.get("message", ""),
        entities.get("destination") or "",
        entities.get("region") or "",
        preference,
        preference_terms,
    ]

    return " ".join(part for part in parts if part).lower().strip()


def apply_rule_filters(df, budget=None, region=None, destination=None, destination_aliases=None):
    """
    Apply rule-based filters to destinations.
    Supports budget, region, and destination-based filtering.
    When a destination has aliases (e.g., Islamabad -> Murree, Taxila),
    those are prioritized for location-based filtering.
    """
    filtered_df = df.copy()

    if budget is not None:
        filtered_df = filtered_df[filtered_df["cost"] <= budget]

    # Priority 1: If destination has aliases, use them to filter by keywords
    if destination_aliases:
        alias_filter = filtered_df["name"].astype(str).str.lower().apply(
            lambda name: any(
                alias.lower() in name.lower() or name.lower() in alias.lower()
                for alias in destination_aliases
            )
        )
        filtered_df = filtered_df[alias_filter]
        # If we got results from aliases, return them
        if not filtered_df.empty:
            return filtered_df

    # Priority 2: If region is specified, filter by region
    if region:
        region_filter = filtered_df["region"].astype(str).str.lower() == str(region).lower()
        filtered_df_by_region = filtered_df[region_filter]
        # Only return region-filtered results if they exist
        if not filtered_df_by_region.empty:
            return filtered_df_by_region

    # Priority 3: If destination name is specified, filter by destination name/type keywords
    if destination:
        dest_filter = (
            (filtered_df["name"].astype(str).str.lower().str.contains(destination.lower(), na=False)) |
            (filtered_df["type"].astype(str).str.lower().str.contains(destination.lower(), na=False))
        )
        filtered_df_by_dest = filtered_df[dest_filter]
        if not filtered_df_by_dest.empty:
            return filtered_df_by_dest

    return filtered_df


def top_rated_fallback(df, limit=5):
    if df.empty:
        return []

    results = df.sort_values(by="user_rating", ascending=False).head(limit).copy()
    results["similarity_score"] = 0.0
    results["budget_match"] = 0.0
    results["personal_rating"] = 0.0
    results["collaborative_score"] = 0.0
    results["final_score"] = results["normalized_user_rating"]
    return results.to_dict(orient="records")


def get_recommendations(query_data, df, similarity_matrix, user_ratings=None, limit=5, cf_matrix=None, user_to_idx=None, dest_to_idx=None, user_id=None, destination_aliases_map=None):
    if df.empty:
        return []

    user_ratings = user_ratings or {}
    destination_aliases_map = destination_aliases_map or {}
    entities = query_data.get("entities", {})
    budget = entities.get("budget")
    region = entities.get("region")
    destination = entities.get("destination")
    
    # Get destination aliases if the destination has any
    destination_aliases = None
    if destination:
        # Normalize destination name for alias lookup
        dest_key = destination.lower().replace(" ", "")
        destination_aliases = destination_aliases_map.get(dest_key)

    # Check for "near me" or "nearby" keywords and default to nearby northern areas
    message = query_data.get("message", "").lower()
    nearby_keywords = ["near me", "nearby", "close by", "around", "in my area"]
    is_nearby_query = any(keyword in message for keyword in nearby_keywords)
    
    if is_nearby_query and destination:
        # User is looking for nearby destinations
        # Try to get aliases for the destination (e.g., Islamabad -> Murree, Taxila)
        if not destination_aliases:
            # Fallback: if no exact alias, try to find partial matches
            for key, aliases in destination_aliases_map.items():
                if destination.lower() in key or key in destination.lower():
                    destination_aliases = aliases
                    break

    filtered_df = apply_rule_filters(df, budget=budget, region=region, destination=destination, destination_aliases=destination_aliases)
    if filtered_df.empty:
        return top_rated_fallback(df, limit)

    query_text = build_query_text(query_data)
    if not query_text:
        return top_rated_fallback(filtered_df, limit)

    vectorizer = TfidfVectorizer(stop_words="english")
    content_matrix = vectorizer.fit_transform(df["content_text"])
    query_vector = vectorizer.transform([query_text])
    similarity_scores = cosine_similarity(query_vector, content_matrix).flatten()

    scored_df = filtered_df.copy()
    scored_df["similarity_score"] = scored_df.index.map(lambda idx: float(similarity_scores[idx]))
    scored_df["user_rating_score"] = scored_df["normalized_user_rating"]
    scored_df["budget_match"] = scored_df["cost"].apply(
        lambda value: 1.0 if budget is not None and value <= budget else 0.0
    )
    scored_df["personal_rating"] = scored_df["id"].map(
        lambda destination_id: float(user_ratings.get(destination_id, 0)) / 5.0
    )
    # ADDED CODE
    cf_scores = get_collaborative_scores(user_id, cf_matrix, user_to_idx, dest_to_idx, scored_df["id"].tolist())
    scored_df["collaborative_score"] = scored_df["id"].map(cf_scores)
    # END ADDED CODE
    scored_df["final_score"] = (
        scored_df["similarity_score"]
        + scored_df["user_rating_score"]
        + scored_df["budget_match"]
        + scored_df["personal_rating"]
        + scored_df["collaborative_score"]
    )

    ranked_df = scored_df.sort_values(
        by=["final_score", "user_rating", "safety_rating"],
        ascending=False,
    ).head(limit)

    if ranked_df.empty:
        return top_rated_fallback(df, limit)

    return ranked_df.to_dict(orient="records")
