CREATE DATABASE travel_app;
USE travel_app;
-- =====================================================
-- USERS TABLE
-- =====================================================

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- DESTINATIONS TABLE
-- =====================================================

CREATE TABLE destinations (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    type VARCHAR(100),

    region VARCHAR(100),

    cost INT DEFAULT 0,

    weather VARCHAR(100),

    best_season VARCHAR(100),

    activities TEXT,

    tags TEXT,

    safety_rating FLOAT DEFAULT 0,

    user_rating FLOAT DEFAULT 0,

    image VARCHAR(255),

    hotel_cost_per_day INT DEFAULT 0,

    meal_cost_per_day INT DEFAULT 0,

    travel_cost INT DEFAULT 0,

    latitude DECIMAL(10,7),

    longitude DECIMAL(10,7)
);

-- =====================================================
-- USER PREFERENCES
-- =====================================================

CREATE TABLE user_preferences (
    user_id INT PRIMARY KEY,

    budget_range INT,

    travel_style VARCHAR(100),

    duration INT,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE
);

-- =====================================================
-- USER RATINGS
-- =====================================================

CREATE TABLE user_ratings (
    user_id INT,

    destination_id INT,

    rating INT,

    PRIMARY KEY(user_id, destination_id),

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (destination_id)
    REFERENCES destinations(id)
    ON DELETE CASCADE
);

-- =====================================================
-- WEATHER CACHE
-- =====================================================

CREATE TABLE weather_cache (
    city VARCHAR(100) PRIMARY KEY,

    temperature FLOAT,

    description VARCHAR(100),

    humidity INT,

    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- =====================================================
-- AI MODELS
-- =====================================================

CREATE TABLE ai_models (
    id INT AUTO_INCREMENT PRIMARY KEY,

    model_name VARCHAR(100) UNIQUE,

    status ENUM('active','inactive')
    DEFAULT 'inactive'
);

INSERT INTO ai_models (model_name, status)
VALUES ('Content-Based Recommender', 'inactive');

-- =====================================================
-- RESTAURANTS
-- =====================================================

CREATE TABLE restaurants (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    city VARCHAR(100) NOT NULL,

    rating DECIMAL(2,1) DEFAULT 4.0,

    type VARCHAR(50),

    price INT DEFAULT 0
);

INSERT INTO restaurants
(name, city, rating, type, price)
VALUES

('Monal', 'Islamabad', 4.7, 'Pakistani', 2500),

('Cafe De Hunza', 'Hunza', 4.5, 'Cafe', 1500),

('Food Street', 'Lahore', 4.6, 'Desi', 1200),

('Skardu Grill', 'Skardu', 4.4, 'BBQ', 1800),

('Coastal Kitchen', 'Gwadar', 4.2, 'Seafood', 2200);


-- =====================================================
-- SAVED PLANS
-- =====================================================

CREATE TABLE saved_plans (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    destination_id INT NOT NULL,

    itinerary LONGTEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (destination_id)
    REFERENCES destinations(id)
    ON DELETE CASCADE
);


-- =====================================================
-- DESTINATION DATA
-- =====================================================

INSERT INTO destinations (

    name,
    type,
    region,
    cost,
    weather,
    best_season,
    activities,
    tags,
    safety_rating,
    user_rating,
    image,
    hotel_cost_per_day,
    meal_cost_per_day,
    travel_cost,
    latitude,
    longitude

)

VALUES

(
'Hunza',

'Adventure Nature',

'Gilgit Baltistan',

25000,

'Cold',

'Summer',

'Hiking, Lakes, Sightseeing',

'nature,mountains,trekking,honeymoon',

4.5,

4.8,

'/static/images/hunza.jpg',

3000,

1500,

5000,

36.3167,

74.6500
),

(
'Murree',

'Family Relaxation',

'Punjab',

15000,

'Cool',

'All Year',

'Sightseeing, Mall Road',

'family,relaxation,hills',

4.2,

4.5,

'/static/images/murree.jpg',

2500,

1200,

4000,

33.9070,

73.3943
),

(
'Skardu',

'Adventure Nature',

'Gilgit Baltistan',

30000,

'Cold',

'Summer',

'Trekking, Camping',

'nature,adventure,lakes',

4.7,

4.9,

'/static/images/skardu.jpg',

3500,

1800,

6000,

35.2971,

75.6333
),

(
'Gwadar Beach',

'Beach Relaxation',

'Balochistan',

20000,

'Hot',

'Winter',

'Beach, Boating',

'beach,relaxation,honeymoon,sea',

4.0,

4.3,

'/static/images/gawadar.jpg',

2000,

1000,

6000,

25.1264,

62.3225
),

(
'Swat Valley',

'Nature Adventure',

'Khyber Pakhtunkhwa',

22000,

'Cold',

'Summer',

'Waterfalls, Lakes',

'nature,adventure,lakes',

4.4,

4.6,

'/static/images/swat.jgp.jpeg',

2500,

1300,

5000,

35.2227,

72.4258
),

(
'Lahore',

'Historical Culture',

'Punjab',

12000,

'Hot',

'Winter',

'Food Street, Museums',

'historical,culture,food',

4.1,

4.4,

'/static/images/lahore.jpg',

2200,

1200,

3000,

31.5204,

74.3587
);

-- =====================================================
-- CHECK DATA
-- =====================================================

SELECT * FROM destinations;

SELECT * FROM restaurants;

SELECT * FROM events;
-- =====================================================
-- TRIP BOOKINGS TABLE
-- =====================================================

CREATE TABLE trip_bookings (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    destination_id INT NOT NULL,

    trip_date DATE,

    travelers INT DEFAULT 1,

    total_cost INT DEFAULT 0,

    booking_status ENUM(
        'pending',
        'confirmed',
        'cancelled'
    ) DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (destination_id)
    REFERENCES destinations(id)
    ON DELETE CASCADE
);


-- =====================================================
-- BOOKING TABLE
-- =====================================================

CREATE TABLE bookings (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    destination_id INT NOT NULL,

    booking_date DATE,

    persons INT DEFAULT 1,

    amount_paid INT DEFAULT 0,

    booking_type VARCHAR(100),

    status ENUM(
        'pending',
        'confirmed',
        'cancelled'
    ) DEFAULT 'pending',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (destination_id)
    REFERENCES destinations(id)
    ON DELETE CASCADE
);

-- =====================================================
-- REVIEWS TABLE
-- =====================================================

CREATE TABLE reviews (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    destination_id INT NOT NULL,

    review_text TEXT,

    rating FLOAT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (destination_id)
    REFERENCES destinations(id)
    ON DELETE CASCADE
);

-- =====================================================
-- PAYMENTS TABLE
-- =====================================================

CREATE TABLE payments (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    booking_id INT NOT NULL,

    amount INT NOT NULL,

    payment_method VARCHAR(50),

    payment_status ENUM(
        'pending',
        'paid',
        'failed'
    ) DEFAULT 'pending',

    transaction_id VARCHAR(255),

    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE CASCADE,

    FOREIGN KEY (booking_id)
    REFERENCES bookings(id)
    ON DELETE CASCADE
);


-- =====================================================
-- ADVISORIES TABLE
-- =====================================================

CREATE TABLE advisories (

    id INT AUTO_INCREMENT PRIMARY KEY,

    city VARCHAR(100) UNIQUE,

    warning TEXT,

    tips TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO advisories
(city, warning, tips)
VALUES

(
'Hunza',
'Mountain roads can be slow after rain or snowfall.',
'Carry warm clothes, keep cash and avoid late-night driving.'
),

(
'Skardu',
'Weather changes quickly and routes may close.',
'Carry power banks and confirm hotel bookings early.'
),

(
'Murree',
'Weekend traffic can be heavy during tourist season.',
'Travel on weekdays and book parking-aware hotels.'
),

(
'Gwadar',
'Extreme daytime heat may occur.',
'Carry water and avoid afternoon beach travel.'
);

-- =====================================================
-- EVENTS TABLE
-- =====================================================

CREATE TABLE events (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    city VARCHAR(100) NOT NULL,

    event_date DATE NOT NULL,

    description TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO events
(name, city, event_date, description)
VALUES

(
'Hunza Cultural Night',
'Hunza',
'2026-06-15',
'Traditional food, local music and handicrafts.'
),

(
'Skardu Spring Festival',
'Skardu',
'2026-05-20',
'Seasonal performances and family activities.'
),

(
'Murree Winter Gala',
'Murree',
'2026-12-10',
'Snow activities, food stalls and live performances.'
),

(
'Gwadar Coastal Festival',
'Gwadar',
'2026-11-05',
'Beachfront community event with local art and seafood.'
);

-- =====================================================
-- SAMPLE REVIEWS
-- =====================================================

INSERT INTO reviews
(user_id, destination_id, review_text, rating)
VALUES

(1, 1, 'Amazing mountain views and peaceful environment.', 4.8),

(1, 2, 'Perfect family destination with cool weather.', 4.5);

-- =====================================================
-- SAMPLE BOOKINGS
-- =====================================================

INSERT INTO bookings
(user_id, destination_id, booking_date, persons, amount_paid, booking_type, status)
VALUES

(1, 1, '2026-06-10', 2, 50000, 'Family Tour', 'confirmed'),

(1, 2, '2026-07-15', 3, 30000, 'Weekend Trip', 'pending');

-- =====================================================
-- SAMPLE PAYMENTS
-- =====================================================

INSERT INTO payments
(user_id, booking_id, amount, payment_method, payment_status, transaction_id)
VALUES

(1, 1, 50000, 'JazzCash', 'paid', 'TXN10001'),

(1, 2, 30000, 'EasyPaisa', 'pending', 'TXN10002');
DROP TABLE IF EXISTS feedback;
CREATE TABLE feedback (

    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NULL,

    name VARCHAR(100),

    email VARCHAR(100),

    message TEXT NOT NULL,

    rating INT DEFAULT 5,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
    ON DELETE SET NULL
);
INSERT IGNORE INTO restaurants (name, city, rating, type, price)
VALUES
    ('Mall Road Cafe',          'Murree', 4.3, 'Cafe',        1200),
    ('Pine View Restaurant',    'Murree', 4.1, 'Continental', 1800),
    ('Murree Brew Restaurant',  'Murree', 4.2, 'Pakistani',   1500),
    ('Bhurban Dining Hall',     'Murree', 4.0, 'Buffet',      2000),
    ('Cecil Hotel Restaurant',  'Murree', 4.4, 'Continental', 2500);
    INSERT IGNORE INTO restaurants (name, city, rating, type, price)
VALUES
    ('Coastal Kitchen',           'Gwadar', 4.2, 'Seafood',     2200),
    ('Pearl Continental Gwadar',  'Gwadar', 4.5, 'Continental', 3000),
    ('Port View Cafe',            'Gwadar', 4.0, 'Cafe',        1000),
    ('Gwadar Fish Market Grill',  'Gwadar', 4.3, 'BBQ Seafood', 1500);
    
    INSERT INTO destinations
    (name, type, region, cost, weather, best_season, activities, safety_rating, user_rating,
     hotel_cost_per_day, meal_cost_per_day, travel_cost, latitude, longitude)
SELECT * FROM (
    SELECT 'Hunza Valley'  AS name, 'valley'       AS type, 'Gilgit Baltistan' AS region, 15000 AS cost,
           'Cold'    AS weather, 'Summer' AS best_season,
           'Trekking, Sightseeing, Cultural Tours' AS activities,
           4.5 AS safety_rating, 4.8 AS user_rating,
           5000 AS hotel_cost_per_day, 2000 AS meal_cost_per_day, 3000 AS travel_cost,
           36.3167 AS latitude, 74.65 AS longitude
    UNION ALL
    SELECT 'Murree', 'hill station', 'Punjab', 10000, 'Mild', 'Summer',
           'Hiking, Picnics, Horse Riding, Family Trips',
           4.2, 4.3, 3000, 1500, 2000, 33.9045, 73.3903
    UNION ALL
    SELECT 'Lahore', 'city', 'Punjab', 20000, 'Hot', 'Winter',
           'Historical Sites, Shopping, Food Tours',
           4.0, 4.5, 4000, 2500, 1000, 31.5497, 74.3436
    UNION ALL
    SELECT 'Swat Valley', 'valley', 'Khyber Pakhtunkhwa', 12000, 'Moderate', 'Spring',
           'Boating, Trekking, Cultural Festivals',
           4.3, 4.6, 3500, 1800, 2500, 35.2227, 72.4258
    UNION ALL
    SELECT 'Karachi', 'city', 'Sindh', 18000, 'Hot', 'Winter',
           'Beaches, Shopping, Historical Sites',
           3.8, 4.1, 4500, 2200, 1500, 24.8607, 67.0011
    UNION ALL
    SELECT 'Gwadar', 'coastal city', 'Balochistan', 15000, 'Hot', 'Winter',
           'Beach Walks, Snorkeling, Seafood, Sunrise Views',
           4.0, 4.2, 4000, 1800, 3000, 25.1216, 62.3254
    UNION ALL
    SELECT 'Skardu', 'mountain city', 'Gilgit Baltistan', 20000, 'Cold', 'Summer',
           'K2 Base Camp Trek, Satpara Lake, Shangrila Resort',
           4.4, 4.7, 5000, 2000, 4000, 35.2966, 75.6356
    UNION ALL
    SELECT 'Naran', 'valley', 'Khyber Pakhtunkhwa', 13000, 'Cold', 'Summer',
           'Saif-ul-Malook Lake, Babusar Pass, Camping, Trekking',
           4.2, 4.5, 3500, 1500, 2500, 34.9027, 73.6544
    UNION ALL
    SELECT 'Neelum Valley', 'valley', 'Azad Kashmir', 14000, 'Cold', 'Summer',
           'Trekking, Ratti Gali Lake, Camping, Romantic Getaway',
           4.3, 4.6, 3500, 1500, 2500, 34.7018, 73.9693
    UNION ALL
    SELECT 'Taxila', 'historical site', 'Punjab', 8000, 'Moderate', 'Winter',
           'Gandhara Museum, Ancient Buddhist Ruins, Historical Tours',
           4.5, 4.2, 2000, 1000, 1500, 33.7451, 72.7977
) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM destinations LIMIT 1);

    


     INSERT INTO destinations (
    name, type, region, cost, weather, best_season,
    activities, tags, safety_rating, user_rating, image,
    hotel_cost_per_day, meal_cost_per_day, travel_cost,
    latitude, longitude
)
VALUES

(
    'Naran',
    'Valley',
    'Khyber Pakhtunkhwa',
    13000,
    'Cold',
    'Summer',
    'Saif-ul-Malook Lake, Babusar Pass, Camping, Trekking, Fishing',
    'adventure,nature,lake,mountain,trekking',
    4.2, 4.5,
    '/static/images/naran.jpg',
    3500, 1500, 2500,
    34.9027, 73.6544
),

(
    'Neelum Valley',
    'Valley',
    'Azad Kashmir',
    14000,
    'Cold',
    'Summer',
    'Trekking, Ratti Gali Lake, Camping, Nature Walks, Rafting',
    'honeymoon,romantic,couple,scenic,nature,adventure,relaxing',
    4.3, 4.6,
    '/static/images/neelum.jpg',
    3500, 1500, 2500,
    34.7018, 73.9693
),

(
    'Fairy Meadows',
    'Meadow',
    'Gilgit Baltistan',
    18000,
    'Cold',
    'Summer',
    'Nanga Parbat View, Camping, Trekking, Photography, Stargazing',
    'adventure,camping,mountain,trekking,scenic,nature',
    4.0, 4.7,
    '/static/images/fairy_meadows.jpg',
    4000, 1500, 4000,
    35.3828, 74.5891
),

(
    'Taxila',
    'Historical Site',
    'Punjab',
    8000,
    'Moderate',
    'Winter',
    'Gandhara Museum, Ancient Buddhist Ruins, Sirkap City, Historical Tours',
    'historical,heritage,culture,archaeology,educational,museum',
    4.5, 4.2,
    '/static/images/taxila.jpg',
    2000, 1000, 1500,
    33.7451, 72.7977
),

(
    'Chitral',
    'Valley',
    'Khyber Pakhtunkhwa',
    16000,
    'Cold',
    'Summer',
    'Kalash Festival, Shandur Polo Match, Tirich Mir View, Cultural Tours, Trekking',
    'culture,adventure,festival,historical,trekking,nature,scenic',
    4.0, 4.4,
    '/static/images/chitral.jpg',
    3500, 1500, 3500,
    35.8503, 71.7864
),

(
    'Bahawalpur',
    'Historical City',
    'Punjab',
    9000,
    'Hot',
    'Winter',
    'Derawar Fort, Cholistan Desert Safari, Noor Mahal, Historical Tours',
    'historical,desert,fort,heritage,culture,architecture',
    4.1, 4.0,
    '/static/images/bahawalpur.jpg',
    2500, 1000, 2000,
    29.3956, 71.6722
),

(
    'Karachi',
    'Coastal City',
    'Sindh',
    18000,
    'Hot',
    'Winter',
    'Clifton Beach, Sea View, Manora Island, Shopping, Historical Sites',
    'beach,coastal,city,seafood,historical,shopping',
    3.8, 4.1,
    '/static/images/karachi.jpg',
    4500, 2200, 1500,
    24.8607, 67.0011
);

SELECT name, region, cost FROM destinations ORDER BY id;

SELECT city, COUNT(*) AS total FROM restaurants GROUP BY city ORDER BY city;

SELECT city, COUNT(*) AS total FROM events GROUP BY city ORDER BY city;

SELECT city FROM advisories ORDER BY city;

INSERT INTO events (name, city, event_date, description) VALUES
('Taxila Heritage Walk', 'Taxila', '2026-11-15', 'Guided archaeological tour of Gandhara ruins and Taxila Museum.'),
('Buddhist Ruins Festival', 'Taxila', '2026-11-20', 'Cultural program celebrating Gandhara civilization with local artists.'),
('Taxila Winter Carnival', 'Taxila', '2026-12-05', 'Food stalls, handicrafts exhibition and family entertainment.'),
('Fairy Meadows Star Night', 'Fairy Meadows', '2026-07-10', 'Stargazing camp at the base of Nanga Parbat with bonfire and local food.'),
('Fairy Meadows Trek Festival', 'Fairy Meadows', '2026-08-05', 'Group trekking event with photography competition and camping.'),
('Nanga Parbat View Camp', 'Fairy Meadows', '2026-09-20', 'Overnight camping with guided nature walks and mountain views.'),
('Chitral Kalash Festival', 'Chitral', '2026-07-15', 'Traditional Kalash tribe spring festival with dance, music and rituals.'),
('Shandur Polo Festival', 'Chitral', '2026-08-07', 'Famous high altitude polo match between Chitral and Gilgit teams.'),
('Chitral Cultural Night', 'Chitral', '2026-09-12', 'Local music, traditional food and handicrafts display event.'),
('Bahawalpur Desert Festival', 'Bahawalpur', '2026-11-20', 'Cholistan desert festival with camel racing and folk music.'),
('Derawar Fort Light Show', 'Bahawalpur', '2026-11-10', 'Night light and sound show at the historic Derawar Fort.'),
('Bahawalpur Food Mela', 'Bahawalpur', '2026-12-15', 'Traditional Saraiki cuisine festival with cultural performances.'),
('Naran Lake Festival', 'Naran', '2026-07-25', 'Saif-ul-Malook lake celebration with boat rides and local food.'),
('Naran Trekkers Meet', 'Naran', '2026-08-20', 'Annual trekkers gathering with guided hikes and camping.'),
('Neelum Valley Nature Festival', 'Neelum Valley', '2026-07-10', 'Nature walks, river rafting and cultural evening in Azad Kashmir.'),
('Ratti Gali Lake Camp', 'Neelum Valley', '2026-08-15', 'Camping event at Ratti Gali Lake with guided trekking.');
SELECT name, city, event_date 
FROM events 
WHERE city IN (
    'Taxila', 'Chitral', 'Fairy Meadows', 
    'Bahawalpur', 'Naran', 'Neelum Valley'
)
ORDER BY city;

INSERT IGNORE INTO restaurants 
(name, city, rating, type, price)
VALUES
-- Taxila
('Taxila Dhaba',              'Taxila',        4.2, 'Pakistani',   800),
('Heritage Cafe',             'Taxila',        4.0, 'Cafe',       1000),
('Gandhara Restaurant',       'Taxila',        4.1, 'Pakistani',   950),

-- Chitral
('Chitral Dine',              'Chitral',       4.3, 'Pakistani',  1200),
('Kalash Restaurant',         'Chitral',       4.1, 'Local Food', 1000),
('Hindu Kush Cafe',           'Chitral',       4.2, 'Cafe',       1100),

-- Bahawalpur
('Bahawalpur Biryani',        'Bahawalpur',    4.4, 'Pakistani',   900),
('Desert View Cafe',          'Bahawalpur',    4.0, 'Cafe',       1100),
('Noor Mahal Dining',         'Bahawalpur',    4.3, 'Pakistani',  1500),

-- Karachi
('Karachi BBQ',               'Karachi',       4.5, 'BBQ',        2000),
('Burns Road Nihari',         'Karachi',       4.6, 'Pakistani',  1500),
('Student Biryani Karachi',   'Karachi',       4.4, 'Pakistani',  1200),
('Kolachi Restaurant',        'Karachi',       4.7, 'Seafood',    3000),

-- Naran
('Naran Food Corner',         'Naran',         4.2, 'Local Food', 1000),
('Kaghan Restaurant',         'Naran',         4.0, 'Pakistani',  1200),
('Lake View Cafe Naran',      'Naran',         4.3, 'Cafe',       1300),

-- Neelum Valley
('Neelum View Dhaba',         'Neelum Valley', 4.1, 'Pakistani',   900),
('AJK Food House',            'Neelum Valley', 4.0, 'Local Food',  800),
('Neelum River Cafe',         'Neelum Valley', 4.2, 'Cafe',       1000),

-- Lahore
('Lahore Chaye Khana',        'Lahore',        4.5, 'Cafe',       1200),
('Haveli Restaurant',         'Lahore',        4.7, 'Pakistani',  2500),
('Cooco Den Lahore',          'Lahore',        4.6, 'Pakistani',  2200),
('Andaaz Restaurant',         'Lahore',        4.4, 'Pakistani',  2000),

-- Murree
('Mall Road Cafe',            'Murree',        4.3, 'Cafe',       1200),
('Murree Brew Restaurant',    'Murree',        4.2, 'Pakistani',  1500),
('Pine View Restaurant',      'Murree',        4.1, 'Continental',1800),
('Bhurban Dining Hall',       'Murree',        4.0, 'Buffet',     2000),
('Cecil Hotel Restaurant',    'Murree',        4.4, 'Continental',2500),

-- Skardu
('Skardu Grill',              'Skardu',        4.4, 'BBQ',        1800),
('Shangrila Resort Dining',   'Skardu',        4.6, 'Continental',3000),
('Upper Kachura Cafe',        'Skardu',        4.3, 'Cafe',       1500),
('Baltistan Kitchen',         'Skardu',        4.2, 'Local Food', 1200),

-- Fairy Meadows
('Fairy Meadows Base Camp Cafe',  'Fairy Meadows', 4.5, 'Cafe',       1500),
('Nanga Parbat View Dhaba',       'Fairy Meadows', 4.3, 'Pakistani',  1200),
('Raikot Camp Restaurant',        'Fairy Meadows', 4.2, 'Local Food', 1000),

-- Hunza
('Cafe De Hunza',             'Hunza',         4.5, 'Cafe',       1500),
('Mountain Taste',            'Hunza',         4.4, 'Pakistani',  1800),
('Serena Hunza Restaurant',   'Hunza',         4.6, 'Continental',2500),
('Eagle Nest Dining',         'Hunza',         4.3, 'Pakistani',  2000),

-- Swat
('Swat Serena Restaurant',    'Swat',          4.5, 'Pakistani',  1800),
('Malam Jabba Cafe',          'Swat',          4.3, 'Cafe',       1200),
('Mingora Food Court',        'Swat',          4.2, 'Local Food', 1000),
('White Palace Dining',       'Swat',          4.4, 'Pakistani',  2000),

-- Gwadar
('Coastal Kitchen',           'Gwadar',        4.4, 'Seafood',    2200),
('Pearl Continental Gwadar',  'Gwadar',        4.5, 'Continental',3000),
('Port View Cafe',            'Gwadar',        4.0, 'Cafe',       1000),
('Gwadar Fish House',         'Gwadar',        4.3, 'Seafood',    1800);
ALTER TABLE users ADD COLUMN is_admin TINYINT(1) DEFAULT 0;
UPDATE users SET is_admin = 1 WHERE email = 'nh564129@gmail.com';
