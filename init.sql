-- For user login credentials
CREATE TABLE userlogindetails (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

-- For user personal data
CREATE TABLE userpersonaldetails (
    username VARCHAR(50) PRIMARY KEY REFERENCES userlogindetails(username),
    dob DATE,
    weight REAL,
    height REAL, -- Store height in meters
    email VARCHAR(100),
    phone VARCHAR(20)
);

-- For managing user sessions
CREATE TABLE sessiondetails (
    sessionid UUID PRIMARY KEY,
    username VARCHAR(50) REFERENCES userlogindetails(username),
    expiredate TIMESTAMP NOT NULL
);

-- To track the user's current day in their plan
CREATE TABLE day_user (
    username VARCHAR(50) PRIMARY KEY REFERENCES userlogindetails(username),
    day INTEGER NOT NULL DEFAULT 1
);

-- To store the daily exercise plan and progress
CREATE TABLE exercise_plan (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) REFERENCES userlogindetails(username),
    day INTEGER NOT NULL,
    pushups INTEGER,
    squats INTEGER,
    situps INTEGER,
    pushups_completed INTEGER,
    squats_completed INTEGER,
    situps_completed INTEGER,
    completion REAL,
    UNIQUE(username, day)
);