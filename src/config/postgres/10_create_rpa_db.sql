DO $$
BEGIN
	IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rpa_db') THEN
		PERFORM pg_catalog.pg_sleep(0);
		EXECUTE 'CREATE DATABASE rpa_db';
	END IF;
END
$$;
