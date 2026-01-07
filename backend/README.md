# MatchMentor Backend

Dota 2 replay analyzer with coaching marketplace - FastAPI backend.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/matches/upload` | Upload replay |
| GET | `/api/matches/{id}` | Get match analysis |
| GET | `/api/coaches` | List coaches |
| POST | `/api/coaches/register` | Register as coach |

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy
- **Auth**: JWT tokens
- **Parser**: Clarity (Java)
- **Payments**: Stripe
- **Email**: SendGrid

## Environment Variables

See `.env.example` for required configuration.

## Tier Limits

| Tier | Monthly Uploads |
|------|----------------|
| FREE | 5 |
| PRO | 50 |
| PREMIUM | Unlimited |
