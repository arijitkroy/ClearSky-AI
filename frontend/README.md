# ClearSky AI Frontend Dashboard

This directory contains the Next.js frontend client for the ClearSky AI Smart City pollution intelligence platform. The user interface provides a live map, data visualizations, alert tickers, and citizen upload controls.

## Technologies Used

* **Next.js (Pages Router)**: Core React application server framework.
* **Tailwind CSS**: Utility-first CSS framework for layout styling.
* **Leaflet & React-Leaflet**: Open-source GIS library for rendering map vectors and custom markers.
* **Recharts**: D3-based charting library for real-time sensor analytics.
* **Framer Motion**: React animation library for interface slides and transitions.
* **Lucide React**: Modular icon library.

## Getting Started

### Prerequisites

Ensure you have Node.js 20+ and npm installed locally.

### 1. Install Packages
```bash
npm install
```

### 2. Configure Environment variables
Ensure you have the backend FastAPI services running at `http://127.0.0.1:8000`. If running on a different port or host, specify it in your shell environment:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser to inspect the application.

## Production Builds

To compile and optimize the client application for production hosting:
```bash
npm run build
npm run start
```
This performs a static build compilation and launches the Next.js production server.
