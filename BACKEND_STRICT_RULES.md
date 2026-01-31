# 🛡️ MatchMentor Strict Development Rules

## RULE #16: MANDATORY PRE-COMMIT VERIFICATION (CRITICAL)

**Before performing ANY `git push` or concluding a task involving code changes, Antigravity MUST:**

1.  **Run Verification Script**: Execute `python prelaunch_check.py`. This script checks:
    - Syntax across the entire backend.
    - Basic import integrity.
2.  **Zero Error Tolerance**: If any error is detected, fix it and re-verify BEFORE notifying the user.
3.  **Verification Proof**: In the final task comment, explicitly state that `prelaunch_check.py` has been passed.

**Failure to follow this rule is considered a CRITICAL error.**
