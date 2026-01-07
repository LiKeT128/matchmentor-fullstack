"""Tests for replay parser service."""

import pytest
from unittest.mock import patch, MagicMock
import json

from app.services.replay_parser import ReplayParser


class TestReplayParser:
    """Test suite for ReplayParser service."""
    
    def test_parser_initialization(self):
        """Test parser initializes with config."""
        parser = ReplayParser()
        assert parser.clarity_jar is not None
    
    def test_parse_replay_file_not_found(self):
        """Test parsing non-existent file."""
        parser = ReplayParser()
        
        with pytest.raises(Exception) as exc_info:
            parser.parse_replay("/nonexistent/file.dem")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_parse_replay_invalid_extension(self, tmp_path):
        """Test parsing file with wrong extension."""
        parser = ReplayParser()
        
        # Create temp file with wrong extension
        wrong_file = tmp_path / "match.txt"
        wrong_file.write_text("fake content")
        
        with pytest.raises(Exception) as exc_info:
            parser.parse_replay(str(wrong_file))
        
        assert ".dem" in str(exc_info.value)
    
    @patch("subprocess.run")
    def test_parse_replay_success(self, mock_run, tmp_path):
        """Test successful replay parsing."""
        parser = ReplayParser()
        
        # Create mock .dem file
        dem_file = tmp_path / "match.dem"
        dem_file.write_bytes(b"fake replay data")
        
        # Mock Clarity output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "match_id": "12345",
                "duration": 2400,
                "hero": "Invoker",
                "gpm": 500,
                "xpm": 600,
                "kills": 10,
                "deaths": 5,
                "assists": 15,
                "last_hits": 200,
                "denies": 20,
                "hero_damage": 25000,
                "tower_damage": 5000,
                "items": ["blink", "aghanims"],
                "winner": "radiant",
                "player_team": "radiant"
            }),
            stderr=""
        )
        
        result = parser.parse_replay(str(dem_file))
        
        assert result["match_id"] == "12345"
        assert result["duration_minutes"] == 40
        assert result["hero_name"] == "Invoker"
        assert result["result"] == "WIN"
        assert result["kills"] == 10
        assert result["gpm"] == 500
    
    @patch("subprocess.run")
    def test_parse_replay_clarity_error(self, mock_run, tmp_path):
        """Test handling Clarity parser error."""
        parser = ReplayParser()
        
        dem_file = tmp_path / "match.dem"
        dem_file.write_bytes(b"corrupt data")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Failed to parse replay"
        )
        
        with pytest.raises(Exception) as exc_info:
            parser.parse_replay(str(dem_file))
        
        assert "Clarity parser failed" in str(exc_info.value)
    
    @patch("subprocess.run")
    def test_parse_replay_json_error(self, mock_run, tmp_path):
        """Test handling invalid JSON from Clarity."""
        parser = ReplayParser()
        
        dem_file = tmp_path / "match.dem"
        dem_file.write_bytes(b"valid replay")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="{ invalid json",
            stderr=""
        )
        
        with pytest.raises(Exception) as exc_info:
            parser.parse_replay(str(dem_file))
        
        assert "not valid JSON" in str(exc_info.value)
    
    def test_determine_result_win(self):
        """Test result determination for win."""
        parser = ReplayParser()
        
        result = parser._determine_result({
            "player_team": "radiant",
            "winner": "radiant",
            "abandoned": False
        })
        
        assert result == "WIN"
    
    def test_determine_result_loss(self):
        """Test result determination for loss."""
        parser = ReplayParser()
        
        result = parser._determine_result({
            "player_team": "radiant",
            "winner": "dire",
            "abandoned": False
        })
        
        assert result == "LOSS"
    
    def test_determine_result_abandoned(self):
        """Test result determination for abandoned match."""
        parser = ReplayParser()
        
        result = parser._determine_result({
            "player_team": "radiant",
            "winner": "radiant",
            "abandoned": True
        })
        
        assert result == "ABANDONED"
