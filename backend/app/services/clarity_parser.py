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
        
        Execute: java -Xmx2G -jar /app/clarity.jar {demo_path} --json
        Returns: Parsed JSON from stdout
        
        Args:
            demo_path: Path to the .dem file.
            
        Returns:
            Dictionary containing parsed match data.
            
        Raises:
            FileNotFoundError: Demo file doesn't exist.
            TimeoutError: Parsing took >60s.
            json.JSONDecodeError: Invalid JSON from Clarity.
            RuntimeError: Non-zero return code.
        """
        # 1. Check if file exists
        if not os.path.exists(demo_path):
            logger.error(f"Demo file not found: {demo_path}")
            raise FileNotFoundError(f"Demo file doesn't exist: {demo_path}")
        
        # 2. Check if JAR exists
        jar_path = str(cls.CLARITY_JAR)
        if not os.path.exists(jar_path):
            # Try fallback path
            fallback_path = "/app/clarity.jar"
            if os.path.exists(fallback_path):
                jar_path = fallback_path
            else:
                logger.error(f"Clarity JAR not found at {cls.CLARITY_JAR}")
                raise FileNotFoundError(f"Clarity JAR not found at {cls.CLARITY_JAR}")
        
        logger.info(f"Parsing demo file: {demo_path}")
        logger.info(f"Using Clarity JAR: {jar_path}")
        
        # 3. Execute Java command
        java_cmd = [
            "java",
            "-Xmx2G",
            "-jar",
            jar_path,
            demo_path,
            "--json"
        ]
        
        try:
            logger.info(f"Running command: {' '.join(java_cmd)}")
            
            # Run subprocess with timeout
            result = subprocess.run(
                java_cmd,
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS,
                check=False
            )
            
            # 4. Check return code
            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"Clarity parser failed with return code {result.returncode}")
                logger.error(f"Stderr: {error_msg}")
                raise RuntimeError(
                    f"Clarity parser failed with return code {result.returncode}: {error_msg}"
                )
            
            # 5. Parse JSON from stdout
            stdout = result.stdout
            if not stdout.strip():
                logger.error("Clarity parser returned empty output")
                raise RuntimeError("Clarity parser returned empty output")
            
            try:
                parsed_data = json.loads(stdout)
                logger.info("Successfully parsed Clarity JSON output")
                return parsed_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Clarity output: {e}")
                logger.error(f"Output (first 500 chars): {stdout[:500]}")
                raise json.JSONDecodeError(
                    f"Invalid JSON from Clarity: {e}",
                    stdout,
                    e.pos
                )
                
        except subprocess.TimeoutExpired:
            logger.error(f"Clarity parser timeout after {cls.TIMEOUT_SECONDS} seconds")
            raise TimeoutError(
                f"Parsing took longer than {cls.TIMEOUT_SECONDS} seconds"
            )
        except FileNotFoundError:
            logger.error("Java executable not found in PATH")
            raise RuntimeError("Java executable not found in PATH")
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}")
            raise RuntimeError(f"Parsing failed: {str(e)}")
