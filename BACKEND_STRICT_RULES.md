# 🛡️ MatchMentor Strict Development Rules

## RULE #16: MANDATORY SYNTAX CHECK (CRITICAL)

**Before performing ANY `git push` or concluding a task involving code changes, Antigravity MUST:**

1.  **Run Syntax Compiler**: Execute `python -m py_compile [path_to_modified_files]` for all modified Python files.
2.  **Verify Frontend Types**: Run `npm run tsc` or equivalent if frontend files were touched.
3.  **Zero Error Tolerance**: If any syntax error or lint error is detected, fix it and re-verify BEFORE notifying the user.
4.  **Verification Proof**: In the final task comment, explicitly state that syntax has been verified.

**Failure to follow this rule is considered a CRITICAL error.**
