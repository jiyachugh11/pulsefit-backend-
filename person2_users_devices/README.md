# Person 2 — Users, Accounts and Device/Profile Data

## What this demonstrates
- PostgreSQL tables with primary keys, a unique email and a foreign key.
- MongoDB documents with flexible fields per device model.
- A query to find devices whose `sensors` list includes `ecg`.

## Setup
1. Install/start PostgreSQL and MongoDB Community Server.
2. Create a PostgreSQL database named `pulsefit` (for example in pgAdmin).
3. Install packages: `python -m pip install -r requirements.txt`.
4. Set your PostgreSQL connection details as environment variables. In PowerShell, for the current terminal:

```powershell
$env:PGDATABASE="pulsefit"
$env:PGUSER="postgres"
$env:PGPASSWORD="YOUR_POSTGRES_PASSWORD"
python users_devices_demo.py
```

MongoDB uses `mongodb://localhost:27017/` by default. Change `MONGO_URI` if yours differs. The Python script creates its tables and sample records, so running `schema.sql` separately is optional. Do not put your actual password into screenshots or shared source files.

## Key explanation
PostgreSQL holds data with a stable structure (users and device registration). MongoDB holds model-specific metadata, so `PW501` can have `ecg` and `skin_temperature` fields while `PB101` does not need them. The application links the two databases using `device_id`; they do not automatically synchronize.

## Screenshot ideas
Show `schema.sql`, PostgreSQL rows in pgAdmin, and a MongoDB document in Compass. Only use terminal output as execution evidence if you ran the script successfully.
