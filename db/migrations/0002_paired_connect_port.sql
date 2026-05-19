-- Add connect_port to paired_devices (Spec §3.1 — Android 11+ uses a
-- separate connection port distinct from the pairing port).
ALTER TABLE paired_devices ADD COLUMN connect_port INTEGER;

PRAGMA user_version = 2;
