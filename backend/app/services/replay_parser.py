"""Replay parser service with memory-optimized JVM and fallback strategies."""

import subprocess
import json
import os
import shutil
import logging
import glob
import sys
from typing import Dict, Any, Optional, List

from app.services.hero_mapping import get_hero_name
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def log_memory_status() -> None:
    """
    Log current memory usage for debugging OOM issues.
    
    Uses psutil to get process memory information. Silently skips
    if psutil is not available.
    """
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        logger.info(
            f"Memory status - RSS: {mem_info.rss / 1024 / 1024:.1f}MB, "
            f"VMS: {mem_info.vms / 1024 / 1024:.1f}MB, "
            f"Process %: {memory_percent:.1f}%"
        )
    except ImportError:
        logger.debug("psutil not available, skipping memory logging")
    except Exception as e:
        logger.debug(f"Memory logging failed: {e}")


def preprocess_replay(file_path: str) -> Dict[str, Any]:
    """
    Preprocess replay to detect memory issues early.
    
    Returns metadata about file for optimization decisions.
    
    Args:
        file_path: Path to the .dem replay file.
        
    Returns:
        Dictionary with size_mb, is_large flag, and optional warning.
    """
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > 80:
            logger.warning(
                f"Large replay detected: {file_size_mb:.1f}MB. "
                "Memory optimization enabled."
            )
            return {
                "size_mb": file_size_mb,
                "is_large": True,
                "warning": "Large replay - memory limits may apply"
            }
        
        return {"size_mb": file_size_mb, "is_large": False}
    
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return {"size_mb": 0, "is_large": False}


def parse_with_manta(file_path: str) -> Dict[str, Any]:
    """
    Lightweight fallback parser using manta-core library.
    
    Memory footprint: ~200MB (vs Clarity ~500MB+)
    
    Returns core match data:
    - Heroes (player + opponents)
    - Duration, result
    - Basic stats (K/D/A, gold, XP)
    
    Limitation: Less detailed metrics than full Clarity parse.
    
    Args:
        file_path: Path to the .dem replay file.
        
    Returns:
        Dictionary with parsed match data.
        
    Raises:
        Exception: If manta parser is not available or parsing fails.
    """
    try:
        # Try importing manta
        try:
            from manta_core import parse_match
        except ImportError:
            logger.warning("manta_core not available, fallback unavailable")
            raise Exception("Fallback parser not available")
        
        logger.info(f"Parsing with manta: {file_path}")
        
        # Parse with manta
        match_data = parse_match(file_path)
        
        # Extract core fields
        return {
            "match_id": match_data.get("match_id", "unknown"),
            "duration": match_data.get("duration", 0),
            "duration_minutes": int(match_data.get("duration", 0) // 60),
            "hero": match_data.get("player_hero", "Unknown"),
            "result": "win" if match_data.get("winner") else "loss",
            "player_team": match_data.get("player_team", "radiant"),
            "winner": match_data.get("winner", "radiant"),
            "kills": match_data.get("kills", 0),
            "deaths": match_data.get("deaths", 0),
            "assists": match_data.get("assists", 0),
            "gpm": match_data.get("gpm", 0),
            "xpm": match_data.get("xpm", 0),
            "last_hits": match_data.get("last_hits", 0),
            "denies": match_data.get("denies", 0),
            "hero_damage": match_data.get("hero_damage", 0),
            "tower_damage": match_data.get("tower_damage", 0),
            "hero_healing": match_data.get("hero_healing", 0),
            "items": match_data.get("items", []),
            "hero_name": match_data.get("player_hero", "Unknown"), # Ensure hero_name is present
            "heroes": match_data.get("heroes", []), # Extract heroes list if available
            "item_timings": {},
            "parsing_method": "manta_fallback",
            "warning": (
                "Limited analysis available. "
                "For full analytics, try a smaller replay (<50MB) "
                "or upgrade to premium tier."
            )
        }
    
    except ImportError:
        logger.error("Manta parser not available")
        raise Exception("No fallback parser available")
    except Exception as e:
        logger.error(f"Manta parsing failed: {e}")
        raise Exception(f"Both parsers failed: {e}")


class ReplayParser:
    """
    Service for parsing Dota 2 replay files using Clarity parser.
    
    Clarity is a Java-based parser that extracts detailed match data
    from .dem replay files. This implementation includes memory
    optimization for low-memory environments like Railway free tier.
    """
    
    def __init__(self):
        """Initialize parser with Clarity JAR path from config with fallbacks."""
        jar_path = settings.clarity_jar_path
        
        # If configured path doesn't exist, try fallbacks
        if not os.path.exists(jar_path):
            logger.warning(f"JAR not found at configured path: {jar_path}")
            
            # Try absolute /app path (Railway deployment)
            if os.path.exists("/app/clarity.jar"):
                jar_path = "/app/clarity.jar"
                logger.info(f"Using JAR at /app/clarity.jar")
            else:
                # Fallback: relative to backend root
                backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                fallback_path = os.path.join(backend_root, "clarity.jar")
                if os.path.exists(fallback_path):
                    jar_path = fallback_path
                    logger.info(f"Using JAR at backend root: {jar_path}")
        
        self.clarity_jar = jar_path
        logger.info(f"Clarity JAR path: {self.clarity_jar}")
        logger.info(f"JAR exists: {os.path.exists(self.clarity_jar)}")
    
    def parse_replay(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a .dem replay file using Clarity parser.
        
        Includes memory monitoring, OOM detection, timeout handling,
        and fallback to manta parser for large files.
        
        Args:
            file_path: Path to the .dem replay file.
            
        Returns:
            Dictionary containing parsed match data.
            
        Raises:
            Exception: If parsing fails or times out.
        """
        # Log memory status at start
        print(f"DEBUG: ReplayParser.parse_replay called for {file_path}", flush=True)
        log_memory_status()
        
        if not os.path.exists(file_path):
            raise Exception(f"Replay file not found: {file_path}")
        
        if not file_path.endswith('.dem'):
            raise Exception("Invalid file format. Expected .dem file")
        
        preprocess_info = preprocess_replay(file_path)
        print(f"DEBUG: Preprocessing done. Info: {preprocess_info}", flush=True)
        logger.info(f"File size: {preprocess_info.get('size_mb', 0):.1f}MB")
        print("DEBUG: Preprocessing done, resolving Java...", flush=True)

        
        try:
            # Resolve Java path
            java_bin = settings.java_path
            need_fallback = False
            
            if os.path.isabs(java_bin):
                # Absolute path provided - check if it exists
                if not os.path.exists(java_bin):
                    logger.warning(f"Absolute Java path '{java_bin}' does not exist, trying fallback locations")
                    need_fallback = True
            else:
                # Relative path - try to find in PATH
                resolved = shutil.which(java_bin)
                if resolved:
                    java_bin = resolved
                else:
                    logger.warning(f"Java binary '{java_bin}' not found in PATH, trying fallback locations")
                    need_fallback = True
            
            if need_fallback:
                # Fallback paths including Nix JDK locations used by Railway/Nixpacks
                common_paths = [
                    "/nix/store/*-openjdk-*/bin/java",  # Nixpacks JDK (glob pattern)
                    "/usr/bin/java",
                    "/usr/local/bin/java",
                    "/usr/lib/jvm/default-jvm/bin/java",
                    "/opt/java/openjdk/bin/java",
                    "/usr/lib/jvm/java-17-openjdk/bin/java",
                    "/usr/lib/jvm/java-17-openjdk-amd64/bin/java",
                ]
                found = False
                for p in common_paths:
                    if '*' in p:
                        # Use glob for Nix paths with hashes
                        matches = glob.glob(p)
                        if matches:
                            java_bin = matches[0]
                            found = True
                            logger.info(f"Found Java via glob at: {java_bin}")
                            break
                    elif os.path.exists(p):
                        java_bin = p
                        found = True
                        logger.info(f"Found Java at fallback path: {java_bin}")
                        break
                
                if not found:
                    # Last resort: try 'java' from PATH (Heroku Aptfile should add it here)
                    java_from_path = shutil.which("java")
                    if java_from_path:
                        java_bin = java_from_path
                        found = True
                        logger.info(f"Found Java in PATH: {java_bin}")
                    else:
                        # DIAGNOSTICS: Print strict environment info
                        logger.error("CRITICAL: Java not found. Starting diagnostics...")
                        logger.error(f"Current Directory: {os.getcwd()}")
                        logger.error(f"PATH env: {os.environ.get('PATH')}")
                        
                        # List accessible java binaries
                        try:
                            logger.error("Searching /usr/bin for java:")
                            subprocess.run(["ls", "-la", "/usr/bin/java"], capture_output=False)
                            subprocess.run(["find", "/usr/lib/jvm", "-name", "java", "-type", "f"], capture_output=False)
                        except Exception as e:
                            logger.error(f"Diagnostic command failed: {e}")

                        raise FileNotFoundError("Java not found in PATH or fallback locations")
            
            logger.info(f"Using Java at: {java_bin}")
            logger.info(f"Using JAR at: {self.clarity_jar}")

            if not os.path.exists(self.clarity_jar):
                 logger.error(f"CRITICAL: Clarity JAR not found at: {self.clarity_jar}")
                 logger.error(f"Directory listing for .:")
                 subprocess.run(["ls", "-la"], capture_output=False)
                 raise FileNotFoundError(f"Clarity JAR missing: {self.clarity_jar}")

            # Prepare temp file for JSON output to avoid OOM in Python
            # Use replay file path as base for temp file
            json_output_path = f"{file_path}.json"
            err_output_path = f"{file_path}.err"
            
            # Optimized JVM parameters for low-memory free tier environment
            java_cmd = [
                java_bin,
                "-Xmx2G",                                # Max heap: 2GB (as requested)
                "-Xms128m",                              # Initial heap: 128MB
                "-XX:+UseG1GC",                          # G1 Garbage Collector (low pause times)
                "-XX:MaxGCPauseMillis=50",               # Aggressive GC pause control
                "-XX:InitiatingHeapOccupancyPercent=35", # Early GC trigger
                "-XX:ParallelGCThreads=1",               # Single GC thread for free tier
                "-XX:-UseAdaptiveSizePolicy",            # Disable adaptive sizing
                "-XX:TieredStopAtLevel=1",               # Disable C2 compiler (saves memory)
                "-jar",
                self.clarity_jar,
                file_path
            ]
            
            # Log memory status before subprocess
            try:
                with open('/proc/meminfo', 'r') as m:
                    lines = m.readlines()[:3]
                    logger.info(f"Memory before Java: {lines}")
            except Exception:
                pass

            logger.info(f"Running Clarity command: {' '.join(java_cmd)}")
            
            try:
                # Stream both stdout and stderr to files to avoid Python OOM
                with open(json_output_path, "wb") as output_file, open(err_output_path, "wb") as error_file:
                    logger.info(f"Starting subprocess and streaming to {json_output_path}")
                    print(f"DEBUG: Starting Java subprocess...", flush=True)
                    
                    process = subprocess.Popen(
                        java_cmd,
                        stdout=output_file,
                        stderr=error_file,
                        cwd=os.path.dirname(file_path) if os.path.dirname(file_path) else None
                    )
                    
                    print(f"DEBUG: Subprocess started with PID {process.pid}. Waiting...", flush=True)

                    # Wait with 2-minute timeout to prevent hanging (reduced from 5m)
                    try:
                        return_code = process.wait(timeout=120)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        logger.error("Clarity parser timeout (possible OOM)")
                        raise Exception(
                            "Parsing timeout. Replay may be corrupted or too large. "
                            "Try uploading a different file (< 50MB)."
                        )
                
                logger.info(f"Subprocess finished with return code: {return_code}")
                
                # Check for OOM kill
                if return_code == -9:
                    logger.error("Process killed by OOM (-9). Memory limit exceeded.")
                    # Try fallback parser
                    try:
                        logger.info("Attempting fallback manta parser...")
                        return parse_with_manta(file_path)
                    except Exception as fallback_error:
                        logger.error(f"Fallback parser failed: {fallback_error}")
                        raise Exception(
                            "Memory limit exceeded. Replays > 50MB require premium. "
                            "Try uploading a smaller replay."
                        )
                
                if return_code != 0:
                    # Read error output
                    err_content = ""
                    try:
                        with open(err_output_path, "r", encoding="utf-8", errors="ignore") as ef:
                            err_content = ef.read()
                    except Exception:
                        pass
                    logger.error(f"Clarity parser failed. Stderr: {err_content[:1000]}") # Log first 1000 chars
                    raise Exception(f"Clarity parser failed (code {return_code}): {err_content[:500]}...")

                # Check if JSON file was created and has content
                if not os.path.exists(json_output_path) or os.path.getsize(json_output_path) == 0:
                     raise Exception("Clarity produced no output.")

                # Parse JSON from file
                # Skip prefix noise (warnings, logs) to find start of JSON
                logger.info("Reading output file and searching for JSON start '{'")
                content = ""
                with open(json_output_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                json_start = content.find('{')
                if json_start == -1:
                    logger.error(f"No JSON found in output. Content start: {content[:500]}")
                    raise Exception("Clarity output contained no JSON data")
                    
                json_str = content[json_start:]
                raw_data = json.loads(json_str)
                logger.info("JSON successfully parsed from file")
                
                # Log memory after successful parse
                log_memory_status()
                
                result = self._normalize_data(raw_data)

                # =======================
                # DEBUG: Log raw Clarity output structure
                # =======================
                logger.info(f"DEBUG: raw_data.keys() = {list(raw_data.keys())}")
                if "players" in raw_data:
                    logger.info(f"DEBUG: players count = {len(raw_data['players'])}")
                    if raw_data["players"]:
                        first_player = raw_data["players"][0]
                        logger.info(f"DEBUG: First player keys = {list(first_player.keys())}")
                        # Log first 500 chars of first player to see structure
                        import json as json_debug
                        logger.info(f"DEBUG: First player = {json_debug.dumps(first_player, default=str)[:500]}")
                else:
                    logger.warning("DEBUG: NO 'players' key in raw_data!")

                # =======================
                # BUILD HEROES ARRAY (with multiple fallback keys)
                # =======================
                if "players" in raw_data:
                    heroes_list = []
                    logger.info("re-building heroes list explicitly...")
                    
                    for i, player in enumerate(raw_data.get("players", [])):
                        # Try multiple possible keys for hero identification
                        hero_id_raw = player.get("hero_id") or player.get("heroId") or player.get("hero")
                        hero_name_raw = player.get("hero_name") or player.get("heroName") or player.get("localized_name")
                        
                        logger.info(f"  Player {i}: hero_id_raw={hero_id_raw}, hero_name_raw={hero_name_raw}")
                        
                        # Determine hero name
                        if hero_id_raw is not None:
                            try:
                                hero_id = int(hero_id_raw)
                                hero_name = get_hero_name(hero_id)
                                logger.info(f"    -> Mapped ID {hero_id} to {hero_name}")
                            except (ValueError, TypeError):
                                # hero_id_raw might be a string name
                                hero_name = str(hero_id_raw)
                                logger.info(f"    -> Using raw value as name: {hero_name}")
                        elif hero_name_raw:
                            hero_name = str(hero_name_raw)
                            logger.info(f"    -> Using hero_name_raw: {hero_name}")
                        else:
                            hero_name = "unknown"
                            logger.warning(f"    -> NO HERO DATA FOUND for player {i}!")
                        
                        hero = {
                            "player_id": i,
                            "hero_name": hero_name,
                            "team": "radiant" if i < 5 else "dire",
                            "position": player.get("position", "unknown"),
                            "steam_id": str(player.get("steam_id", player.get("account_id", ""))) if player.get("account_id") or player.get("steam_id") else None,
                            "kills": int(player.get("kills", 0)),
                            "deaths": int(player.get("deaths", 0)),
                            "assists": int(player.get("assists", 0))
                        }
                        heroes_list.append(hero)
                    
                    result["heroes"] = heroes_list
                    logger.info(f"✓ Built heroes array with {len(heroes_list)} heroes")

                
                # Check if heroes were extracted successfully
                if not result.get('heroes') or len(result['heroes']) == 0:
                    logger.warning("Clarity parsed successfully but found NO HEROES. Attempting fallback.")
                    # Force fallback
                    try:
                        return parse_with_manta(file_path)
                    except Exception as fallback_error:
                        logger.error(f"Fallback after empty heroes failed: {fallback_error}")
                        # Return original result if fallback fails, better than nothing
                        return result
                        
                return result

            finally:
                # Cleanup output files
                if os.path.exists(json_output_path):
                    logger.info(f"Cleaning up temporary JSON file: {json_output_path}")
                    os.remove(json_output_path)
                if os.path.exists(err_output_path):
                    os.remove(err_output_path)
            
        except subprocess.TimeoutExpired:
            raise Exception("Replay parsing timeout (>5 minutes)")
        except json.JSONDecodeError as e:
            raise Exception(f"Clarity output not valid JSON: {str(e)}")
        except FileNotFoundError:
            raise Exception("Java not found. Please install Java Runtime Environment")
        except Exception as e:
            raise Exception(f"Parsing error: {str(e)}")
    
    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw Clarity output into consistent format.
        
        Args:
            raw_data: Raw JSON from Clarity parser.
            
        Returns:
            Normalized match data dictionary.
        """
        duration_seconds = raw_data.get("duration", 0)
        
        # Build detailed heroes list
        heroes_list = self._extract_all_heroes(raw_data)
        
        # Extract metadata
        normalized = {
            "match_id": str(raw_data.get("match_id", "")),
            "duration_minutes": duration_seconds // 60,
            "duration_seconds": duration_seconds,
            "hero_name": raw_data.get("hero", "Unknown"),
            "result": self._determine_result(raw_data),
            
            # Core stats
            "kills": raw_data.get("kills", 0),
            "deaths": raw_data.get("deaths", 0),
            "assists": raw_data.get("assists", 0),
            "gpm": raw_data.get("gpm", 0),
            "xpm": raw_data.get("xpm", 0),
            "last_hits": raw_data.get("last_hits", 0),
            "denies": raw_data.get("denies", 0),
            
            # Combat stats
            "hero_damage": raw_data.get("hero_damage", 0),
            "tower_damage": raw_data.get("tower_damage", 0),
            "hero_healing": raw_data.get("hero_healing", 0),
            
            # Items
            "items": raw_data.get("items", []),
            "item_timings": raw_data.get("item_timings", {}),
            
            # Additional frontend data
            "heroes": heroes_list,
            "steam_id": self._extract_steam_id(raw_data),
            
            # Full data for advanced analysis
            "full_data": raw_data
        }
        
        logger.info(f"Successfully normalized data for Match ID: {normalized['match_id']}, Hero: {normalized['hero_name']}")
        return normalized

    def _extract_steam_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract a primary Steam ID if possible."""
        # Check players for one matching specific criteria if needed
        # For now, if 'player_steam_id' exists in root, use it
        if data.get("steam_id"):
            return str(data.get("steam_id"))
            
        # Or check if any player is marked as 'is_local' or similar (Clarity specific)
        if "players" in data:
            for p in data["players"]:
                # account_id is 32-bit, steam_id needs to be 64-bit
                account_id = p.get("account_id")
                steam_id = p.get("steam_id")
                
                if steam_id:
                    return str(steam_id)
                
                # Conversion logic: 64-bit ID = 32-bit ID + 76561197960265728
                if account_id and int(account_id) > 0:
                    steam_64 = int(account_id) + 76561197960265728
                    logger.info(f"✓ Extracted steam_id: {steam_64} (from account_id {account_id})")
                    return str(steam_64)
                    
        return None


    def _extract_all_heroes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract detailed hero list from match data.
        
        Args:
            data: Raw match data.
            
        Returns:
            List of hero dictionaries.
        """
        heroes = []
        
        if "players" in data:
            for i, p in enumerate(data["players"]):
                # Use hero_id if available, otherwise try 'hero' (which might be int or str)
                hero_id_val = p.get("hero_id", p.get("hero"))
                
                # If it's an integer, map it. If it's a string, use it.
                if isinstance(hero_id_val, int):
                    h_name = get_hero_name(hero_id_val)
                elif isinstance(hero_id_val, str) and hero_id_val.isdigit():
                    h_name = get_hero_name(int(hero_id_val))
                else:
                    h_name = str(hero_id_val) if hero_id_val else "unknown"

                # Cleanup if it already has npc_dota_hero prefix or not (mapping adds it)
                if not h_name.startswith("npc_dota_hero_") and h_name != "unknown":
                     # Double check if it's not unknown_ID
                     if "unknown_" not in h_name:
                         # Assume it might be a raw name if not mapped
                         pass

                team = "radiant" if i < 5 else "dire"
                
                hero_entry = {
                    "player_id": i,
                    "hero_name": h_name,
                    "team": team,
                    "position": p.get("position", "unknown"),
                    "steam_id": str(p.get("steam_id", p.get("account_id", ""))) or None,
                    "kills": p.get("kills", 0),
                    "deaths": p.get("deaths", 0),
                    "assists": p.get("assists", 0),
                }
                heroes.append(hero_entry)
        
        # Log results for debugging
        logger.info(f"✓ Built heroes array with {len(heroes)} heroes")
        if heroes:
            logger.info(f"Sample hero: {heroes[0]['hero_name']}")
            
        return heroes

    
    def _determine_result(self, data: Dict[str, Any]) -> str:
        """
        Determine match result from parsed data.
        
        Args:
            data: Parsed match data.
            
        Returns:
            WIN, LOSS, or ABANDONED.
        """
        if data.get("abandoned", False):
            return "ABANDONED"
        
        player_team = data.get("player_team", "radiant")
        winner = data.get("winner", "")
        
        if player_team.lower() == winner.lower():
            return "WIN"
        return "LOSS"
    
    def validate_jar(self) -> bool:
        """
        Check if Clarity JAR exists and is accessible.
        
        Returns:
            True if JAR is valid, False otherwise.
        """
        return os.path.exists(self.clarity_jar)
