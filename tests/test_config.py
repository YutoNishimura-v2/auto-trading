import pytest
import os
from src.config import Config

def test_config_defaults():
    assert Config.TICKER_LIMIT == 20
    assert Config.MIN_VOLUME == 1000000
    assert Config.IS_SIMULATION is True

def test_env_var_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_NAME", "test-model-v1")
    
    # Need to reload module to pick up env var if it's read at class level directly?
    # Since Config is a class with static attributes read once, we might need to check how it's implemented.
    # In src/config.py, it reads os.getenv() at class definition time.
    # So we can't easily test the ENV override without reloading the module.
    
    import importlib
    import src.config
    importlib.reload(src.config)
    
    assert src.config.Config.GEMINI_MODEL_NAME == "test-model-v1"
