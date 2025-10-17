"""Unit tests for config module."""
import pytest
from unittest.mock import patch

from src.config.config import get_rabbitmq_config, get_postgres_dsn


class TestRabbitMQConfig:
    """Test RabbitMQ configuration."""
    
    @patch.dict('os.environ', {
        'RABBITMQ_HOST': 'test-host',
        'RABBITMQ_PORT': '5673',
        'RABBITMQ_VHOST': '/test',
        'RABBITMQ_USER': 'testuser',
        'RABBITMQ_PASSWORD': 'testpass',
        'RABBITMQ_EXCHANGE': 'test-exchange',
        'RABBITMQ_ROUTING_KEY': 'test-queue'
    })
    def test_get_rabbitmq_config_with_env_vars(self):
        """Test config with environment variables."""
        config = get_rabbitmq_config()
        
        assert config['RABBITMQ_HOST'] == 'test-host'
        assert config['RABBITMQ_PORT'] == '5673'
        assert config['RABBITMQ_VHOST'] == '/test'
        assert config['RABBITMQ_USER'] == 'testuser'
        assert config['RABBITMQ_PASSWORD'] == 'testpass'
        assert config['RABBITMQ_EXCHANGE'] == 'test-exchange'
        assert config['RABBITMQ_ROUTING_KEY'] == 'test-queue'
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_rabbitmq_config_defaults(self):
        """Test config with default values."""
        config = get_rabbitmq_config()
        
        assert config['RABBITMQ_HOST'] == 'localhost'
        assert config['RABBITMQ_PORT'] == '5672'
        assert config['RABBITMQ_VHOST'] == '/'
        assert config['RABBITMQ_USER'] == ''
        assert config['RABBITMQ_PASSWORD'] == ''
        assert config['RABBITMQ_EXCHANGE'] == ''
        assert config['RABBITMQ_ROUTING_KEY'] == 'rpa_events'


class TestPostgresConfig:
    """Test PostgreSQL configuration."""
    
    @patch.dict('os.environ', {
        'RPA_DB_HOST': 'test-db-host',
        'RPA_DB_PORT': '5433',
        'RPA_DB_USER': 'testuser',
        'RPA_DB_PASSWORD': 'testpass',
        'RPA_DB_NAME': 'test_db'
    })
    def test_get_postgres_dsn_with_env_vars(self):
        """Test DSN with environment variables."""
        dsn = get_postgres_dsn()
        
        assert 'test-db-host' in dsn
        assert '5433' in dsn
        assert 'testuser' in dsn
        assert 'testpass' in dsn
        assert 'test_db' in dsn
        assert dsn.startswith('postgresql://')
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_postgres_dsn_defaults(self):
        """Test DSN with default values."""
        dsn = get_postgres_dsn()
        
        assert 'postgres' in dsn
        assert '5432' in dsn
        assert 'airflow' in dsn
        assert 'rpa_db' in dsn
        assert dsn.startswith('postgresql://')
