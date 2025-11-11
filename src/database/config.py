import os
from urllib.parse import quote_plus


def _get_required_env(name: str) -> str:
	"""Get required environment variable or raise error."""
	value = os.getenv(name)
	if value is None or value == "":
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value


def build_database_url() -> str:
	"""Build database URL from required environment variables."""
	host = _get_required_env("RPA_DB_HOST")
	port = _get_required_env("RPA_DB_PORT")
	user = _get_required_env("RPA_DB_USER")
	password = _get_required_env("RPA_DB_PASSWORD")
	dbname = _get_required_env("RPA_DB_NAME")
	return f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
