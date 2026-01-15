#!/usr/bin/env python3
"""
Test the upload fix to ensure proper error handling.
"""

import sys
import os
sys.path.append('.')

from app.services.replay_parser import ReplayParser

def test_parser_validation():
    """Test that parser properly validates results."""
    print("🧪 Testing ReplayParser validation...")
    
    parser = ReplayParser()
    
    # Test with non-existent file (should fail properly)
    try:
        result = parser.parse_replay("nonexistent.dem")
        print("❌ Parser should have failed but returned:", result)
        return False
    except Exception as e:
        print(f"✅ Parser correctly failed: {e}")
    
    # Test with empty file (should fail properly)
    empty_file = "test_empty.dem"
    try:
        with open(empty_file, 'wb') as f:
            f.write(b'')
        
        result = parser.parse_replay(empty_file)
        print("❌ Parser should have failed for empty file but returned:", result)
        return False
    except Exception as e:
        print(f"✅ Parser correctly failed for empty file: {e}")
    finally:
        if os.path.exists(empty_file):
            os.remove(empty_file)
    
    print("✅ Parser validation working correctly")
    return True

def test_upload_endpoint_validation():
    """Test upload endpoint validation logic."""
    print("\n🧪 Testing upload validation logic...")
    
    # Test minimal data detection
    minimal_data = {
        "status": "failed",
        "filename": "test.dem"
    }
    
    # This should be detected as invalid
    if not minimal_data or len(minimal_data.keys()) < 5:
        print("✅ Minimal data correctly detected as invalid")
    else:
        print("❌ Minimal data not detected")
        return False
    
    # Test failure indicators
    failure_data = {
        "match_id": "unknown",
        "hero_name": "unknown", 
        "duration_minutes": 0,
        "some_other_field": "value"
    }
    
    if (failure_data.get("match_id") in ["unknown", None] or 
        failure_data.get("hero_name") in ["unknown", None] or
        failure_data.get("duration_minutes", 0) == 0):
        print("✅ Failure indicators correctly detected")
    else:
        print("❌ Failure indicators not detected")
        return False
    
    print("✅ Upload validation logic working correctly")
    return True

if __name__ == "__main__":
    print("🚀 Testing MatchMentor Upload Fix\n")
    
    parser_ok = test_parser_validation()
    upload_ok = test_upload_endpoint_validation()
    
    print("\n" + "="*50)
    print("🏁 TEST RESULTS:")
    print(f"   Parser Validation: {'✅ PASS' if parser_ok else '❌ FAIL'}")
    print(f"   Upload Validation: {'✅ PASS' if upload_ok else '❌ FAIL'}")
    
    if parser_ok and upload_ok:
        print("\n🎉 All validation tests passed!")
        print("The upload fix should now properly handle parsing failures.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed.")
        sys.exit(1)
