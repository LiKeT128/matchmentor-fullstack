---
trigger: always_on
---

# Backend Code Quality Rules

## Python Style
- All code PEP 8 compliant
- Use Black formatter
- All functions need docstrings
- Type hints on all parameters

## FastAPI Standards
- All endpoints need docstrings
- All endpoints return proper HTTP status codes
- All database queries parameterized (SQL injection safe)
- All errors handled with proper exceptions

## Database
- Use SQLAlchemy ORM (no raw SQL)
- Eager loading for relationships
- Proper foreign keys
- Migrations tracked

## Testing
- Every endpoint needs test
- Test with pytest
- Run tests before committing

## API Documentation
- Every endpoint documented
- Request/Response examples provided
```

**Workflows для Backend Developer:**

```markdown
# Backend Workflows

## Workflow: test-backend
Execute:
1. Run pytest
2. Check coverage (min 70%)
3. Run API smoke tests
4. Verify database connectivity
5. Fail if any tests don't pass

## Workflow: deploy-local
Execute:
1. Start PostgreSQL
2. Run migrations
3. Start FastAPI on port 8000
4. Verify health endpoint
5. Test Clarity parser with sample file
```

---