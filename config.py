"""PE-Scout 全局配置"""

import os
from pathlib import Path

# Auto-load .env file (local dev)
_ENV_FILE = Path(__file__).parent / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key not in os.environ:
                    os.environ[key] = value

# Streamlit Cloud secrets (st.secrets) override .env
try:
    import streamlit as _st
    _secrets = _st.secrets
    for _k in ("DEEPSEEK_API_KEY", "GERMAN_LAW_DIR"):
        if _k in _secrets and _k not in os.environ:
            os.environ[_k] = str(_secrets[_k])
except Exception:
    pass  # Not running under Streamlit

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"

# LLM Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# Alternative LLM backends (OpenAI-compatible)
LLM_BACKENDS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_key_env": "DASHSCOPE_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}

# Agent settings
AGENT_MAX_ITERATIONS = 5
AGENT_TEMPERATURE = 0.3
AGENT_MAX_TOKENS = 2048

# German law documents path (configurable for different machines)
GERMAN_LAW_DIR = os.getenv(
    "GERMAN_LAW_DIR",
    str(PROJECT_ROOT / "legal_docs")
)

# RAG settings
RAG_TOP_K = 5
RAG_CHUNK_SIZE = 2000
RAG_CHUNK_OVERLAP = 200

# Knowledge Graph settings
KG_MAX_DEPTH = 3
KG_NODE_LIMIT = 50
