-- Run this in cqlsh. The partition key groups a device's readings by date.
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
