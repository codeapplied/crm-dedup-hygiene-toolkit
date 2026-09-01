import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DedupRules:
    score_weights: dict[str, int] = field(default_factory=dict)
    skip_pairs: list[dict] = field(default_factory=list)


@dataclass
class Settings:
    db_path: str
    pipedrive_api_token: str | None
    pipedrive_domain: str | None


def load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("CRMDEDUP_DB_PATH", "data/crmdedup.db"),
        pipedrive_api_token=os.getenv("PIPEDRIVE_API_TOKEN"),
        pipedrive_domain=os.getenv("PIPEDRIVE_DOMAIN"),
    )


def load_rules(config_path: str = "config/rules.yaml") -> DedupRules:
    path = Path(config_path)
    if not path.exists():
        return DedupRules()
    with path.open() as f:
        raw = yaml.safe_load(f) or {}
    return DedupRules(
        score_weights=raw.get("score_weights", {}),
        skip_pairs=raw.get("skip_pairs", []),
    )


settings = load_settings()
