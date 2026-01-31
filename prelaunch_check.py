import os
import sys
import py_compile
from pathlib import Path

def check_syntax():
    print("🔍 Rule #16: Running Syntax Check...")
    backend_path = Path("backend")
    errors = 0
    # Exclude common directories that might have thousands of files or compiled binaries
    exclude_dirs = {"venv", ".git", "__pycache__", ".pytest_cache", "node_modules"}
    
    for py_file in backend_path.glob("**/*.py"):
        if any(ex in py_file.parts for ex in exclude_dirs):
            continue
            
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  ❌ SYNTAX ERROR in {py_file}:")
            print(f"     {e}")
            errors += 1
        except Exception as e:
            # Skip errors that are not syntax related (e.g. permission issues on some systems)
            continue
    return errors

def check_imports():
    print("🔍 Checking for obvious import errors...")
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    try:
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["SECRET_KEY"] = "test"
        
        # Test main entry points
        import app.main
        import app.api.matches
        print("  ✅ Imports look healthy")
        return 0
    except Exception as e:
        print(f"  ❌ IMPORT ERROR: {e}")
        # import traceback
        # traceback.print_exc()
        return 1

def run_checks():
    print("="*40)
    print("🛡️  MATCHMENTOR PRE-LAUNCH VERIFICATION")
    print("="*40)
    
    syntax_errors = check_syntax()
    import_errors = check_imports()
    
    print("="*40)
    if syntax_errors == 0 and import_errors == 0:
        print("🚀 VERIFICATION PASSED. Safe to commit/push.")
        sys.exit(0)
    else:
        print(f"🛑 VERIFICATION FAILED. ({syntax_errors} syntax, {import_errors} import)")
        sys.exit(1)

if __name__ == "__main__":
    run_checks()
