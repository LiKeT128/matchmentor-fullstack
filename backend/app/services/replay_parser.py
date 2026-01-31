"""
Replay parser service for Dota 2 .dem files.

Uses OpenDota's parser primarily, but can fallback to direct Clarity JAR execution.
"""

import os
import logging
from typing import Dict, Any

from app.config import get_settings
from app.services.odota_parser_client import OpenDotaParserClient
from app.services.clarity_parser import ClarityParser

logger = logging.getLogger(__name__)
settings = get_settings()


class ReplayParser:
    """
    Service for parsing Dota 2 replay files.
    """
    
    def __init__(self):
        """Initialize parser client."""
        self.client = OpenDotaParserClient()
        logger.info("ReplayParser initialized")
    
    def parse_replay(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a .dem replay file.
        Attempts OpenDota parser service first, then direct Clarity fallback.
        """
        logger.info(f"Starting parse for {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Replay file not found: {file_path}")
            
        # 1. Try Direct Clarity Parser (Fastest for local dev IF configured/available)
        jar_path = "backend/clarity.jar"
        if os.path.exists(jar_path):
            try:
                logger.info("Direct Clarity JAR found. Attempting direct parsing...")
                match_data = ClarityParser.parse_demo_file(file_path)
                
                if match_data and match_data.get("players"):
                    logger.info("✓ Direct Clarity parsing successful")
                    return match_data
            except Exception as e:
                logger.warning(f"Direct Clarity parsing failed: {e}. Falling back to OpenDota service...")

        # 2. Try OpenDota Parser Service
        try:
            logger.info("Attempting OpenDota Parser Service...")
            match_data = self.client.parse_replay(file_path)
            
            if not match_data.get("players"):
                raise ValueError("Parsed data missing players")
                
            return match_data
            
        except Exception as e:
            logger.error(f"Replay parsing failed via all methods: {e}")
            raise
