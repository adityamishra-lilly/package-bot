import os
from typing import Optional
from dotenv import load_dotenv


load_dotenv()

class Config:
    "Centralized configuration for the application."

    def __init__(self):
        self.GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")    
        self.GITHUB_COMMAND_TOKEN = os.environ.get("GITHUB_COMMAND_TOKEN")
        self.GITHUB_ORG = os.environ.get("GITHUB_ORG")
        self.TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE")
        self.TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return getattr(self, key, default)
    
config = Config()