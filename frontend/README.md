# Compliance-as-Code Frontend Dashboard

A premium, cinematic developer dashboard designed to visualize compliance rules and real-time device telemetry violations. Built with a dark-mode-first aesthetic inspired by linear.app and Vercel.

## Tech Stack
- **Core:** React 19 + TypeScript + Vite
- **Styling:** Tailwind CSS (v4) with premium custom dark themes
- **Animations:** Framer Motion for highly responsive, micro-animated interactions
- **Visuals:** Lucide React icons & Recharts for interactive dashboards

## Key Features
1. **Dynamic Pipeline Visualization:** Real-time visual pipeline showing active telemetry ingestion, parsing, rule validation, and violation alerting.
2. **Interactive Rule Explorer:** Browse rules parsed from policies, complete with metadata, category grouping, and direct-access key-value schemas.
3. **Advanced PDF Ingestor (Drag & Drop):** High-fidelity dropzone to upload compliance policy PDFs, using the backend's Gemini LLM extraction pipeline with real-time UI streaming feedback.
4. **Telemetry Stream Analytics:** Visualizes incoming device check-ins and compliance metrics using smooth, real-time charts.

## Setup & Running

Make sure you have Node.js (v18+) installed.

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The application will start on [http://localhost:5173](http://localhost:5173).

## API Integration & Proxying
Vite is pre-configured via `vite.config.ts` to proxy requests targeting `/api`, `/health`, and `/metrics` directly to the FastAPI server:
- API Proxy Target: `http://127.0.0.1:8000`
- Connection timeout is configured to 180 seconds to fully support streaming Gemini rule extraction pipelines without dropping.
