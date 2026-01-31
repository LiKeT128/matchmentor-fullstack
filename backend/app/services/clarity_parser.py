"""Clarity parser service for executing Clarity JAR to parse Dota 2 replay files."""

import subprocess
import json
import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ClarityParser:
    """Wrapper for Clarity JAR parser execution."""
    
    CLARITY_JAR = Path("backend/clarity.jar")
    TIMEOUT_SECONDS = 300 # Increased timeout for real matches
    
    @classmethod
    def parse_demo_file(cls, demo_path: str) -> Dict[str, Any]:
        """
        Execute Clarity JAR to parse a .dem file.
        
        Handles Windows space path issues by copying to a temporary workspace.
        """
        demo_file = Path(demo_path)
        
        if not demo_file.exists():
            logger.error(f"Demo file not found: {demo_path}")
            raise FileNotFoundError(f"Demo file not found: {demo_path}")
            
        # 1. Determine JAR path
        jar_path = "backend/clarity.jar"
        if not os.path.exists(jar_path):
             # Try app root (Docker or local)
            jar_path = "/app/clarity.jar"
            if not os.path.exists(jar_path):
                jar_path = "clarity.jar" # Last resort
            
        # 2. Workspace Workaround (Fix for 'UnsatisfiedLinkError' or 'NoSuchFileException' due to spaces in path)
        abs_demo_path = os.path.abspath(demo_path)
        abs_jar_path = os.path.abspath(jar_path)
        
        # Trigger workaround if ANY path has spaces on Windows
        use_workaround = (" " in abs_demo_path or " " in abs_jar_path) and os.name == 'nt'
        
        temp_dir = None
        current_demo_path = abs_demo_path
        current_jar_path = abs_jar_path
        exec_cwd = os.path.dirname(abs_demo_path)
        
        if use_workaround:
            # Using C:\mm-test or a system temp without spaces
            temp_root = "C:\\mm-test"
            if not os.path.exists(temp_root):
                try:
                    os.makedirs(temp_root)
                except:
                    temp_root = tempfile.gettempdir()
            
            temp_dir = tempfile.mkdtemp(dir=temp_root)
            logger.info(f"Using workspace workaround: {temp_dir}")
            
            # Copy JAR and DEM to temp dir
            target_jar = os.path.join(temp_dir, "clarity.jar")
            target_demo = os.path.join(temp_dir, demo_file.name)
            
            shutil.copy2(abs_jar_path, target_jar)
            shutil.copy2(abs_demo_path, target_demo)
            
            current_jar_path = "clarity.jar"
            current_demo_path = demo_file.name
            exec_cwd = temp_dir
            logger.info(f"Copied files to workspace. Executing from {exec_cwd}")

        try:
            logger.info(f"Parsing: {current_demo_path} via Clarity ({current_jar_path})")
            
            # 3. Execute Clarity JAR
            # Note: capturing stdout as current jar version might output there
            result = subprocess.run(
                ["java", "-Xmx4G", "-jar", current_jar_path, current_demo_path, "--json"],
                capture_output=True,
                text=True,
                cwd=exec_cwd,
                timeout=cls.TIMEOUT_SECONDS
            )
            
            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                logger.error(f"Clarity failed (code {result.returncode}): {error_msg}")
                # Log first 200 chars of stdout too in case error is there
                if result.stdout:
                    logger.error(f"Stdout snippet: {result.stdout[:200]}")
                raise RuntimeError(f"Clarity failed: {error_msg}")
            
            # 4. Parse JSON from stdout OR file
            parsed_data = None
            
            # Try parsing from stdout (skipping warning lines)
            stdout_lines = result.stdout.splitlines()
            json_blob = ""
            start_capturing = False
            for line in stdout_lines:
                if line.strip().startswith("{"):
                    start_capturing = True
                if start_capturing:
                    json_blob += line + "\n"
            
            if json_blob:
                try:
                    parsed_data = json.loads(json_blob)
                    logger.info("Successfully parsed JSON from stdout")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from stdout: {e}. Output was: {json_blob[:100]}...")
            
            # Fallback: Read from FILE
            if not parsed_data:
                json_output_path = Path(f"{current_demo_path}.json")
                if use_workaround:
                    json_output_path = Path(os.path.join(temp_dir, f"{demo_file.name}.json"))
                
                if json_output_path.exists():
                    logger.info(f"Reading JSON from file: {json_output_path}")
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        parsed_data = json.load(f)
                        logger.info("Successfully parsed JSON from file")
            
            if not parsed_data:
                # Debug info
                logger.error(f"Current dir files: {os.listdir(exec_cwd)}")
                raise ValueError("No valid JSON found in Clarity output or file")
            
            # 5. Adapt structured data
            # If it's a single hero summary, wrap it in the expected 'players' structure
            if "hero" in parsed_data and "players" not in parsed_data:
                logger.info("Recognized Summary-style Clarity output. Adapting structure...")
                hero_data = parsed_data.copy()
                hero_data["player_slot"] = 0
                # Ensure hero_name is set for MatchAnalyzer
                hero_data["hero_name"] = hero_data.get("hero")
                
                # Add rate stats for LaningStageExtractor estimates
                hero_data["gold_per_min"] = hero_data.get("gpm", 0)
                hero_data["xp_per_min"] = hero_data.get("xpm", 0)
                hero_data["last_hits"] = hero_data.get("last_hits", hero_data.get("lh", 0))
                
                # Convert item_timings to purchase_log if available
                if "item_timings" in hero_data:
                    purchase_log = []
                    for item, timestamp in hero_data["item_timings"].items():
                        purchase_log.append({
                            "item": item,
                            "time": int(timestamp),
                            "key": item
                        })
                    hero_data["purchase_log"] = purchase_log
                
                # Mock a players list
                parsed_data = {
                    "match_id": str(parsed_data.get("match_id", "demo")),
                    "players": [hero_data],
                    "heroes": [
                        {
                            "hero_name": hero_data.get("hero"), 
                            "player_slot": 0, 
                            "hero_id": 0,
                            "hero": hero_data.get("hero")
                        }
                    ],
                    "duration_seconds": parsed_data.get("duration", 0),
                    "duration_minutes": int(parsed_data.get("duration", 0) / 60)
                }

            logger.info(f"✓ Parsed: {len(parsed_data.get('players', []))} players found")
            return parsed_data
            
        except subprocess.TimeoutExpired:
            logger.error("Clarity parser timeout")
            raise TimeoutError("Parsing timeout")
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            raise RuntimeError(f"Parsing failed: {str(e)}")
        finally:
            # Cleanup workaround dir
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up workspace: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_dir}: {e}")
