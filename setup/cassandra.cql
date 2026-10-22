-- Original partitioned table, unchanged.
CREATE KEYSPACE IF NOT EXISTS pulsefit
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
USE pulsefit;
CREATE TABLE IF NOT EXISTS sensor_readings_by_device_day (
    device_id text,
    reading_date date,
    reading_ts timestamp,
    heart_rate int,
    steps int,
    spo2 int,
    latitude double,
    longitude double,
    PRIMARY KEY ((device_id, reading_date), reading_ts)
) WITH CLUSTERING ORDER BY (reading_ts ASC);
-- The original three readings, anchored to a reproducible demonstration date.
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T09:58:00Z', 78, 120, 98, 12.9716, 80.2206);
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T09:59:00Z', 82, 145, 97, 12.9717, 80.2207);
INSERT INTO sensor_readings_by_device_day
(device_id, reading_date, reading_ts, heart_rate, steps, spo2, latitude, longitude)
VALUES ('PB101', '2026-10-11', '2026-10-11T10:00:00Z', 80, 160, 98, 12.9718, 80.2208);
