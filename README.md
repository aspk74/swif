# Compliance-as-Code Pipeline

An automated compliance engine that transforms security policy PDFs into a structured MongoDB rules registry, then validates live device telemetry against those rules in real-time.

## Architecture

The system is split into two decoupled phases:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Rule Ingestion (pipeline/)                                    │
│                                                                         │
│  PDF ──► Chunker ──► Gemini LLM ──► Pydantic Validation ──► MongoDB    │
│                        (extract)       (repair loop)        (rules)     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 2: Telemetry Validation (validation/)                            │
│                                                                         │
│  Producer ──► FastAPI ──► asyncio.Queue ──► StreamProcessor             │
│  (devices)    /telemetry   (backpressure)   (compare against rules)     │
│                                                     │                   │
│                                                     ▼                   │
│                                              MongoDB (violations)       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
swif/
├── config.py                  # Centralized configuration (env vars)
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment variables
│
├── pipeline/                  # Phase 1: PDF → Rules
│   ├── main.py                # CLI entrypoint for PDF ingestion
│   ├── ingestion.py           # PDF text extraction and chunking
│   ├── extractor.py           # Gemini LLM extraction with repair loop
│   └── logger.py              # JSON-formatted structured logging
│
├── db/                        # Shared database layer
│   ├── schema.py              # Pydantic models (SecurityRule, LogicOperator, etc.)
│   └── storage.py             # RuleStore — MongoDB CRUD + violation persistence
│
├── validation/                # Phase 2: Telemetry → Violations
│   ├── ingestor.py            # FastAPI service (POST /telemetry)
│   ├── processor.py           # Async stream processor (queue consumer)
│   ├── comparator.py          # Rule evaluation engine (all LogicOperators)
│   ├── producer.py            # Mock device telemetry simulator
│   └── models.py              # TelemetryPayload, ComplianceViolation models
│
├── tests/                     # Test suite
│   ├── test_comparator.py     # 33 tests for all LogicOperator variants
│   ├── test_extractor.py      # LLM extraction + repair loop tests
│   ├── test_ingestion.py      # PDF chunking tests
│   └── test_storage.py        # MongoDB storage tests
│
└── data/                      # Place your PDF policy documents here
```

## Setup

### 1. Python Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Your Google Gemini API key |
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | Gemini model for rule extraction |
| `MONGO_URI` | `mongodb://localhost:27017/` | MongoDB connection string |
| `DB_NAME` | `compliance_db` | Database name |
| `COLLECTION_NAME` | `rules` | Rules collection name |
| `VIOLATIONS_COLLECTION_NAME` | `violations` | Violations collection name |
| `MAX_WORKERS` | `10` | Concurrent PDF chunk processing threads |
| `MAX_CHUNK_TOKENS` | `12000` | Max tokens per PDF chunk |
| `TELEMETRY_QUEUE_MAX_SIZE` | `1000` | Backpressure limit for telemetry queue |
| `INGESTOR_HOST` | `127.0.0.1` | Host for the FastAPI ingestor |
| `INGESTOR_PORT` | `8000` | Port for the FastAPI ingestor |

### 3. MongoDB

You need a running MongoDB instance. Choose one:

**Option A: Docker (Recommended)**
```bash
docker run -d -p 27017:27017 --name compliance-mongo mongo:latest
```

**Option B: Homebrew (Mac)**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

## Running

### Phase 1: Ingest a Security Policy PDF

This extracts security rules from a PDF and stores them in MongoDB.

```bash
# Place your PDF in the data/ folder, then:
python -m pipeline.main --pdf data/policy.pdf
```

To preview extracted rules without writing to MongoDB:
```bash
python -m pipeline.main --pdf data/policy.pdf --dry-run
```

### Phase 2: Validate Device Telemetry

This runs the real-time validation pipeline. You need **two terminals** (plus MongoDB running).

**Terminal 1 — Start the Ingestor (FastAPI)**
```bash
source venv/bin/activate
python -m uvicorn validation.ingestor:app --host 127.0.0.1 --port 8000 --workers 1
```

> **Important:** Always use `--workers 1`. Multiple workers break the in-process asyncio.Queue.

**Terminal 2 — Start the Producer (Mock Devices)**
```bash
source venv/bin/activate
python -m validation.producer
```

The producer will simulate 5 devices sending telemetry every 1–2 seconds. Roughly half will be non-compliant, generating violations.

### Verifying Results

**Check the ingestor health:**
```bash
curl http://127.0.0.1:8000/health
```

**Reload rules cache** (after ingesting a new PDF):
```bash
curl -X POST http://127.0.0.1:8000/rules/reload
```

**Inspect violations in MongoDB:**
```bash
mongosh compliance_db --eval "db.violations.find().sort({violated_at: -1}).limit(5).pretty()"
```

## Testing

Run the full test suite (43 tests):

```bash
python -m pytest tests/ -v
```

Run only the comparator tests:

```bash
python -m pytest tests/test_comparator.py -v
```

## Key Design Decisions

- **`asyncio.to_thread()`** wraps all synchronous `pymongo` calls to prevent event-loop blocking in the async FastAPI/processor pipeline.
- **Bounded queue** (`maxsize=1000`) provides natural backpressure — if the processor falls behind, the HTTP endpoint slows down.
- **In-memory rules cache** avoids hitting MongoDB on every telemetry event. Rules are loaded at startup and refreshable via `POST /rules/reload`.
- **Sentinel-based shutdown** — pushing `None` into the queue signals the processor to drain remaining events and exit cleanly.
- **Content-hash deduplication** — rules are keyed by a deterministic SHA-256 hash of their content, ensuring idempotent PDF re-ingestion.

