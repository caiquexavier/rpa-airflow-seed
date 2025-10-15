-- Create database if it does not exist using psql's \gexec (runs outside function context)
SELECT 'CREATE DATABASE rpa_db'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'rpa_db'
);
\gexec
