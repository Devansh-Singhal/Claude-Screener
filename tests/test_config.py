import os
from screener import config

def test_token_path_under_home():
    assert config.TOKEN_PATH.name == "token.json"
    assert config.TOKEN_PATH.parent.name == ".screener"

def test_credentials_read_from_env(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "abc")
    monkeypatch.setenv("KITE_API_SECRET", "xyz")
    assert config.api_key() == "abc"
    assert config.api_secret() == "xyz"

def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    try:
        config.api_key()
        assert False, "expected error"
    except config.ConfigError:
        pass
