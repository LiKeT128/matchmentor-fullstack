"""Clarity parser service for executing Clarity JAR to parse Dota 2 replay files."""

import subprocess
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ClarityParser:
    """Wrapper for Clarity JAR parser execution."""
    
    CLARITY_JAR = Path("/app/clarity.jar")
    TIMEOUT_SECONDS = 60
    
    @classmethod
    async def parse_demo_file(cls, demo_path: str) -> Dict[str, Any]:
        """
        Execute Clarity JAR to parse a .dem file.
        
        Clarity writes JSON output to {demo_path}.json file, not stdout.
        This method reads from that file after execution.
        
        Args:
            demo_path: Path to the .dem file.
            
        Returns:
            Dictionary containing parsed match data.
            
        Raises:
            FileNotFoundError: Demo file doesn't exist or output file not found.
            TimeoutError: Parsing took >60s.
            json.JSONDecodeError: Invalid JSON from Clarity.
            RuntimeError: Non-zero return code.
        """
        demo_file = Path(demo_path)
        json_output_path = Path(f"{demo_path}.json")
        
        # 1. Check if demo file exists
        if not demo_file.exists():
            logger.error(f"Demo file not found: {demo_path}")
            raise FileNotFoundError(f"Demo file not found: {demo_path}")
        
        # 2. Check if JAR exists
        jar_path = str(cls.CLARITY_JAR)
        if not os.path.exists(jar_path):
            fallback_path = "/app/clarity.jar"
            if os.path.exists(fallback_path):
                jar_path = fallback_path
            else:
                logger.error(f"Clarity JAR not found at {cls.CLARITY_JAR}")
                raise FileNotFoundError(f"Clarity JAR not found at {cls.CLARITY_JAR}")
        
        try:
            logger.info(f"Parsing: {demo_path}")
            
            # 3. Execute Clarity JAR
            result = subprocess.run(
                ["java", "-Xmx2G", "-jar", jar_path, str(demo_path), "--json"],
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            
            # 4. Check return code
            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"Clarity failed with return code {result.returncode}")
                logger.error(f"Stderr: {error_msg}")
                raise RuntimeError(f"Clarity failed: {error_msg}")
            
            # 5. KEY FIX: Read from FILE, not stdout!
            if not json_output_path.exists():
                logger.error(f"Clarity output file not found: {json_output_path}")
                raise FileNotFoundError(f"Clarity output not found: {json_output_path}")
            
            # Read and parse JSON from file
            with open(json_output_path, 'r', encoding='utf-8') as f:
                parsed_data = json.load(f)
            
            num_players = len(parsed_data.get('players', []))
            logger.info(f"✓ Parsed: {num_players} players found")
            return parsed_data
        
        except subprocess.TimeoutExpired:
            logger.error(f"Clarity parser timeout after {cls.TIMEOUT_SECONDS} seconds")
            raise TimeoutError("Parsing timeout >60s")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Clarity: {e}")
            raise ValueError(f"Invalid JSON: {e}")
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}")
            raise RuntimeError(f"Parsing failed: {str(e)}")
