"""Analysis logger utility for tracking match analysis steps."""

import logging
import time
from typing import List, Dict, Any, Optional

class AnalysisLogger:
    """
    Collects granular logs and events during match analysis.
    Provides transparency into which formulas were used and what data was extracted.
    """
    
    def __init__(self, match_id: str, hero_name: str):
        self.match_id = match_id
        self.hero_name = hero_name
        self.start_time = time.time()
        self.logs: List[Dict[str, Any]] = []
        self.data_sources: Dict[str, str] = {}
        
    def log(self, step: str, message: str, level: str = "INFO", data: Optional[Dict[str, Any]] = None):
        """Add a log entry."""
        entry = {
            "timestamp": time.time() - self.start_time,
            "step": step,
            "level": level,
            "message": message,
            "data": data or {}
        }
        self.logs.append(entry)
        
        # Also log to standard python logger
        py_logger = logging.getLogger(f"analysis.{step}")
        if level == "INFO":
            py_logger.info(f"[{self.hero_name}] {message}")
        elif level == "WARNING":
            py_logger.warning(f"[{self.hero_name}] {message}")
        elif level == "ERROR":
            py_logger.error(f"[{self.hero_name}] {message}")

    def set_data_source(self, component: str, source: str):
        """Track which data source was used for a component."""
        self.data_sources[component] = source
        self.log("DATA_SOURCE", f"Using {source} for {component}", data={"component": component, "source": source})

    def get_summary(self) -> Dict[str, Any]:
        """Return the collected logs as a serializable dict."""
        return {
            "match_id": self.match_id,
            "hero_name": self.hero_name,
            "total_duration": time.time() - self.start_time,
            "data_sources": self.data_sources,
            "trace": self.logs
        }
