# This function generates a day-by-day itinerary based on trip duration and user preference
def generate_itinerary(days, preference):
    if days <= 0:
        raise ValueError("days must be greater than 0")

    preference = (preference or "general").strip().lower()

    activity_map = {
    "adventure": "Hiking, trekking, and outdoor exploration tours",
    "relaxation": "Leisure sightseeing, resort stays, and calm evening retreats",
    "culture": "Museum visits, heritage landmarks, and cultural experiences",
    "family": "Family-friendly parks, sightseeing, and entertainment activities",
    "general": "Local sightseeing and balanced city exploration"
}
    selected_activity = activity_map.get(preference, activity_map["general"])
    itinerary = []

    for day in range(1, days + 1):
        if day == 1:
            # # ADDED FEATURE: Time slots and distance-aware scheduling
            activities = [
                {"time": "Morning", "activity": "Arrival and Hotel Check-in", "location": "Hotel"},
                {"time": "Afternoon", "activity": "Local Visit", "location": "Nearby Attraction"},
                {"time": "Evening", "activity": "Dinner and Rest", "location": "Restaurant"}
            ]
        else:
            activities = [
                {"time": "Morning", "activity": selected_activity, "location": "Main Attraction"},
                {"time": "Afternoon", "activity": "Local food experience", "location": "Restaurant"},
                {"time": "Evening", "activity": "Evening rest", "location": "Hotel"}
            ]
        itinerary.append({
            "day": f"Day {day}",
            "activities": activities
        })

    return itinerary