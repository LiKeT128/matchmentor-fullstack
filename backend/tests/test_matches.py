"""Tests for matches endpoints."""

import pytest
from io import BytesIO
from app.models.match import Match
from app.models.user import User


class TestMatchesEndpoints:
    """Test suite for /api/matches endpoints."""
    
    def test_list_matches_empty(self, client, auth_headers):
        """Test listing matches when none exist."""
        response = client.get("/api/matches", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_matches_unauthenticated(self, client):
        """Test listing matches without auth."""
        response = client.get("/api/matches")
        
        assert response.status_code == 403
    
    def test_get_match_not_found(self, client, auth_headers):
        """Test getting non-existent match."""
        response = client.get("/api/matches/999", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_upload_invalid_file_type(self, client, auth_headers):
        """Test uploading non-.dem file."""
        file_content = b"not a replay file"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        
        response = client.post(
            "/api/matches/upload",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code == 400
        assert ".dem" in response.json()["detail"]
    
    def test_upload_unauthenticated(self, client):
        """Test uploading without auth."""
        file_content = b"fake replay data"
        files = {"file": ("match.dem", BytesIO(file_content), "application/octet-stream")}
        
        response = client.post("/api/matches/upload", files=files)
        
        assert response.status_code == 403
    
    def test_delete_match_not_found(self, client, auth_headers):
        """Test deleting non-existent match."""
        response = client.delete("/api/matches/999", headers=auth_headers)
        
        assert response.status_code == 404

    def test_compare_matches(self, client, auth_headers, db):
        """Test comparing two matches."""
        # Get user
        user = db.query(User).filter(User.email == "test@example.com").first()
        
        # Create two matches
        m1 = Match(
            match_id="111", player_id=user.id, hero_name="Axe", 
            duration_minutes=30, result="WIN",
            metrics={"overall_score": 50, "combat_kda": 3.0, "farming_gpm": 400}
        )
        m2 = Match(
            match_id="222", player_id=user.id, hero_name="Axe", 
            duration_minutes=35, result="WIN",
            metrics={"overall_score": 60, "combat_kda": 4.5, "farming_gpm": 450}
        )
        db.add_all([m1, m2])
        db.commit()
        
        response = client.get(f"/api/matches/compare/{m1.id}/{m2.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["improvements"]["overall_score"] == 10
        assert data["improvements"]["combat_kda"] == 1.5
        assert data["improvements"]["farming_gpm"] == 50

    def test_get_match_hero_data_fallback(self, client, auth_headers, db):
        """Test that get_match ensures heroes array exists even if missing in DB."""
        user = db.query(User).filter(User.email == "test@example.com").first()
        
        # Create match with parsed_data structure but NO 'heroes' key (simulating old data)
        # But WITH 'players' so fallback logic can work
        match = Match(
            match_id="99999", 
            player_id=user.id, 
            hero_name="Juggernaut",
            duration_minutes=30, 
            result="WIN",
            metrics={"overall_score": 100},
            parsed_data={
                "players": [
                    {"hero_name": "npc_dota_hero_juggernaut", "steam_id": "123"},
                    {"hero_name": "npc_dota_hero_cm", "steam_id": "456"}
                ]
                # 'heroes' key intentionally missing
            }
        )
        db.add(match)
        db.commit()
        
        response = client.get(f"/api/matches/{match.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "parsed_data" in data
        assert "heroes" in data["parsed_data"]
        assert len(data["parsed_data"]["heroes"]) == 2
        heroes = data["parsed_data"]["heroes"]
        assert any(h["hero_name"] == "npc_dota_hero_juggernaut" for h in heroes)
        assert any(h["hero_name"] == "npc_dota_hero_cm" for h in heroes)


class TestMatchFilters:
    """Test match listing filters."""
    
    def test_filter_by_hero(self, client, auth_headers):
        """Test filtering matches by hero name."""
        response = client.get(
            "/api/matches",
            params={"hero": "Invoker"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_filter_by_result(self, client, auth_headers):
        """Test filtering matches by result."""
        response = client.get(
            "/api/matches",
            params={"result": "WIN"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_pagination(self, client, auth_headers):
        """Test match pagination."""
        response = client.get(
            "/api/matches",
            params={"skip": 0, "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200

    def test_duplicate_match_different_users(self, client, db):
        """Test that multiple users can analyze the same match ID."""
        # Create two users
        u1 = User(email="u1@example.com", password_hash="pw", tier="pro")
        u2 = User(email="u2@example.com", password_hash="pw", tier="pro")
        db.add_all([u1, u2])
        db.commit()
        
        # Create match for u1
        m1 = Match(
            match_id="12345", player_id=u1.id, hero_name="Axe",
            duration_minutes=30, result="WIN", metrics={"gpm": 500}
        )
        db.add(m1)
        db.commit()
        
        # Simulate u2 uploading same match (should work now)
        m2 = Match(
            match_id="12345", player_id=u2.id, hero_name="Axe",
            duration_minutes=30, result="LOSS", metrics={"gpm": 400}
        )
        db.add(m2)
        db.commit()
        
        # Verify both exist
        count = db.query(Match).filter(Match.match_id == "12345").count()
        assert count == 2
        
        # Verify unique ownership
        m1_db = db.query(Match).filter(Match.player_id == u1.id, Match.match_id == "12345").first()
        m2_db = db.query(Match).filter(Match.player_id == u2.id, Match.match_id == "12345").first()
        
        assert m1_db.id != m2_db.id
        assert m1_db.result == "WIN"
        assert m2_db.result == "LOSS"
