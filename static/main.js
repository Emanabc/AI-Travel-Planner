// -------- Global Variables --------
const API = window.location.origin;
// NOTE: Do not use a second generic `map` variable name here.
// Leaflet map instance is stored in `travelMap` only.


// Tracks the destination currently selected for itinerary generation and saving.

let selectedDestination = null;
let appConfig = {
    weather_enabled: true,
    maps_enabled: true
};

// -------- Helper Functions --------                                                                                                      

// This function gets an element by ID
function el(id) {
    return document.getElementById(id);
}

// This function gets and trims the value of an input field
function getValue(id) {
    const element = el(id);
    return element ? element.value.trim() : "";
}

// This function escapes HTML characters for safe display
function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// Escapes single quotes for inline onclick handlers.
function escapeSingleQuotes(value) {
    return String(value ?? "").replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

// Formats currency values in a cleaner PKR style.
function formatCurrency(value) {
    return `PKR ${Number(value || 0).toLocaleString()}`;
}

function createDestinationPlaceholderImage(name) {
    const label = String(name || "Destination").trim() || "Destination";
    let hash = 0;
    for (let index = 0; index < label.length; index += 1) {
        hash = (hash * 31 + label.charCodeAt(index)) % 360;
    }

    const hue = hash;
    const safeLabel = escapeHtml(label);
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
            <defs>
                <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="hsl(${hue}, 62%, 34%)"/>
                    <stop offset="100%" stop-color="hsl(${(hue + 42) % 360}, 66%, 22%)"/>
                </linearGradient>
            </defs>
            <rect width="800" height="500" fill="url(#bg)"/>
            <path d="M0 365 C145 305 250 335 370 285 C505 228 623 250 800 184 L800 500 L0 500 Z" fill="rgba(255,255,255,0.18)"/>
            <circle cx="642" cy="116" r="54" fill="rgba(255,255,255,0.22)"/>
            <text x="50%" y="52%" text-anchor="middle" fill="#ffffff" font-family="Arial, sans-serif" font-size="44" font-weight="700">${safeLabel}</text>
        </svg>
    `.trim();

    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function getDestinationImage(destination) {
    const rawImage = String(destination?.image || "").trim();
    if (rawImage && rawImage !== "null" && rawImage !== "undefined") {
        return rawImage;
    }

    const normalizedName = String(destination?.name || "destination")
        .trim()
        .toLowerCase();
    const knownImages = {
        "gwadar": "/static/images/gawadar.jpg",
        "gwadar beach": "/static/images/gawadar.jpg",
        "swat": "/static/images/swat.jpeg",
        "swat valley": "/static/images/swat.jpeg"
    };

    if (knownImages[normalizedName]) {
        return knownImages[normalizedName];
    }

    return createDestinationPlaceholderImage(destination?.name || "Destination");
}

function renderInlineState(type, message) {
    return `
        <div class="ui-state ui-state-${escapeHtml(type)}">
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

function setSectionState(elementId, type, message) {
    const element = el(elementId);
    if (!element) return;

    if (type === "loading") {
        element.innerHTML = `
            <div class="ui-state ui-state-loading">
                <div class="loading-spinner"></div>
                <p>${escapeHtml(message)}</p>
            </div>`;
    } else {
        element.innerHTML = renderInlineState(type, message);
    }
}


function ensureStatusBanner() {
    let banner = document.getElementById("appStatusBanner");
    if (banner) return banner;

    banner = document.createElement("div");
    banner.id = "appStatusBanner";
    banner.className = "app-status-banner";
    banner.setAttribute("role", "status");
    banner.setAttribute("aria-live", "polite");
    document.body.appendChild(banner);
    return banner;
}

function showBanner(message, type = "info") {
    const banner = ensureStatusBanner();
    banner.className = `app-status-banner app-status-${type}`;
    banner.textContent = message;
    banner.classList.add("is-visible");

    window.clearTimeout(showBanner.hideTimer);
    showBanner.hideTimer = window.setTimeout(() => {
        banner.classList.remove("is-visible");
    }, 2600);
}

function renderActionLink(label, href) {
    return `
        <a class="info-link-btn" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
            ${escapeHtml(label)}
        </a>
    `;
}

function createSectionHeadingMarkup(title, description = "") {
    return `
        <div class="info-card">
            <div class="info-card-head">
                <span class="info-icon">I</span>
                <strong>${escapeHtml(title)}</strong>
            </div>
            ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        </div>
    `;
}

function ensureElementExists(parent, selector, markup) {
    let element = parent.querySelector(selector);
    if (element) return element;

    parent.insertAdjacentHTML("beforeend", markup);
    element = parent.querySelector(selector);
    return element;
}

function scrollToElement(target) {
    if (!target || typeof target.scrollIntoView !== "function") return;

    target.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function flashSection(target) {
    if (!target) return;

    target.classList.remove("section-flash");
    void target.offsetWidth;
    target.classList.add("section-flash");

    window.clearTimeout(flashSection.hideTimer);
    flashSection.hideTimer = window.setTimeout(() => {
        target.classList.remove("section-flash");
    }, 1400);
}

// ADDED: Extract a destination name from the current UI state.
function getActiveDestinationName() {
    const searchQuery = getValue("searchQuery");
    if (searchQuery) return searchQuery;
    if (selectedDestination && selectedDestination.name) return selectedDestination.name;
    return "";
}

function ensureTravelInfoPanelStructure() {
    const panel = el("travelInfoPanel");
    if (!panel) {
        return null;
    }

    let sectionsWrap = panel.querySelector(".insights-sections");
    if (!sectionsWrap) {
        panel.innerHTML = `
            <h3>Destination Insights</h3>
            <p class="insights-selected-label" id="insightsSelectedLabel">
                Select a destination card to load travel details.
            </p>
            <div class="insights-sections">
                <section class="insight-section" id="generalInfoSection">
                    <h4>Quick View</h4>
                    <div class="info-panel-body" id="generalInfoContent">
                        ${createSectionHeadingMarkup("Quick View", "Map previews and shared travel details will appear here.")}
                    </div>
                </section>
                <section class="insight-section" id="restaurantsSection">
                    <h4>Restaurants</h4>
                    <div class="info-panel-body" id="restaurantsContent">
                        ${createSectionHeadingMarkup("Restaurants", "Restaurant recommendations will appear here.")}
                    </div>
                </section>
                <section class="insight-section" id="eventsSection">
                    <h4>Events</h4>
                    <div class="info-panel-body" id="eventsContent">
                        ${createSectionHeadingMarkup("Events", "Upcoming events and local happenings will appear here.")}
                    </div>
                </section>
                <section class="insight-section" id="weatherSection">
                    <h4>Weather</h4>
                    <div class="info-panel-body" id="weatherContent">
                        ${createSectionHeadingMarkup("Weather", "Current weather details will appear here.")}
                    </div>
                </section>
                <section class="insight-section" id="advisorySection">
                    <h4>Travel Advisory</h4>
                    <div class="info-panel-body" id="advisoryContent">
                        ${createSectionHeadingMarkup("Travel Advisory", "Safety tips and travel guidance will appear here.")}
                    </div>
                </section>
            </div>
        `;
        sectionsWrap = panel.querySelector(".insights-sections");
    }

    ensureElementExists(panel, "#insightsSelectedLabel", `
        <p class="insights-selected-label" id="insightsSelectedLabel">
            Select a destination card to load travel details.
        </p>
    `);
    ensureElementExists(panel, "#generalInfoContent", `
        <section class="insight-section" id="generalInfoSection">
            <h4>Quick View</h4>
            <div class="info-panel-body" id="generalInfoContent"></div>
        </section>
    `);
    ensureElementExists(panel, "#restaurantsContent", `
        <section class="insight-section" id="restaurantsSection">
            <h4>Restaurants</h4>
            <div class="info-panel-body" id="restaurantsContent"></div>
        </section>
    `);
    ensureElementExists(panel, "#eventsContent", `
        <section class="insight-section" id="eventsSection">
            <h4>Events</h4>
            <div class="info-panel-body" id="eventsContent"></div>
        </section>
    `);
    ensureElementExists(panel, "#weatherContent", `
        <section class="insight-section" id="weatherSection">
            <h4>Weather</h4>
            <div class="info-panel-body" id="weatherContent"></div>
        </section>
    `);
    ensureElementExists(panel, "#advisoryContent", `
        <section class="insight-section" id="advisorySection">
            <h4>Travel Advisory</h4>
            <div class="info-panel-body" id="advisoryContent"></div>
        </section>
    `);

    return {
        panel,
        selectedLabel: panel.querySelector("#insightsSelectedLabel"),
        general: panel.querySelector("#generalInfoContent"),
        restaurants: panel.querySelector("#restaurantsContent"),
        events: panel.querySelector("#eventsContent"),
        weather: panel.querySelector("#weatherContent"),
        advisory: panel.querySelector("#advisoryContent")
    };
}

function ensureItineraryContainerStructure() {
    const container = el("itineraryResult");
    if (!container) {
        return null;
    }

    if (!container.querySelector("#itineraryStatus")) {
        container.innerHTML = `
            <div class="info-panel-body" id="itineraryStatus">
                ${createSectionHeadingMarkup("Itinerary Planner", "Your generated itinerary will appear here and stay editable.")}
            </div>
            <div id="itineraryEditorHost"></div>
        `;
    }

    return {
        container,
        status: container.querySelector("#itineraryStatus"),
        editorHost: container.querySelector("#itineraryEditorHost")
    };
}

function renderInsightSection(sectionKey, title, cardsMarkup, selectedPlace = "") {
    const sections = ensureTravelInfoPanelStructure();
    if (!sections) return;

    const target = sections[sectionKey];
    if (!target) {
        console.error(`Insight section "${sectionKey}" is missing.`);
        return;
    }

    console.log("[TARGET ELEMENT]", target);
    console.log("[SECTION KEY]", sectionKey);
    console.log("[RENDER SECTION] sectionKey:", sectionKey, "target element:", target);
    console.log("[RENDER SECTION] Markup length:", cardsMarkup?.length || 0);

    if (sections.selectedLabel && selectedPlace) {
        sections.selectedLabel.textContent = `Selected destination: ${selectedPlace}`;
    }

    target.innerHTML = cardsMarkup || createSectionHeadingMarkup(title, "No data available.");
    
    console.log(target.innerHTML);
    console.log("[RENDER SECTION] After innerHTML assignment, target.innerHTML length:", target.innerHTML.length);
    console.log("[RENDER SECTION] target.innerHTML first 200 chars:", target.innerHTML.substring(0, 200));
    
    if (sectionKey !== "weather") {
        scrollToElement(sections.panel);
    }
    flashSection(target.closest(".insight-section") || target);
}

function renderInsightState(sectionKey, title, type, message, selectedPlace = "") {
    renderInsightSection(
        sectionKey,
        title,
        renderInlineState(type, message),
        selectedPlace
    );
}

function normalizeArrayResponse(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    if (data && Array.isArray(data.items)) return data.items;
    return [];
}

function ensureFeedbackStatusBox() {
    const statusBox = el("feedbackStatus");
    if (!statusBox) {
        console.error("feedbackStatus container is missing from the page.");
        return null;
    }

    return statusBox;
}

function renderFeedbackState(type, message) {
    const statusBox = ensureFeedbackStatusBox();
    if (!statusBox) return;

    statusBox.innerHTML = renderInlineState(type, message);
    scrollToElement(statusBox);
    flashSection(statusBox);
}

// -------- Map Helpers --------

const DEFAULT_MAP_CENTER = [35.8825, 74.4643];
const DEFAULT_MAP_ZOOM = 6;
const FEATURED_DESTINATIONS = [
    {
        name: "Hunza",
        lat: 36.3167,
        lng: 74.65,
        description: "Mountain valleys, lakes, and panoramic Karakoram views."
    },
    {
        name: "Skardu",
        lat: 35.2971,
        lng: 75.6333,
        description: "A high-altitude gateway to lakes, treks, and alpine landscapes."
    },
    {
        name: "Murree",
        lat: 33.907,
        lng: 73.3943,
        description: "Cool-weather hills, scenic roads, and family-friendly escapes."
    }
];

let travelMap = null;
let featuredMarkerLayer = null;
let activeLocationMarker = null;
let userLocationMarker = null;
const destinationMarkers = new Map();

function normalizeDestinationKey(name) {
    return String(name || "").trim().toLowerCase();
}

function getFeaturedDestination(name) {
    const key = normalizeDestinationKey(name);
    return FEATURED_DESTINATIONS.find((destination) => normalizeDestinationKey(destination.name) === key) || null;
}

function buildMapLinks(place) {
    const encodedPlace = encodeURIComponent(place);
    return {
        mapsUrl: `https://www.openstreetmap.org/search?query=${encodedPlace}`,
        exploreUrl: `https://www.openstreetmap.org/search?query=${encodedPlace}`
    };
}

function buildCoordinateMapLink(lat, lng) {
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=11/${lat}/${lng}`;
}

function createPopupMarkup(name, description = "") {
    return `
        <div class="map-popup">
            <strong>${escapeHtml(name)}</strong>
            ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        </div>
    `;
}

function renderMapPanel(name, lat, lng, description = "") {
    const coordinateLink = buildCoordinateMapLink(lat, lng);

    renderInfoPanel(
        `${name} Map`,
        `
            <div class="info-card">
                <div class="info-card-head">
                    <span class="info-icon">M</span>
                    <strong>${escapeHtml(name)} on OpenStreetMap</strong>
                </div>
                <p>${escapeHtml(description || `The map has been centered on ${name}.`)}</p>
                <div class="info-link-row">
                    ${renderActionLink("Open in OpenStreetMap", coordinateLink)}
                </div>
            </div>
        `
    );
}

function addFeaturedDestinationMarker(destination) {
    const key = normalizeDestinationKey(destination.name);
    let marker = destinationMarkers.get(key);

    if (!marker) {
        marker = L.marker([destination.lat, destination.lng], {
            title: destination.name
        });
        destinationMarkers.set(key, marker);
        marker.addTo(featuredMarkerLayer);
    } else {
        marker.setLatLng([destination.lat, destination.lng]);
    }

    marker.bindPopup(createPopupMarkup(destination.name, destination.description));
    return marker;
}

function ensureTravelMap() {
    // Safety: map container might not be mounted yet (or may be hidden).
    // We initialize it only once and reuse that instance.
    if (travelMap) return travelMap;

    const mapElement = el("map");
    if (!mapElement) {
        return null;
    }

    if (typeof L === "undefined") {
        console.warn("Leaflet is not loaded; map initialization skipped.");
        return null;
    }

    // Check if map is already initialized on this element
    if (mapElement._leaflet_id !== undefined) {
        console.warn("Map already initialized on this element");
        return travelMap;
    }

    try {
        travelMap = L.map(mapElement, {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(travelMap);

        featuredMarkerLayer = L.layerGroup().addTo(travelMap);

        FEATURED_DESTINATIONS.forEach((destination) => {
            addFeaturedDestinationMarker(destination);
        });

        const bounds = L.latLngBounds(FEATURED_DESTINATIONS.map((destination) => [destination.lat, destination.lng]));
        if (bounds.isValid()) {
            travelMap.fitBounds(bounds.pad(0.18), {
                animate: false
            });
        }

        window.setTimeout(() => {
            if (travelMap && travelMap.invalidateSize) {
                travelMap.invalidateSize();
            }
        }, 120);
    } catch (error) {
        console.error("Error initializing map:", error);
        travelMap = null;
        return null;
    }

    return travelMap;
}

function focusMapSection() {
    const mapSection = document.querySelector(".map-section");
    if (mapSection) {
        scrollToElement(mapSection);
        flashSection(mapSection);
    }
}

function showLocationOnMap(lat, lng, name) {
    const leafletMap = ensureTravelMap();
    if (!leafletMap) return;

    const numericLat = Number(lat);
    const numericLng = Number(lng);
    if (!Number.isFinite(numericLat) || !Number.isFinite(numericLng)) {
        showBanner("Location coordinates are invalid.", "error");
        return;
    }

    const fallbackName = (name || "Selected Destination").trim() || "Selected Destination";
    const featuredDestination = getFeaturedDestination(fallbackName);
    const marker = featuredDestination
        ? addFeaturedDestinationMarker(featuredDestination)
        : (() => {
            if (!activeLocationMarker) {
                activeLocationMarker = L.marker([numericLat, numericLng], {
                    title: fallbackName
                }).addTo(leafletMap);
            } else {
                activeLocationMarker.setLatLng([numericLat, numericLng]);
            }

            activeLocationMarker.bindPopup(createPopupMarkup(fallbackName));
            return activeLocationMarker;
        })();

    leafletMap.flyTo([numericLat, numericLng], 10, {
        animate: true,
        duration: 1.25
    });

    marker.openPopup();
    renderMapPanel(
        fallbackName,
        numericLat,
        numericLng,
        featuredDestination ? featuredDestination.description : ""
    );
    focusMapSection();
}

window.showLocationOnMap = showLocationOnMap;

async function geocodeDestination(place) {
    // NOTE: Map initialization should be independent from geocoding.
    // If Leaflet is not ready, this function will still throw a useful error.

    const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(place)}`, {
        headers: {
            Accept: "application/json"
        }
    });

    if (!response.ok) {
        throw new Error("Unable to locate this destination on the map.");
    }

    const matches = await response.json();
    if (!Array.isArray(matches) || !matches.length) {
        throw new Error("No map match was found for this destination.");
    }

    return matches[0];
}

async function openMap(place) {
    const cleanPlace = (place || "").trim();
    if (!cleanPlace) {
        showBanner("Destination name is required to open map.", "error");
        return;
    }

    const featuredDestination = getFeaturedDestination(cleanPlace);
    if (featuredDestination) {
        showLocationOnMap(featuredDestination.lat, featuredDestination.lng, featuredDestination.name);
        return;
    }

    try {
        const match = await geocodeDestination(cleanPlace);
        showLocationOnMap(parseFloat(match.lat), parseFloat(match.lon), cleanPlace);
    } catch (error) {
        const { mapsUrl, exploreUrl } = buildMapLinks(cleanPlace);
        renderInfoPanel(
            `${cleanPlace} Map`,
            `
                <div class="info-card">
                    <div class="info-card-head">
                        <span class="info-icon">M</span>
                        <strong>OpenStreetMap Search</strong>
                    </div>
                    <p>${escapeHtml(error.message || `We could not center the map automatically for ${cleanPlace}.`)}</p>
                    <div class="info-link-row">
                        ${renderActionLink("Search in OpenStreetMap", mapsUrl)}
                        ${renderActionLink("Explore Nearby", exploreUrl)}
                    </div>
                </div>
            `
        );
        showBanner(error.message || "Map lookup failed.", "error");
    }
}
// END ADDED FEATURE

async function parseJsonResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json()
        : { error: await response.text() };

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong");
    }

    return data;
}

// Shared fetch wrapper used throughout the app.
async function apiFetch(path, options = {}) {
    const config = {
        method: options.method || "GET",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    };

    if (options.body !== undefined) {
        config.body = JSON.stringify(options.body);
    }

    const response = await fetch(`${API}${path}`, config);
    return parseJsonResponse(response);
}

async function loadAppConfig() {
    try {
        const data = await apiFetch("/app-config");
        appConfig = {
            ...appConfig,
            ...data
        };
    } catch (error) {
        console.error("App config load failed:", error);
    }
}

function getGoogleClientId() {
    const loginContainer = document.getElementById("googleLoginContainer");
    return loginContainer ? (loginContainer.dataset.googleClientId || "").trim() : "";
}

function prefillFeedbackForm() {
    const storedName = localStorage.getItem("user_name") || "";
    const storedEmail = localStorage.getItem("user_email") || "";

    if (el("fb_name") && storedName && !el("fb_name").value.trim()) {
        el("fb_name").value = storedName;
    }

    if (el("fb_email") && storedEmail && !el("fb_email").value.trim()) {
        el("fb_email").value = storedEmail;
    }
}

// Updates the selected destination label used by the planner section.
function setSelectedDestination(destinationId, destinationName) {
    selectedDestination = {
        id: destinationId || null,
        name: destinationName || "Selected Destination"
    };

    if (el("selectedDestination")) {
        el("selectedDestination").textContent = selectedDestination.id
            ? `Selected destination: ${selectedDestination.name}`
            : "Generate a plan from the controls below or pick a destination card.";
    }
}

// Converts itinerary data into shareable plain text.
function itineraryToText(plan) {
    if (!Array.isArray(plan)) {
        return String(plan || "");
    }

    return plan.map((item, index) => {
        const normalizedItem = normalizePlanItem(item, index);
        return `${normalizedItem.day}\n${normalizedItem.activities.map((activity) => `- ${activity}`).join("\n")}`;
    }).join("\n\n");
}

// Converts any activity shape (string/object) into readable plain text.
function normalizeActivity(activity) {
    if (typeof activity === "string") {
        return activity.trim();
    }

    if (activity && typeof activity === "object") {
        const likelyTextFields = ["text", "title", "name", "activity", "description", "task"];
        for (const key of likelyTextFields) {
            if (typeof activity[key] === "string" && activity[key].trim()) {
                return activity[key].trim();
            }
        }

        // Fallback: join primitive values so object content stays readable.
        const primitiveValues = Object.values(activity).filter((value) =>
            typeof value === "string" || typeof value === "number"
        );
        if (primitiveValues.length) {
            return primitiveValues.map((value) => String(value).trim()).filter(Boolean).join(" - ");
        }
    }

    return String(activity ?? "").trim();
}

// Normalizes a single itinerary day so UI never renders [object Object].
function normalizePlanItem(item, index) {
    const safeItem = item && typeof item === "object" ? item : {};
    const dayLabel = typeof safeItem.day === "string" && safeItem.day.trim()
        ? safeItem.day.trim()
        : `Day ${index + 1}`;
    const rawActivities = Array.isArray(safeItem.activities) ? safeItem.activities : [];
    const activities = rawActivities
        .map(normalizeActivity)
        .filter(Boolean);

    return {
        day: dayLabel,
        activities: activities.length ? activities : ["No activities added yet."]
    };
}

// Normalizes all itinerary items before rendering or exporting.
function normalizePlanData(plan) {
    if (!Array.isArray(plan)) return [];
    return plan.map((item, index) => normalizePlanItem(item, index));
}
// -------------------------
// Authentication And Profile
// -------------------------

// Handles placeholder Google login.
async function googleLogin(credentialResponse = null) {
    try {
        const googleCredential = credentialResponse && typeof credentialResponse === "object"
            ? credentialResponse.credential
            : null;
        const googleClientId = getGoogleClientId();

        if (!googleCredential && window.google && google.accounts && google.accounts.id && googleClientId) {
            google.accounts.id.prompt();
            return;
        }

        const data = await apiFetch("/google-login", {
            method: "POST",
            body: {
                credential: googleCredential,
                name: "Google User",
                email: "google_user@travelplanner.local"
            }
        });

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_name", data.name || "");
        localStorage.setItem("user_email", data.email || "");
        showBanner("Welcome Eman " + (data.name || "User") + "! Logging you in...", "success");

        setTimeout(() => {
            window.location.href = data.redirect_url || "/";
        }, 800);
    } catch (error) {
        if (el("msg")) el("msg").textContent = error.message;
    }
}

function initGoogleLogin() {
    const container = document.getElementById("googleLoginContainer");
    if (!container) return;

    const googleClientId = getGoogleClientId();
    const placeholderButton = document.getElementById("googleFallbackButton");
    const statusText = document.getElementById("googleLoginStatus");

    if (!googleClientId || !(window.google && google.accounts && google.accounts.id)) {
        if (statusText && !googleClientId) {
            statusText.textContent = "Google sign-in is not configured on this server.";
        }
        return;
    }

    if (placeholderButton) {
        placeholderButton.style.display = "none";
    }

    google.accounts.id.initialize({
        client_id: googleClientId,
        callback: function(credentialResponse) {
            googleLogin(credentialResponse);
        }
    });

    google.accounts.id.renderButton(container, {
        theme: "filled_blue",
        size: "large",
        shape: "rectangular",
        text: "continue_with",
        width: 320
    });

    google.accounts.id.prompt(function(notification) {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            console.log("Google One Tap not shown:", notification.getNotDisplayedReason());
        }
    });
}

    
// Logs the user in and stores the returned user id locally.
async function loginUser() {
    try {
        const email = getValue("email");
        const password = getValue("password");

        if (!email || !password) {
            throw new Error("Email and password are required");
        }

        const data = await apiFetch("/login", {
            method: "POST",
            body: { email, password }
        });

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("user_name", data.name || "");
        localStorage.setItem("user_email", email);
        if (el("msg")) el("msg").textContent = "Login successful";

        setTimeout(() => {
            window.location.href = "/";
        }, 800);
    } catch (error) {
        showBanner(error.message || "Login failed. Please try again.", "error");
    }
}

// Loads the greeting for the active user.
async function loadGreeting() {
    const userId = localStorage.getItem("user_id");
    const box = el("welcomeBox");
    if (!userId || !box) return;

    try {
        const data = await apiFetch(`/greeting/${userId}`);
        box.textContent = data.message || "Welcome Traveler!";
    } catch (error) {
        console.error("Greeting load failed:", error);
    }
}

// Saves user travel preferences from the profile page.
async function savePreferences() {
    try {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            throw new Error("Login first");
        }

        const travelStyle = getValue("travel_style");
        const budget = getValue("budget");
        const duration = getValue("duration");

        if (!travelStyle || !budget || !duration) {
            throw new Error("Please fill all preference fields");
        }

        const data = await apiFetch("/save-preferences", {
            method: "POST",
            body: {
                user_id: parseInt(userId, 10),
                travel_style: travelStyle,
                budget_range: parseInt(budget, 10),
                duration: parseInt(duration, 10)
            }
        });

        if (el("message")) el("message").textContent = data.message || "Preferences saved";
    } catch (error) {
        if (el("message")) el("message").textContent = error.message;
    }
}

// Loads user preferences back into the profile form.
async function loadPreferences() {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;

    try {
        const data = await apiFetch(`/get-preferences/${userId}`);
        if (el("travel_style")) el("travel_style").value = data.travel_style || "";
        if (el("budget")) el("budget").value = data.budget_range || data.budget || "";
        if (el("duration")) el("duration").value = data.duration || "";
        if (el("preference")) el("preference").value = (data.travel_style || "").toLowerCase() || "";
    } catch (error) {
        console.error("Load preferences failed:", error);
    }
}

// Logs the user out by clearing local storage.
// Purana replace karo:
async function logout() {
    try {
        await fetch("/logout", { method: "POST" });
    } catch (e) {}
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_email");
    window.location.href = "/login";
}
// Renders destination cards and keeps each action grouped within the same card.
function renderCards(data, title = "") {
    const container = el("results") || el("suggestions");
    if (!container) return;

    if (!Array.isArray(data) || data.length === 0) {
        container.innerHTML = `
            ${title ? `<h2 class="results-heading">${escapeHtml(title)}</h2>` : ""}
            <div class="ui-state ui-state-info no-results-state">
                <span class="state-icon">🔍</span>
                <p>No destinations found. Try a different keyword, region, or budget.</p>
                <p class="no-results-hint">Examples: "Hunza", "adventure", "Gilgit Baltistan", "under 50000"</p>
            </div>`;
        scrollToElement(container);
        return;
    }

    const cards = data.map((destination) => {
        const stars = buildStarRating(destination.user_rating || destination.rating || 0);
        const imageUrl = getDestinationImage(destination);
        return `
            <article class="card" tabindex="0">
                <div class="card-img-wrap">
                    <img
                        src="${escapeHtml(imageUrl)}"
                        onerror="this.closest('.card-img-wrap').classList.add('card-img-missing');this.remove();"
                        alt="${escapeHtml(destination.name || "Destination")}"
                        loading="lazy"
                    >
                    <span class="card-img-fallback">${escapeHtml(destination.name || "Destination")}</span>
                    <span class="card-type-badge">${escapeHtml(destination.type || "Destination")}</span>
                </div>

                <div class="card-content">
                    <h3 class="card-name">${escapeHtml(destination.name || "Unknown Destination")}</h3>
                    <p class="card-region">${escapeHtml(destination.region || "Pakistan")}</p>
                    <div class="card-stars" aria-label="Rating ${destination.user_rating || 0} out of 5">
                        ${stars}
                    </div>
                    <p class="card-price-pill">${formatCurrency(destination.cost)}<span class="price-label"> est. cost</span></p>
                </div>

                <div class="card-actions">
                    <button type="button" class="card-btn card-btn-map"     data-action="map"         data-city="${escapeHtml(destination.name || "")}">🗺 Map</button>
                    <button type="button" class="card-btn card-btn-weather"  data-action="weather"     data-city="${escapeHtml(destination.name || "")}">🌤 Weather</button>
                    <button type="button" class="card-btn card-btn-budget"   data-action="budget"      data-destination-id="${escapeHtml(String(destination.id || ""))}">💰 Budget</button>
                    <button type="button" class="card-btn card-btn-food"     data-action="restaurants" data-city="${escapeHtml(destination.name || "")}">🍽 Restaurants</button>
                    <button type="button" class="card-btn card-btn-events"   data-action="events"      data-city="${escapeHtml(destination.name || "")}">🎉 Events</button>
                    <button type="button" class="card-btn card-btn-advisory" data-action="advisory"    data-city="${escapeHtml(destination.name || "")}">⚠ Advisory</button>
                    <button type="button" class="card-btn card-btn-plan"     data-action="itinerary"   data-destination-id="${escapeHtml(String(destination.id || ""))}" data-city="${escapeHtml(destination.name || "")}">📅 Itinerary</button>
                </div>

                <div class="weather-inline-result"></div>
                <div id="budget-card-${destination.id}" class="budget-inline-result"></div>
            </article>
        `;
    }).join("");

    container.innerHTML = `
        ${title ? `<h2 class="results-heading">${escapeHtml(title)}</h2>` : ""}
        <div class="cards-grid">${cards}</div>
    `;

    // Auto-scroll and highlight results
    scrollToElement(container);
    flashSection(container);

    // Focus first card for keyboard/accessibility
    const firstCard = container.querySelector(".card");
    if (firstCard) firstCard.focus({ preventScroll: true });
}
// Helper — build 5-star rating display
function buildStarRating(rating) {
    const num = parseFloat(rating) || 0;
    const full = Math.floor(num);
    const half = num - full >= 0.5 ? 1 : 0;
    const empty = 5 - full - half;
    return (
        "★".repeat(full) +
        (half ? "½" : "") +
        "☆".repeat(empty) +
        ` <span class="rating-num">${num.toFixed(1)}</span>`
    );
}


// Loads the home suggestions section.
async function loadHomeSuggestions() {
    try {
        setSectionState("results", "loading", "Loading top destinations...");
        const data = await apiFetch("/suggestions");
        renderCards(data, "Top Destinations");
    } catch (error) {
        setSectionState("results", "error", error.message || "Unable to load suggestions.");
    }
}

// -------- Recommendations And Search --------

// Sends a request to the recommendation API with better error handling.
async function getRecommendations() {
    try {
        const query = getValue("searchQuery");
        if (!query.trim()) {
            showBanner("Please describe your ideal trip to get recommendations.", "info");
            el("searchQuery") && el("searchQuery").focus();
            return;
        }

        setSectionState("results", "loading", "🤖 AI is generating recommendations...");

        const userId = localStorage.getItem("user_id");
        const data = await apiFetch("/recommend", {
            method: "POST",
            body: {
                message: query,
                user_id: userId ? parseInt(userId, 10) : null
            }
        });

        const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
        if (!recommendations.length) {
            setSectionState("results", "info", "No recommendations found. Try a different query — e.g. 'relaxing mountain trip' or 'Hunza adventure'.");
            return;
        }

        renderCards(recommendations, "🤖 AI Recommendations");
        showBanner(`${recommendations.length} AI recommendation${recommendations.length !== 1 ? "s" : ""} ready.`, "success");
    } catch (error) {
        setSectionState("results", "error", error.message || "AI recommendation failed. Please try again.");
        showBanner(error.message || "Failed to load recommendations.", "error");
    }
}
// Extracts number of days from natural language query (e.g. "5 days trip to swat")
function syncDaysFromQuery(query) {
    const match = query.match(/(\d+)\s*(day|days|din|raat|night|nights)\b/i);
    if (match) {
        const detectedDays = parseInt(match[1], 10);
        if (detectedDays > 0 && el("days")) {
            el("days").value = detectedDays;
        }
        return detectedDays;
    }
    return null;
}


function smartSearch() {
    try {
        const query = getValue("searchQuery");
        if (!query.trim()) {
            showBanner("Please enter a destination, region, or budget to search.", "info");
            el("searchQuery") && el("searchQuery").focus();
            return;
        }

        const detectedDays = syncDaysFromQuery(query);   // <-- YE LINE ADD KARO
        if (detectedDays) {
            showBanner(`Detected ${detectedDays}-day trip from your search.`, "info");
        }

        setSectionState("results", "loading", `Searching for "${query}"...`);
        

        // Strict search first (faster, deterministic)
        fetch(`${API}/search-destinations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                // Fallback to AI smart search
                return fetch(`${API}/smart-search`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query })
                }).then(r => r.json());
            }
            return data;
        })
        .then(data => {
            if (data && data.error) {
                setSectionState("results", "error", data.error);
                return;
            }
            const results = (data && Array.isArray(data.results)) ? data.results : [];
            renderCards(results, results.length ? `Results for "${query}"` : "");
            if (results.length) {
                showBanner(`${results.length} destination${results.length !== 1 ? "s" : ""} found.`, "success");
            }
        })
        .catch(error => {
            setSectionState("results", "error", error.message || "Search failed. Please try again.");
            showBanner("Search failed.", "error");
        });

    } catch (error) {
        setSectionState("results", "error", error.message);
        showBanner(error.message, "error");
    }
}


// Loads destinations for a selected region.
async function loadNear(region) {
    try {
        const selectedRegion = region || getValue("regionSelect");
        if (!selectedRegion) {
            showBanner("Please select a region first.", "info");
            return;
        }

        const regionRequestMap = {
            "KPK": "Khyber Pakhtunkhwa",
            "Khyber Pakhtunkhwa": "Khyber Pakhtunkhwa",
            "Gilgit Baltistan": "Gilgit Baltistan",
            "Kashmir": "Azad Kashmir",
            "Azad Kashmir": "Azad Kashmir"
        };
        const normalizedRegion = regionRequestMap[selectedRegion] || selectedRegion;

        setSectionState("results", "loading", `Loading destinations in ${selectedRegion}...`);

        const data = await apiFetch(`/near/${encodeURIComponent(normalizedRegion)}`);
        const results = Array.isArray(data) ? data : [];
        renderCards(results, `Destinations in ${selectedRegion}`);

        if (results.length) {
            showBanner(`${results.length} destinations found in ${selectedRegion}.`, "success");
        } else {
            showBanner(`No destinations found in ${selectedRegion}.`, "info");
        }
    } catch (error) {
        setSectionState("results", "error", error.message || "Could not load region destinations.");
        showBanner(error.message, "error");
    }
}



// Shows weather information for a destination.
async function getWeatherDynamic(place, inlineContainer = null) {
    const placeName = String(place || "").trim();
    console.log("getWeather started");
    console.log("[Weather] getWeather called:", placeName);

    if (!placeName) {
        const message = "Please select a destination before loading weather.";
        console.error("[Weather] Missing destination name.");
        renderInsightState("weather", "Weather", "error", message);
        showBanner(message, "error");
        return;
    }

    try {
        renderInsightState(
            "weather",
            `${placeName} Weather`,
            "loading",
            `Loading weather for ${placeName}...`,
            placeName
        );
        if (inlineContainer) {
            inlineContainer.innerHTML = renderInlineState("loading", `Loading weather for ${placeName}...`);
        }

        const weatherResultContainer = document.getElementById("weatherResult");
        const weatherContentContainer = document.getElementById("weatherContent");
        console.log("Weather container:", weatherResultContainer);
        console.log("[Weather] weatherContent container:", weatherContentContainer);

        const requestUrl = `/weather/${encodeURIComponent(placeName)}`;
        const fullWeatherUrl = `${API}${requestUrl}`;
        console.log("Calling API:", requestUrl);
        console.log("[Weather] Fetching:", requestUrl);

        const response = await fetch(fullWeatherUrl, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });
        console.log("Response status:", response.status);

        const data = await parseJsonResponse(response);
        console.log("Weather data:", data);
        console.log("[WEATHER RESPONSE] Full API Response:", JSON.stringify(data, null, 2));

        const tempDisplay = data.temperature != null
            ? `${Math.round(data.temperature)} °C`
            : "No live data";

        const humidityDisplay = data.humidity != null
            ? `${data.humidity}%`
            : "No live data";

        const weatherDesc =
            data.weather && data.weather !== "Unavailable"
                ? data.weather
                : "Not available";

        const { mapsUrl } = buildMapLinks(placeName);

        const html = `
            <div class="info-card weather-result-card">
                <div class="info-card-head">
                    <span class="info-icon">🌤</span>
                    <strong>Current Conditions</strong>
                </div>
                <p style="color:#000;">
                    <strong>🌡 Temperature:</strong>
                    ${escapeHtml(tempDisplay)}
                </p>
                <p style="color:#000;">
                    <strong>☁ Condition:</strong>
                    ${escapeHtml(weatherDesc)}
                </p>
                <p style="color:#000;">
                    <strong>💧 Humidity:</strong>
                    ${escapeHtml(humidityDisplay)}
                </p>
                <p style="color:#000;">
                    <strong>📍 Location:</strong>
                    ${escapeHtml(data.resolved_city || placeName)}
                </p>
                <p style="color:#000;font-size:0.82rem;">
                    Source: ${escapeHtml(data.source || "live")}
                </p>
                ${data.message ? `
                    <p style="
                        color:#000;
                        background:#fef9c3;
                        padding:8px 12px;
                        border-radius:8px;
                        font-size:0.82rem;
                        margin-top:8px;
                    ">
                        ⚠ ${escapeHtml(data.message)}
                    </p>
                ` : ""}
                <div class="info-link-row">
                    ${renderActionLink("Open Map", mapsUrl)}
                </div>
            </div>
            `;

        console.log("[WEATHER HTML]", html);
        console.log("[WEATHER DATA FIELDS] Temp:", tempDisplay, "Humidity:", humidityDisplay, "Condition:", weatherDesc);

        renderInsightSection(
            "weather",
            `${placeName} Weather`,
            html,
            placeName
        );
        if (inlineContainer) {
            inlineContainer.innerHTML = html;
        }

        // Verify card is in DOM after rendering
        setTimeout(() => {
            const card = document.querySelector('.weather-result-card');
            console.log(card);
            console.log(card?.outerHTML);
            console.log(card ? getComputedStyle(card) : null);
            console.log("[AFTER RENDER] Weather card found:", !!card);
            if (card) {
                const cardStyle = getComputedStyle(card);
                const parentStyle = getComputedStyle(card.parentElement);
                console.log("[AFTER RENDER] Card HTML:", card.outerHTML);
                console.log("[AFTER RENDER] Card computed style:", {
                    display: cardStyle.display,
                    visibility: cardStyle.visibility,
                    opacity: cardStyle.opacity,
                    color: cardStyle.color,
                    background: cardStyle.backgroundColor,
                    height: cardStyle.height,
                    width: cardStyle.width
                });
                console.log("[WEATHER CARD COLOR]", cardStyle.color);
                console.log("[WEATHER PARENT BACKGROUND]", parentStyle.backgroundColor);
                console.log("[AFTER RENDER] Card parent background:", parentStyle.backgroundColor);
                console.log("[AFTER RENDER] Card text content sample:", card.textContent.substring(0, 100));
            }
        }, 200);

        showBanner(
            `Weather loaded for ${placeName}.`, "success"
        );

    } catch (error) {
        console.error("[Weather] Failed to load weather:", error);
        renderInsightState(
            "weather",
            `${placeName} Weather`,
            "error",
            error.message || "Weather data could not be loaded.",
            placeName
        );
        if (inlineContainer) {
            inlineContainer.innerHTML = renderInlineState("error", error.message || "Weather data could not be loaded.");
        }
        showBanner(error.message || "Weather data could not be loaded.", "error");
    }
}

async function getWeather(place, inlineContainer = null) {
    return getWeatherDynamic(place, inlineContainer);
}


// Calculates the budget and renders the breakdown inside the clicked card.
async function calculateBudgetById(destinationId) {
    try {
        const daysInput = getValue("days") || prompt("Enter number of days:");
        if (!daysInput) {
            throw new Error("Days required");
        }

        const days = parseInt(daysInput, 10);
        if (!days || Number.isNaN(days)) {
            throw new Error("Please enter a valid number of days");
        }

        const budgetContainer = el(`budget-card-${destinationId}`);
        if (budgetContainer) {
            budgetContainer.innerHTML = renderInlineState("loading", "Calculating budget...");
        }

        const data = await apiFetch("/calculate-budget", {
            method: "POST",
            body: {
                destination_id: parseInt(destinationId, 10),
                days
            }
        });

        if (budgetContainer) {
            budgetContainer.innerHTML = createBudgetTableMarkup(data, days);
        }
        showBanner("Budget calculated successfully.", "success");
    } catch (error) {
        const budgetContainer = el(`budget-card-${destinationId}`);
        if (budgetContainer) {
            budgetContainer.innerHTML = renderInlineState("error", error.message);
        } else {
            showBanner(error.message, "error");
        }
    }
}
function createBudgetTableMarkup(data, days) {
    const destinationLabel = data.destination ? `<p class="budget-destination">📍 ${escapeHtml(data.destination)}</p>` : "";

    return `
        <div class="budget-card modern-budget-card">
            <div class="budget-card-header">
                <div class="budget-card-title">💰 Budget Breakdown</div>
                <span class="budget-card-days">${days} Day${days > 1 ? "s" : ""}</span>
            </div>
            ${destinationLabel}
            <div class="budget-table-wrap">
                <table class="budget-table">
                    <thead>
                        <tr>
                            <th>Expense</th>
                            <th>Amount (PKR)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🏨 Hotel (${days} night${days > 1 ? "s" : ""})</td>
                            <td class="budget-amount">${formatCurrency(data.hotel)}</td>
                        </tr>
                        <tr>
                            <td>🍱 Meals (${days} day${days > 1 ? "s" : ""})</td>
                            <td class="budget-amount">${formatCurrency(data.meals)}</td>
                        </tr>
                        <tr>
                            <td>🚌 Travel</td>
                            <td class="budget-amount">${formatCurrency(data.travel)}</td>
                        </tr>
                        <tr>
                            <td>🎯 Destination Fee</td>
                            <td class="budget-amount">${formatCurrency(data.destination_cost)}</td>
                        </tr>
                        <tr class="budget-total-row">
                            <td><strong>Total Estimate</strong></td>
                            <td class="budget-total-amount"><strong>${formatCurrency(data.total)}</strong></td>
                        </tr>
                        ${data.per_day_average ? `
                        <tr class="budget-per-day-row">
                            <td>Per Day Average</td>
                            <td>${formatCurrency(data.per_day_average)}</td>
                        </tr>` : ""}
                    </tbody>
                </table>
            </div>
            <p class="budget-disclaimer">* Estimates based on average costs. Actual prices may vary.</p>
        </div>
    `;
}


// -------------------------
// Itinerary Planner
// -------------------------

// Renders the editable itinerary planner.
function renderItineraryEditor(plan) {
    const layout = ensureItineraryContainerStructure();
    if (!layout) return;

    const normalizedPlan = normalizePlanData(plan);
    if (!normalizedPlan.length) {
        layout.status.innerHTML = renderInlineState("info", "No itinerary available.");
        layout.editorHost.innerHTML = "";
        return;
    }

    layout.status.innerHTML = `
        <div class="info-card">
            <div class="info-card-head">
                <span class="info-icon">P</span>
                <strong>${escapeHtml(selectedDestination?.name || "Travel Itinerary")}</strong>
            </div>
            <p>${normalizedPlan.length} day plan is ready below. You can edit, copy, or save it.</p>
        </div>
    `;

    layout.editorHost.innerHTML = `
        <div class="itinerary-toolbar">
            <button type="button" class="secondary-btn" onclick="addItineraryDay()">Add Day</button>
            <button type="button" class="secondary-btn" onclick="copyCurrentPlan()">Copy Plan</button>
            <button type="button" class="secondary-btn" onclick="saveCurrentPlan()">Save Plan</button>
        </div>

        <div class="itinerary-editor-grid">
            ${normalizedPlan.map((item, index) => `
                <div class="itinerary-day-editor" data-day-index="${index}">
                    <input
                        type="text"
                        class="day-label-input"
                        value="${escapeHtml(item.day || `Day ${index + 1}`)}"
                    >
                    <textarea class="activity-editor" rows="5">${escapeHtml((item.activities || []).join("\n"))}</textarea>
                </div>
            `).join("")}
        </div>
    `;

    scrollToElement(layout.container);
    flashSection(layout.container);
}

// Gets an itinerary from the backend.
async function getItinerary() {
    try {
        scrollToElement(document.getElementById("itineraryResult"));
        const days = document.getElementById("days")?.value;
        const preference = document.getElementById("preference")?.value;

        if (!days || !preference) {
            throw new Error("Please enter days and select preference");
        }

        // Show loading state in UI
        const layout = ensureItineraryContainerStructure();
        if (layout) {
            layout.status.innerHTML = renderInlineState("loading", "Generating your itinerary...");
        }

        const response = await fetch(`${API}/itinerary`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ days, preference })
        });

        const data = await response.json();

        if (!data || !data.plan) {
            throw new Error("Invalid itinerary response");
        }

        renderItineraryEditor(data.plan);

        showBanner("Itinerary generated successfully.", "success");

    } catch (error) {
        console.error("Itinerary error:", error);

        const layout = ensureItineraryContainerStructure();
        if (layout) {
            layout.status.innerHTML = renderInlineState("error", error.message);
        }

        showBanner(error.message, "error");
    }
}
// Sets a destination, loads its itinerary, and updates supporting insights.
async function generateDestinationItinerary(destinationId, destinationName) {
    setSelectedDestination(destinationId, destinationName);
    await getItinerary();
    await Promise.allSettled([
        viewRestaurants(destinationName),
        viewEvents(destinationName),
        getWeather(destinationName),
        viewAdvisory(destinationName)
    ]);
}

// Adds a new editable itinerary day card.
function addItineraryDay() {
    const existingPlan = collectItineraryFromEditor();
    const nextDay = existingPlan.length + 1;

    existingPlan.push({
        day: `Day ${nextDay}`,
        activities: ["Add your activity here"]
    });

    renderItineraryEditor(existingPlan);
}

// Copies the current itinerary text to the clipboard.
async function copyCurrentPlan() {
    try {
        const planText = itineraryToText(collectItineraryFromEditor());
        if (!planText.trim()) {
            throw new Error("Generate or edit an itinerary first");
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(planText);
        } else {
            const temp = document.createElement("textarea");
            temp.value = planText;
            document.body.appendChild(temp);
            temp.select();
            document.execCommand("copy");
            temp.remove();
        }

        showBanner("Itinerary copied successfully.", "success");
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// Saves the current itinerary to the backend.
async function saveCurrentPlan() {
    try {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            throw new Error("Login first to save a plan");
        }

        if (!selectedDestination || !selectedDestination.id) {
            throw new Error("Select a destination card before saving");
        }

        const itinerary = collectItineraryFromEditor();
        if (!itinerary.length) {
            throw new Error("No itinerary available to save");
        }

        const data = await apiFetch("/save-plan", {
            method: "POST",
            body: {
                user_id: parseInt(userId, 10),
                destination_id: selectedDestination.id,
                itinerary
            }
        });

        showBanner(data.message || "Plan saved", "success");
        loadSavedPlans();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// -------------------------
// Destination Insights
// -------------------------

// Renders the destination insights panel with styled cards.
function renderInfoPanel(title, cardsMarkup) {
    const sections = ensureTravelInfoPanelStructure();
    if (!sections) return;

    if (sections.selectedLabel && title) {
        sections.selectedLabel.textContent = title;
    }

    if (sections.general) {
        sections.general.innerHTML = cardsMarkup || createSectionHeadingMarkup(title || "Quick View", "No preview is available.");
        scrollToElement(sections.panel);
        flashSection(sections.general.closest(".insight-section") || sections.general);
    }
}

// Loads restaurant recommendations for a selected city.
async function viewRestaurants(place) {
    try {
        renderInsightState("restaurants", `${place} Restaurants`, "loading", `Loading restaurants in ${place}...`, place);

        const data = await apiFetch(`/restaurants/${encodeURIComponent(place)}`);
        const list = normalizeArrayResponse(data);

        const html = list && list.length
            ? list.map(r => `
                <div class="info-card">
                    <div class="info-card-head">
                        <span class="info-icon">🍽</span>
                        <strong>${escapeHtml(r.name || "Restaurant")}</strong>
                    </div>
                    <p>⭐ Rating: ${escapeHtml(r.rating || "N/A")}</p>
                    <p>Type: ${escapeHtml(r.type || "Restaurant")}</p>
                    <p>${escapeHtml(r.address || r.city || place)}</p>
                </div>
            `).join("")
            : createSectionHeadingMarkup("Restaurants", "No restaurants found.");

        renderInsightSection("restaurants", `${place} Restaurants`, html, place);
    } catch (error) {
        renderInsightState("restaurants", `${place} Restaurants`, "error", error.message, place);
    }
}
// Loads static advisory tips for a selected city.
async function viewAdvisory(city) {
    try {
        renderInsightState("advisory", `${city} Advisory`, "loading", `Loading travel advisory for ${city}...`, city);

        const data = await apiFetch(`/advisory/${encodeURIComponent(city)}`);

        const tips = (data.tips || []).map(t => `<li>${escapeHtml(t)}</li>`).join("");

        const html = `
            <div class="info-card">
                <div class="info-card-head">
                    <span class="info-icon">⚠</span>
                    <strong>${escapeHtml(city)}</strong>
                </div>
                <p>${escapeHtml(data.warning || "No warnings")}</p>
                <ul>${tips}</ul>
            </div>
        `;

        renderInsightSection("advisory", `${city} Advisory`, html, city);
    } catch (error) {
        renderInsightState("advisory", `${city} Advisory`, "error", error.message, city);
    }
}
// -------------------------
// Feedback
// -------------------------

// Submits feedback to the backend.
/* =========================================
   Submit User Feedback
========================================= */

window.submitFeedback = async function ()  {

    // Get input values
    const nameInput = document.getElementById("fb_name");
    const emailInput = document.getElementById("fb_email");
    const messageInput = document.getElementById("fb_message");
    const status = document.getElementById("feedbackStatus");

    if (!nameInput || !emailInput || !messageInput || !status) {
        console.error("Feedback form is missing required fields.");
        return;
    }

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const message = messageInput.value.trim();


    // Validate form
    if (!name || !email || !message) {

        status.innerHTML = "Please fill all fields.";
        return;
    }

    try {

        // Send feedback to Flask backend
        const response = await fetch("/submit-feedback", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                name,
                email,
                message
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Feedback submission failed.");
        }

        // Show success message
        status.innerHTML = data.message;

        // Clear form after submit
        nameInput.value = "";
        emailInput.value = "";
        messageInput.value = "";

    } catch (error) {

        console.error("Feedback Error:", error);

        status.innerHTML = "Feedback submission failed.";
    }
}



// Loads saved plans on the profile page.
async function loadSavedPlans() {
    const plansContainer = el("savedPlans");
    const userId = localStorage.getItem("user_id");

    if (!plansContainer) return;

    if (!userId) {
        plansContainer.innerHTML = renderInlineState("info", "Login to view your saved travel plans.");
        return;
    }

    try {
        plansContainer.innerHTML = renderInlineState("loading", "Loading your saved travel plans...");
        const data = await apiFetch(`/my-plans/${userId}`);

        plansContainer.innerHTML = data.length
            ? data.map((plan) => {
                const itineraryText = Array.isArray(plan.itinerary)
                    ? itineraryToText(plan.itinerary)
                    : String(plan.itinerary || "");

                return `
                    <div class="saved-plan-card">
                        <h3>${escapeHtml(plan.destination_name || "Saved Destination")}</h3>
                        <p>${escapeHtml(plan.destination_region || "")}</p>
                        <p>Saved On: ${escapeHtml((plan.created_at || "").replace("T", " ").slice(0, 16))}</p>
                        <textarea rows="7" readonly>${escapeHtml(itineraryText)}</textarea>
                    </div>
                `;
            }).join("")
            : "<p>No saved plans yet.</p>";
    } catch (error) {
        plansContainer.innerHTML = renderInlineState("error", error.message);
    }
}
function createBudgetTableMarkup(data, days) {
    const destinationLabel = data.destination ? `<p class="budget-destination">📍 ${escapeHtml(data.destination)}</p>` : "";

    return `
        <div class="budget-card modern-budget-card">
            <div class="budget-card-header">
                <div class="budget-card-title">💰 Budget Breakdown</div>
                <span class="budget-card-days">${days} Day${days > 1 ? "s" : ""}</span>
            </div>
            ${destinationLabel}
            <div class="budget-table-wrap">
                <table class="budget-table">
                    <thead>
                        <tr>
                            <th>Expense</th>
                            <th>Amount (PKR)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>🏨 Hotel (${days} night${days > 1 ? "s" : ""})</td>
                            <td class="budget-amount">${formatCurrency(data.hotel)}</td>
                        </tr>
                        <tr>
                            <td>🍱 Meals (${days} day${days > 1 ? "s" : ""})</td>
                            <td class="budget-amount">${formatCurrency(data.meals)}</td>
                        </tr>
                        <tr>
                            <td>🚌 Travel</td>
                            <td class="budget-amount">${formatCurrency(data.travel)}</td>
                        </tr>
                        <tr>
                            <td>🎯 Destination Fee</td>
                            <td class="budget-amount">${formatCurrency(data.destination_cost)}</td>
                        </tr>
                        <tr class="budget-total-row">
                            <td><strong>Total Estimate</strong></td>
                            <td class="budget-total-amount"><strong>${formatCurrency(data.total)}</strong></td>
                        </tr>
                        ${data.per_day_average ? `
                        <tr class="budget-per-day-row">
                            <td>Per Day Average</td>
                            <td>${formatCurrency(data.per_day_average)}</td>
                        </tr>` : ""}
                    </tbody>
                </table>
            </div>
            <p class="budget-disclaimer">* Estimates based on average costs. Actual prices may vary.</p>
        </div>
    `;
}

function nearMe() {
    const nearButton = el("nearMeBtn");

    if (!navigator.geolocation) {
        const message = "Your browser does not support location detection.";
        setSectionState("results", "error", message);
        showBanner(message, "error");
        return;
    }

    const isLocalhost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    if (!window.isSecureContext && !isLocalhost) {
        const message = "Location access requires HTTPS or localhost. Please open this app on localhost or a secure HTTPS URL.";
        setSectionState("results", "error", message);
        showBanner(message, "error");
        return;
    }

    setSectionState("results", "loading", "📍 Detecting your location...");
    if (nearButton) {
        nearButton.disabled = true;
        nearButton.setAttribute("aria-busy", "true");
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            setSectionState("results", "loading", "Finding destinations near you...");
            fetch(`${API}/near-me`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    lat: pos.coords.latitude,
                    lng: pos.coords.longitude
                })
            })
            .then(async (res) => {
                const data = await res.json();
                if (!res.ok) {
                    throw new Error(data.error || "Could not load nearby destinations.");
                }
                return data;
            })
            .then(data => {
                const results = Array.isArray(data) ? data : [];
                renderCards(results, "Nearby Destinations");
                if (results.length) {
                    showBanner(`Found ${results.length} destinations near you.`, "success");
                } else {
                    setSectionState("results", "info", "No destinations found within 100km. Try Top Destinations or search by region.");
                    showBanner("No destinations found within 100km.", "info");
                }
            })
            .catch((error) => {
                const message = error.message || "Could not load nearby destinations.";
                setSectionState("results", "error", message);
                showBanner(message, "error");
            })
            .finally(() => {
                if (nearButton) {
                    nearButton.disabled = false;
                    nearButton.removeAttribute("aria-busy");
                }
            });
        },
        (err) => {
            const messages = {
                1: "Location permission denied. Please allow location access in your browser.",
                2: "Location unavailable. Please try again.",
                3: "Location request timed out. Please try again."
            };
            const msg = messages[err.code] || "Could not detect your location.";
            setSectionState("results", "error", msg);
            showBanner(msg, "error");
            if (nearButton) {
                nearButton.disabled = false;
                nearButton.removeAttribute("aria-busy");
            }
        },
        {
            enableHighAccuracy: false,
            timeout: 12000,
            maximumAge: 60000
        }
    );
}

async function viewEvents(city) {
    try {
        renderInsightState("events", `${city} Events`, "loading", `Loading events in ${city}...`, city);

        const data = await apiFetch(`/events/${encodeURIComponent(city)}`);
        const list = normalizeArrayResponse(data);

        const html = list && list.length
            ? list.map(e => `
                <div class="info-card">
                    <div class="info-card-head">
                        <span class="info-icon">🎉</span>
                        <strong>${escapeHtml(e.name || "Event")}</strong>
                    </div>
                    <p>${escapeHtml(e.event_date || "TBA")}</p>
                    <p>${escapeHtml(e.description || "No description available")}</p>
                </div>
            `).join("")
            : createSectionHeadingMarkup("Events", "No events found.");

        renderInsightSection("events", `${city} Events`, html, city);
    } catch (error) {
        renderInsightState("events", `${city} Events`, "error", error.message, city);
    }
}
// -------------------------
// ADDED: Dynamic Content Rendering Functions
// -------------------------

// Reusable function to render content with title and html
function renderContent(title, html) {
    const container = el("dynamicContent");
    if (!container) {
        console.error("dynamicContent container is missing from the page.");
        return;
    }
    container.innerHTML = `
        <div class="dynamic-result-header">
            <h2>${escapeHtml(title)}</h2>
        </div>
        <div class="dynamic-result-content">
            ${html}
        </div>
    `;
    scrollToElement(container);
    flashSection(container);
}

// Show loading state
function renderLoading(message) {
    renderContent("Loading...", `<p class="loading-message">${escapeHtml(message)}</p>`);
}

// Show error message
function renderError(message) {
    renderContent("Error", `<p class="error-message">${escapeHtml(message)}</p>`);
}

// Show no data message
function renderNoData(message) {
    renderContent("No Data", `<p class="no-data-message">${escapeHtml(message)}</p>`);
}

function clearDynamicContent() {
    const container = el("dynamicContent");
    if (container) {
        container.innerHTML = "";
    }
}

// ADDED: Wrap generated cards in a consistent grid.
function wrapDynamicCards(content) {
    return `<div class="dynamic-card-grid">${content}</div>`;
}

// FIXED: Dynamic function for Restaurants
async function getRestaurantsDynamic(city) {
    if (!city) {
        renderError("Please enter a city name.");
        return;
    }

    clearDynamicContent();
    renderLoading(`Loading restaurants for ${city}...`);

    try {
        const response = await fetch(
            `${API}/restaurants/${encodeURIComponent(city)}`
        );

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        const list = normalizeArrayResponse(data);

        if (!list || list.length === 0) {
            renderContent(
                `${city} Restaurants`,
                `<div style="
                    padding: 40px 24px;
                    text-align: center;
                    background: #ffffff;
                    border-radius: 14px;
                    border: 1px solid #e2e8f0;
                ">
                    <p style="font-size:2.5rem;margin:0;">🍽</p>
                    <p style="
                        color:#1e293b;
                        font-size:1rem;
                        font-weight:700;
                        margin:10px 0 6px;
                    ">
                        No restaurants found for
                        <strong>${escapeHtml(city)}</strong>
                    </p>
                    <p style="
                        color:#64748b;
                        font-size:0.88rem;
                        margin:0;
                    ">
                        Try another city or check back later.
                    </p>
                </div>`
            );
            return;
        }

        const html = wrapDynamicCards(
            list.map((r) => `
                <div style="
                    background:#ffffff;
                    border:1px solid #e2e8f0;
                    border-radius:14px;
                    padding:18px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.06);
                ">
                    <h3 style="
                        color:#1e293b;
                        font-size:1rem;
                        font-weight:700;
                        margin:0 0 12px;
                    ">
                        🍽 ${escapeHtml(r.name || "Restaurant")}
                    </h3>

                    <p style="
                        color:#374151;
                        font-size:0.88rem;
                        margin:0 0 6px;
                    ">
                        <strong>⭐ Rating:</strong>
                        ${escapeHtml(String(r.rating || "N/A"))}
                    </p>

                    <p style="
                        color:#374151;
                        font-size:0.88rem;
                        margin:0 0 6px;
                    ">
                        <strong>🍴 Type:</strong>
                        ${escapeHtml(r.type || "Restaurant")}
                    </p>

                    <p style="
                        color:#374151;
                        font-size:0.88rem;
                        margin:0 0 6px;
                    ">
                        <strong>💰 Price:</strong>
                        ${r.price
                            ? escapeHtml(formatCurrency(r.price))
                            : "N/A"
                        }
                    </p>

                    <p style="
                        color:#64748b;
                        font-size:0.82rem;
                        margin:0;
                    ">
                        <strong>📍 City:</strong>
                        ${escapeHtml(r.city || city)}
                    </p>

                    <span style="
                        display:inline-block;
                        margin-top:10px;
                        padding:3px 10px;
                        border-radius:20px;
                        font-size:0.72rem;
                        font-weight:700;
                        background:${
                            r.source === "google_places"
                            ? "#dbeafe" : "#dcfce7"
                        };
                        color:${
                            r.source === "google_places"
                            ? "#1e40af" : "#166534"
                        };
                    ">
                        ${
                            r.source === "google_places"
                            ? "🌐 Google" : "📋 Local"
                        }
                    </span>
                </div>
            `).join("")
        );

        renderContent(`${city} Restaurants`, html);

    } catch (error) {
        console.error("[RESTAURANTS] Error:", error);
        renderError(
            `Could not load restaurants for ${city}.`
        );
    }
}
 async function getEventsDynamic(city) {
    if (!city) {
        renderError("Please enter a city name.");
        return;
    }

    clearDynamicContent();
    renderLoading(`Loading events for ${city}...`);

    try {
        const response = await fetch(
            `${API}/events/${encodeURIComponent(city)}`
        );

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        const list = normalizeArrayResponse(data);

        // ---- Empty State ----
        if (!list || list.length === 0) {
            renderContent(
                `${city} Events`,
                `<div style="
                    padding: 40px 24px;
                    text-align: center;
                    background: #ffffff;
                    border-radius: 14px;
                    border: 1px solid #e2e8f0;
                ">
                    <p style="font-size: 2.5rem; margin: 0;">📅</p>
                    <p style="
                        color: #1e293b;
                        font-size: 1rem;
                        font-weight: 700;
                        margin: 10px 0 6px;
                    ">
                        No events found for
                        <strong>${escapeHtml(city)}</strong>
                    </p>
                    <p style="
                        color: #64748b;
                        font-size: 0.88rem;
                        margin: 0;
                    ">
                        No upcoming events available right now.
                        Check back soon.
                    </p>
                </div>`
            );
            return;
        }

        // ---- Render Events ----
        const html = wrapDynamicCards(
            list.map((eventItem) => {

                // Source badge
                let badgeBg = "#dcfce7";
                let badgeColor = "#166534";
                let badgeText = "📋 Local";

                if (eventItem.source === "predicthq") {
                    badgeBg = "#dbeafe";
                    badgeColor = "#1e40af";
                    badgeText = "🌐 Live";
                } else if (eventItem.source === "ticketmaster") {
                    badgeBg = "#fef9c3";
                    badgeColor = "#854d0e";
                    badgeText = "🎟 Ticketmaster";
                } else if (eventItem.source === "database") {
                    badgeBg = "#dcfce7";
                    badgeColor = "#166534";
                    badgeText = "📋 Local";
                }

                return `
                    <div style="
                        background: #ffffff;
                        border: 1px solid #e2e8f0;
                        border-radius: 14px;
                        overflow: hidden;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                        transition: transform 0.2s ease;
                    ">
                        ${eventItem.image ? `
                            <img
                                src="${escapeHtml(eventItem.image)}"
                                alt="${escapeHtml(eventItem.name || 'Event')}"
                                style="
                                    width: 100%;
                                    height: 160px;
                                    object-fit: cover;
                                    display: block;
                                "
                                onerror="this.style.display='none'"
                            >
                        ` : ""}

                        <div style="padding: 16px;">

                            <h3 style="
                                color: #1e293b;
                                font-size: 1rem;
                                font-weight: 700;
                                margin: 0 0 12px;
                                line-height: 1.4;
                            ">
                                🎉 ${escapeHtml(eventItem.name || "Event")}
                            </h3>

                            <p style="
                                color: #374151;
                                font-size: 0.88rem;
                                margin: 0 0 6px;
                            ">
                                <strong>📅 Date:</strong>
                                ${escapeHtml(eventItem.event_date || "TBA")}
                            </p>

                            <p style="
                                color: #374151;
                                font-size: 0.88rem;
                                margin: 0 0 6px;
                            ">
                                <strong>📍 City:</strong>
                                ${escapeHtml(eventItem.city || city)}
                            </p>

                            <p style="
                                color: #64748b;
                                font-size: 0.85rem;
                                margin: 0 0 14px;
                                line-height: 1.5;
                            ">
                                ${escapeHtml(
                                    eventItem.description ||
                                    "No description available."
                                )}
                            </p>

                            <div style="
                                display: flex;
                                align-items: center;
                                gap: 8px;
                                flex-wrap: wrap;
                            ">
                                ${eventItem.url ? `
                                    
                                        href="${escapeHtml(eventItem.url)}"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        style="
                                            padding: 6px 14px;
                                            background: #0ea5e9;
                                            color: #ffffff;
                                            border-radius: 8px;
                                            font-size: 0.82rem;
                                            font-weight: 700;
                                            text-decoration: none;
                                        "
                                    >
                                        🎟 View Event
                                    </a>
                                ` : ""}

                                <span style="
                                    padding: 4px 12px;
                                    border-radius: 20px;
                                    font-size: 0.75rem;
                                    font-weight: 700;
                                    background: ${badgeBg};
                                    color: ${badgeColor};
                                ">
                                    ${badgeText}
                                </span>

                                ${eventItem.is_upcoming ? `
                                    <span style="
                                        padding: 4px 12px;
                                        border-radius: 20px;
                                        font-size: 0.75rem;
                                        font-weight: 700;
                                        background: #f0fdf4;
                                        color: #15803d;
                                    ">
                                        ✅ Upcoming
                                    </span>
                                ` : ""}
                            </div>

                        </div>
                    </div>
                `;
            }).join("")
        );

        renderContent(`${city} Events`, html);

    } catch (error) {
        console.error("[EVENTS] Error:", error);
        renderError(
            `Could not load events for ${city}. Please try again.`
        );
    }
}
// ====== ITINERARY FUNCTIONS ======

async function getItineraryDynamic(destinationName = "") {
    const days = getValue("days");
    const preference = getValue("preference");

    if (!days || !preference) {
        renderError("Please enter days and select preference.");
        return;
    }

    clearDynamicContent();
    renderLoading("Generating your itinerary...");

    try {
        const data = await apiFetch("/itinerary", {
            method: "POST",
            body: {
                days,
                preference,
                destination_name: destinationName || getActiveDestinationName()
            }
        });

        if (!data || !data.plan) {
            throw new Error("Invalid itinerary response");
        }

        const normalizedPlan = normalizePlanData(data.plan);

        if (!normalizedPlan.length) {
            renderNoData("No itinerary available.");
            return;
        }

        // FIX: Convert to EDITABLE itinerary UI instead of static display
        const editableHtml = `
            <div id="editableItinerary" style="display: flex; flex-direction: column; gap: 20px;">
                ${normalizedPlan.map((item, index) => `
                    <div class="itinerary-day-editor" data-day-index="${index}" style="border: 1px solid #ddd; padding: 15px; border-radius: 6px; background: #f9f9f9;">
                        <div style="margin-bottom: 10px;">
                            <label><strong>Day Label:</strong></label>
                            <input 
                                type="text" 
                                class="day-label-input" 
                                value="${escapeHtml(item.day || `Day ${index + 1}`)}"
                                style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;"
                            >
                        </div>
                        <div style="margin-bottom: 10px;">
                            <label><strong>Activities (one per line):</strong></label>
                            <textarea 
                                class="activity-editor" 
                                rows="5"
                                style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; font-family: monospace;"
                            >${escapeHtml((item.activities || []).join("\n"))}</textarea>
                        </div>
                    </div>
                `).join("")}
                
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button type="button" class="secondary-btn" onclick="addItineraryDay()" style="padding: 10px 15px; cursor: pointer;">➕ Add Day</button>
                    <button type="button" class="secondary-btn" onclick="copyCurrentPlan()" style="padding: 10px 15px; cursor: pointer;">📋 Copy Plan</button>
                    <button type="button" class="primary-btn" onclick="saveEditedItinerary()" style="padding: 10px 15px; cursor: pointer; background: #4CAF50; color: white; border: none; border-radius: 4px;">💾 Save Itinerary</button>
                </div>
            </div>
        `;

        renderContent(destinationName ? `${destinationName} Itinerary - EDITABLE` : "Your Travel Itinerary - EDITABLE", editableHtml);

    } catch (error) {
        renderError(error.message || "Failed to generate itinerary.");
    }
}

// FIX: New function to save edited itinerary
async function saveEditedItinerary() {
    try {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            throw new Error("Login first to save a plan");
        }

        if (!selectedDestination || !selectedDestination.id) {
            throw new Error("Select a destination card before saving");
        }

        // FIX: Collect itinerary from editable fields
        const itinerary = collectItineraryFromEditor();
        if (!itinerary.length) {
            throw new Error("No itinerary available to save");
        }

        const data = await apiFetch("/save-plan", {
            method: "POST",
            body: {
                user_id: parseInt(userId, 10),
                destination_id: selectedDestination.id,
                itinerary
            }
        });

        showBanner(data.message || "Itinerary saved successfully", "success");
        loadSavedPlans();
    } catch (error) {
        showBanner(error.message, "error");
    }
}

// FIX: Ensure collectItineraryFromEditor works correctly for edited fields
function collectItineraryFromEditor() {
    const editors = document.querySelectorAll(".itinerary-day-editor");

    return Array.from(editors).map((editor, index) => {
        const dayInput = editor.querySelector(".day-label-input");
        const activitiesInput = editor.querySelector(".activity-editor");

        const dayLabel = dayInput
            ? dayInput.value.trim()
            : `Day ${index + 1}`;

        const activities = activitiesInput
            ? activitiesInput.value
                  .split("\n")
                  .map(item => item.trim())
                  .filter(Boolean)
            : [];

        return {
            day: dayLabel,
            activities: activities.length ? activities : ["No activities added yet."]
        };
    });
}

// ====== ADVISORY FUNCTIONS ======

async function getAdvisoryDynamic(city) {
    if (!city) {
        renderError("Please enter a city name.");
        return;
    }

    clearDynamicContent();
    renderLoading(`Loading travel advisory for ${city}...`);

    try {
        const data = await apiFetch(`/advisory/${encodeURIComponent(city)}`);
        const tipsHtml = (data.tips || []).map((tip) => `<li>${escapeHtml(tip)}</li>`).join("");

        const html = wrapDynamicCards(`
            <div class="dynamic-card advisory-card">
                <div class="dynamic-card-header">
                    <h3>${escapeHtml(city)} Travel Advisor</h3>
                </div>
                <div class="dynamic-card-body">
                    <p><strong>Warning:</strong> ${escapeHtml(data.warning || "No specific warnings")}</p>
                    ${tipsHtml ? `<p><strong>Suggestions:</strong></p><ul class="dynamic-list">${tipsHtml}</ul>` : ""}
                    <p><strong>Source:</strong> ${escapeHtml(data.source || "Travel Advisor")}</p>
                </div>
            </div>
        `);

        renderContent(`${city} Travel Advisor`, html);
    } catch (error) {
        renderError(error.message || "Failed to load travel advisory.");
    }
}

// ====== EVENT LISTENERS ======

// FIX: Centralized event listeners for homepage buttons and destination cards
function bindHomePageEventListeners() {
    if (el("searchBtn")) {
        el("searchBtn").addEventListener("click", smartSearch);
    }

    if (el("recommendBtn")) {
        el("recommendBtn").addEventListener("click", getRecommendations);
    }

    if (el("nearMeBtn")) {
        el("nearMeBtn").addEventListener("click", nearMe);
    }

    if (el("topDestinationsBtn")) {
        el("topDestinationsBtn").addEventListener("click", loadHomeSuggestions);
    }

    if (el("generateItineraryBtn")) {
        el("generateItineraryBtn").addEventListener("click", async () => {
            await getItinerary();
        });
    }

    if (el("submitFeedbackBtn")) {
        el("submitFeedbackBtn").addEventListener("click", submitFeedback);
    }

    if (el("searchQuery")) {
        el("searchQuery").addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                smartSearch();
            }
        });
    }

    if (el("results")) {
        el("results").addEventListener("click", async (event) => {
            const button = event.target.closest("button[data-action]");
            if (!button) return;

            const action = button.dataset.action;
            const city = (button.dataset.city || "").trim();
            const destinationId = button.dataset.destinationId;

            if (action === "map") {
                await openMap(city);
                return;
            }

            if (action === "budget") {
                await calculateBudgetById(destinationId);
                return;
            }

            if (action === "restaurants") {
                await getRestaurantsDynamic(city);
                return;
            }

            if (action === "events") {
                await getEventsDynamic(city);
                return;
            }

            if (action === "weather") {
                console.log("[Weather] Weather button clicked:", city);
                const weatherInlineContainer = button.closest(".card")?.querySelector(".weather-inline-result") || null;
                await getWeather(city, weatherInlineContainer);
                return;
            }

            if (action === "advisory") {
                await getAdvisoryDynamic(city);
                return;
            }

            if (action === "itinerary") {
                setSelectedDestination(destinationId ? parseInt(destinationId, 10) : null, city);
                await getItinerary();
                await getItineraryDynamic(city);
            }
        });
    }

    if (el("mapQuickActions")) {
        el("mapQuickActions").addEventListener("click", (event) => {
            const button = event.target.closest(".map-action-btn");
            if (!button) return;

            showLocationOnMap(
                Number(button.dataset.lat),
                Number(button.dataset.lng),
                button.dataset.name || "Destination"
            );
        });
    }
}

// ====== APP INITIALIZATION ======

function isAdminPage() {
    return document.body.classList.contains("admin-page");
}

function isHomePage() {
    return Boolean(el("results") || el("travelInfoPanel") || el("itineraryResult") || el("map"));
}

// FIX: Consolidated single DOMContentLoaded handler (merged duplicate blocks)
document.addEventListener("DOMContentLoaded", () => {
    if (isAdminPage()) {
        return;
    }

    loadAppConfig();

    initGoogleLogin();
    prefillFeedbackForm();

    if (isHomePage()) {
        ensureTravelInfoPanelStructure();
        ensureItineraryContainerStructure();

        bindHomePageEventListeners();

        const mapInstance = ensureTravelMap();

        if (mapInstance) {
            window.setTimeout(() => {
                if (travelMap && travelMap.invalidateSize) {
                    travelMap.invalidateSize();
                }
            }, 300);
        }

        if (el("results")) loadHomeSuggestions();
        setSelectedDestination(null, "");

        if (navigator.geolocation && el("map") && mapInstance) {
            navigator.geolocation.getCurrentPosition((position) => {
                const leafletMap = ensureTravelMap();
                if (!leafletMap) return;

                const lat = position.coords.latitude;
                const lng = position.coords.longitude;

                if (!userLocationMarker) {
                    userLocationMarker = L.marker([lat, lng], {
                        title: "Your Location"
                    }).addTo(leafletMap);
                } else {
                    userLocationMarker.setLatLng([lat, lng]);
                }

                userLocationMarker.bindPopup(createPopupMarkup("You are here"));
            });
        }
    }

    if (el("welcomeBox")) loadGreeting();
    if (el("travel_style")) loadPreferences();

    if (el("savedPlans")) loadSavedPlans();

    if (el("saveBtn")) {
        el("saveBtn").addEventListener("click", savePreferences);
    }
    if (el("logoutBtn")) {
        el("logoutBtn").addEventListener("click", logout);
    }
});

