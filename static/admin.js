// -------------------------
// Admin Dashboard
// -------------------------

// Load dashboard statistics for admin dashboard
async function loadStats() {
    if (!el("statsData")) return;

    try {
        const data = await apiFetch("/admin/user-activity");

        el("statsData").innerHTML = `
            <div class="stats-item">
                <span class="stats-label">Users</span>
                <span class="stats-value">${data.total_users ?? 0}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">Ratings</span>
                <span class="stats-value">${data.total_ratings ?? 0}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">Feedback</span>
                <span class="stats-value">${data.total_feedback ?? 0}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">Models</span>
                <span class="stats-value">${data.total_models ?? 0}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">Restaurants</span>
                <span class="stats-value">${data.total_restaurants ?? 0}</span>
            </div>
            <div class="stats-item">
                <span class="stats-label">Events</span>
                <span class="stats-value">${data.total_events ?? 0}</span>
            </div>
        `;
    } catch (error) {
        el("statsData").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Loads admin feedback records.
async function loadFeedback() {
    if (!el("feedbackData")) return;

    try {
        const data = await apiFetch("/admin/feedback");

        el("feedbackData").innerHTML = (data || []).length
            ? data.map((item) => `
                <div class="feedback-box">
                    <strong>${escapeHtml(item.name)}</strong> (${escapeHtml(item.email)})
                    <p>${escapeHtml(item.message)}</p>
                </div>
            `).join("")
            : "<p>No feedback available.</p>";
    } catch (error) {
        el("feedbackData").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Loads all destinations for the admin destination grid.
async function loadAdmin() {
    if (!el("adminData")) return;

    try {
        const data = await apiFetch("/admin/destinations");

        el("adminData").innerHTML = (data || []).map((destination) => `
            <div class="admin-destination">
                <img
                    src="${destination.image || "https://via.placeholder.com/200"}"
                    onerror="this.src='https://via.placeholder.com/200'"
                    alt="${escapeHtml(destination.name || "Destination")}"
                >
                <h3>${escapeHtml(destination.name)}</h3>
                <p>${escapeHtml(destination.region)} | ${formatCurrency(destination.cost)}</p>
                <button class="delete-btn" onclick="deleteDestination(${destination.id})">Delete</button>
            </div>
        `).join("");
    } catch (error) {
        el("adminData").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Adds a new destination from the admin form.
async function addDestination() {
    try {
        const payload = {
            name: getValue("name"),
            type: getValue("type"),
            region: getValue("region"),
            cost: parseInt(getValue("cost") || "0", 10),
            weather: getValue("weather"),
            best_season: getValue("season"),
            activities: getValue("activities"),
            safety_rating: parseFloat(getValue("safety_rating") || "5"),
            user_rating: parseFloat(getValue("user_rating") || "4"),
            image: getValue("image"),
            hotel_cost_per_day: parseInt(getValue("hotel_cost") || "0", 10),
            meal_cost_per_day: parseInt(getValue("meal_cost") || "0", 10),
            travel_cost: parseInt(getValue("travel_cost") || "0", 10)
        };

        if (!payload.name || !payload.type || !payload.region || !payload.cost) {
            throw new Error("Please fill all required destination fields");
        }

        const data = await apiFetch("/admin/add", {
            method: "POST",
            body: payload
        });

        showBanner(data.message || "Destination added", "success");
        loadAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Deletes a destination from the admin list.
async function deleteDestination(id) {
    try {
        const data = await apiFetch(`/admin/delete/${id}`, { method: "DELETE" });
        showBanner(data.message || "Destination deleted", "success");
        loadAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Keeps legacy delete calls working safely.
async function adminDeleteDestination(id) {
    await deleteDestination(id);
}

// Loads AI models in a cleaner list layout.
async function loadModels() {
    if (!el("modelList")) return;

    try {
        const data = await apiFetch("/admin/models");

        el("modelList").innerHTML = (data || []).length
            ? data.map((model) => `
                <div class="model-item">
                    <div>
                        <b>${escapeHtml(model.name)}</b>
                        <div class="model-status">${escapeHtml(model.status)}</div>
                    </div>
                    <button type="button" class="admin-btn" onclick="activateModel(${model.id})">Activate</button>
                </div>
            `).join("")
            : "<p>No models found</p>";
    } catch (error) {
        el("modelList").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Adds a new AI model.
async function addModel() {
    try {
        const modelName = getValue("modelName");
        if (!modelName) {
            throw new Error("Enter model name");
        }

        const data = await apiFetch("/admin/add-model", {
            method: "POST",
            body: { model_name: modelName }
        });

        showBanner(data.message || "Model saved", "success");
        if (el("modelName")) el("modelName").value = "";
        loadModels();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Activates the selected AI model.
async function activateModel(modelId) {
    try {
        const data = await apiFetch(`/admin/activate-model/${modelId}`, {
            method: "PUT"
        });
        showBanner(data.message || "Model activated", "success");
        loadModels();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Refreshes the dataset for recommendations.
async function refreshDataset() {
    try {
        const data = await apiFetch("/admin/refresh-dataset");
        showBanner(data.message || "Dataset refreshed", "success");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Loads all restaurants into the admin dashboard.
async function loadRestaurantsAdmin() {
    if (!el("restaurantsAdminData")) return;

    try {
        const data = await apiFetch("/admin/restaurants");

        el("restaurantsAdminData").innerHTML = data.length
            ? data.map((restaurant) => `
                <div class="info-card">
                    <div class="info-card-head">
                        <span class="info-icon">🍽</span>
                        <strong>${escapeHtml(restaurant.name)}</strong>
                    </div>
                    <p>${escapeHtml(restaurant.city)} | ${escapeHtml(restaurant.type)}</p>
                    <p>Rating: ${escapeHtml(restaurant.rating)} | Price: ${formatCurrency(restaurant.price)}</p>
                    <button class="delete-btn" onclick="deleteRestaurant(${restaurant.id})">Delete</button>
                </div>
            `).join("")
            : "<p>No restaurants added yet.</p>";
    } catch (error) {
        el("restaurantsAdminData").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Adds a new restaurant from the admin form.
async function addRestaurant() {
    try {
        const payload = {
            name: getValue("restaurant_name"),
            city: getValue("restaurant_city"),
            rating: parseFloat(getValue("restaurant_rating") || "0"),
            type: getValue("restaurant_type"),
            price: parseInt(getValue("restaurant_price") || "0", 10)
        };

        if (!payload.name || !payload.city || !payload.rating || !payload.type || !payload.price) {
            throw new Error("Please fill all restaurant fields");
        }

        const data = await apiFetch("/admin/restaurants", {
            method: "POST",
            body: payload
        });

        showBanner(data.message || "Restaurant added", "success");
        loadRestaurantsAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Deletes a restaurant from the admin list.
async function deleteRestaurant(restaurantId) {
    try {
        const data = await apiFetch(`/admin/restaurants/${restaurantId}`, {
            method: "DELETE"
        });
        showBanner(data.message || "Restaurant deleted", "success");
        loadRestaurantsAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Loads all events into the admin dashboard.
async function loadEventsAdmin() {
    if (!el("eventsAdminData")) return;

    try {
        const data = await apiFetch("/admin/events");

        el("eventsAdminData").innerHTML = data.length
            ? data.map((event) => `
                <div class="info-card">
                    <div class="info-card-head">
                        <span class="info-icon">🎉</span>
                        <strong>${escapeHtml(event.name)}</strong>
                    </div>
                    <p>${escapeHtml(event.city)} | ${escapeHtml(event.event_date || "TBA")}</p>
                    <p>${escapeHtml(event.description || "")}</p>
                    <button class="delete-btn" onclick="deleteEvent(${event.id})">Delete</button>
                </div>
            `).join("")
            : "<p>No events added yet.</p>";
    } catch (error) {
        el("eventsAdminData").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
    }
}

// Adds a new event from the admin form.
async function addEvent() {
    try {
        const payload = {
            name: getValue("event_name"),
            city: getValue("event_city"),
            event_date: getValue("event_date"),
            description: getValue("event_description")
        };

        if (!payload.name || !payload.city || !payload.event_date || !payload.description) {
            throw new Error("Please fill all event fields");
        }

        const data = await apiFetch("/admin/events", {
            method: "POST",
            body: payload
        });

        showBanner(data.message || "Event added", "success");
        loadEventsAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Deletes an event from the admin list.
async function deleteEvent(eventId) {
    try {
        const data = await apiFetch(`/admin/events/${eventId}`, {
            method: "DELETE"
        });
        showBanner(data.message || "Event deleted", "success");
        loadEventsAdmin();
        loadStats();
    } catch (error) {
        showBanner(error.message, "error");
    }
}
function initAdminDashboard() {
    if (!document.body.classList.contains("admin-page")) return;

    if (el("adminData")) loadAdmin();
    if (el("statsData")) loadStats();
    if (el("feedbackData")) loadFeedback();
    if (el("modelList")) loadModels();
    if (el("restaurantsAdminData")) loadRestaurantsAdmin();
    if (el("eventsAdminData")) loadEventsAdmin();
}

window.loadStats = loadStats;
window.loadFeedback = loadFeedback;
window.loadAdmin = loadAdmin;
window.addDestination = addDestination;
window.deleteDestination = deleteDestination;
window.adminDeleteDestination = adminDeleteDestination;
window.loadModels = loadModels;
window.addModel = addModel;
window.activateModel = activateModel;
window.refreshDataset = refreshDataset;
window.loadRestaurantsAdmin = loadRestaurantsAdmin;
window.addRestaurant = addRestaurant;
window.deleteRestaurant = deleteRestaurant;
window.loadEventsAdmin = loadEventsAdmin;
window.addEvent = addEvent;
window.deleteEvent = deleteEvent;

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminDashboard);
} else {
    initAdminDashboard();
}

