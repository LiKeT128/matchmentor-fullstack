"""
Replay parser service for Dota 2 .dem files.

Uses OpenDota's parser (HTTP service based on Clarity 3.1.3) to extract detailed match data.
This replaces the old subprocess-based Clarity parser.
"""

import os
import logging
from typing import Dict, Any

from app.config import get_settings
from app.services.odota_parser_client import OpenDotaParserClient

logger = logging.getLogger(__name__)
settings = get_settings()


class ReplayParser:
    """
    Service for parsing Dota 2 replay files using OpenDota parser.
    """
    
    def __init__(self):
        """Initialize parser client."""
        # parser_port can be configured via env, defaults to 5600 inside the client
        self.client = OpenDotaParserClient()
        logger.info("ReplayParser initialized with OpenDota backend")
    
    def parse_replay(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a .dem replay file.
        
        Args:
            file_path: Path to the .dem replay file.
            
        Returns:
            Dictionary containing parsed match data.
            
        Raises:
            Exception: If parsing fails.
        """
        logger.info(f"Starting parse for {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Replay file not found: {file_path}")
            
        try:
            # Delegate to OpenDota client
            match_data = self.client.parse_replay(file_path)
            
            # Additional processing/validation if needed
            if not match_data.get("players"):
                raise ValueError("Parsed data missing players")
                
            return match_data
            
        except Exception as e:
            logger.error(f"Replay parsing failed: {e}")
            raise
