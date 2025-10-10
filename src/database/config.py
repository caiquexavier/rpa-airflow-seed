import os
from urllib.parse import quote_plus

try:
	from dotenv import load_dotenv  # type: ignore
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
	# dotenv is optional; env vars may already be set in the shell/CI
	pass


def get_env(name: str, default: str | None = None) -> str:
	value = os.getenv(name, default)
	if value is None:
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value


def build_database_url() -> str:
	host = get_env("RPA_DB_HOST", "postgres")
	port = get_env("RPA_DB_PORT", "5432")
	user = get_env("RPA_DB_USER", "airflow")
	password = get_env("RPA_DB_PASSWORD", "airflow")
	dbname = get_env("RPA_DB_NAME", "rpa_db")
	return f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
