-- Connect to pulsefit first. Preserve the supplied table and column names.
BEGIN;
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(20) PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES users(user_id),
    device_name VARCHAR(100) NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Additive migration: no DROP, rename, or replacement of existing records.
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);
UPDATE users SET first_name = split_part(full_name, ' ', 1),
    last_name = CASE WHEN strpos(full_name, ' ') > 0
        THEN substr(full_name, strpos(full_name, ' ') + 1) ELSE '' END
WHERE first_name IS NULL;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_type VARCHAR(50) NOT NULL DEFAULT 'wearable';
ALTER TABLE devices ADD COLUMN IF NOT EXISTS brand VARCHAR(100) NOT NULL DEFAULT 'PulseFit';
CREATE TABLE IF NOT EXISTS challenges (
    challenge_id VARCHAR(20) PRIMARY KEY,
    challenge_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL CHECK (end_date >= start_date)
);
INSERT INTO users (user_id, full_name, first_name, last_name, email) VALUES
('U101', 'Jiya', 'Jiya', '', 'jiya@example.test'),
('U102', 'Rahul', 'Rahul', '', 'rahul@example.test'),
('U103', 'Priya', 'Priya', '', 'priya@example.test'),
('U104', 'Aman', 'Aman', '', 'aman@example.test')
ON CONFLICT (user_id) DO NOTHING;
INSERT INTO devices (device_id, user_id, device_name, device_type, brand) VALUES
('PB101', 'U101', 'PulseBand X1', 'fitness band', 'PulseFit'),
('PW501', 'U102', 'PulseWatch Pro', 'smartwatch', 'PulseFit')
ON CONFLICT (device_id) DO NOTHING;
INSERT INTO challenges VALUES ('CH101', 'October Step Challenge', '2026-10-01', '2026-10-31')
ON CONFLICT (challenge_id) DO NOTHING;
COMMIT;
