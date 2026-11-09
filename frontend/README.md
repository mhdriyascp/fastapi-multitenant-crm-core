# 🖥️ Enterprise CRM — Frontend Application

[![Next.js](https://img.shields.io/badge/Next.js-16.4.5-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.3.0-61dafb.svg?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178c6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-4.x-38bdf8.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20.x-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org/)

The frontend application is built with the **Next.js 16 App Router**, **React 19**, and **Tailwind CSS 4**. In its current phase, it delivers real-time system health diagnostics communicating directly with the FastAPI backend service.

---

## 📑 Table of Contents

- [Overview & Architecture](#-overview--architecture)
- [Directory Layout](#-directory-layout)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Available Scripts](#-available-scripts)
- [Current Implementation Status](#-current-implementation-status)
- [Related Documentation](#-related-documentation)

---

## 🏛️ Overview & Architecture

```mermaid
flowchart TD
    Browser["🌐 Web Browser\n(http://localhost:3000)"]

    subgraph NextJS_App["Next.js 16 Frontend (frontend/)"]
        direction TB
        Page["📄 app/page.tsx\nClient Component"]
        Layout["📄 app/layout.tsx\nRoot Layout & Geist Fonts"]
        CSS["🎨 app/globals.css\nTailwind v4 Utility Styles"]
        
        Page -->|Mounts & Renders| UI["Health Dashboard UI\n• Overall System Status\n• PostgreSQL Connectivity\n• Redis Connection"]
    end

    subgraph Backend_API["FastAPI Backend (:8000)"]
        HealthEndpoint["GET /health\n(HealthResponse)"]
        PG["🐘 PostgreSQL Probe"]
        RD["⚡ Redis Probe"]
        HealthEndpoint --> PG
        HealthEndpoint --> RD
    end

    Browser --> Page
    Page -->|fetch() via NEXT_PUBLIC_API_URL| HealthEndpoint
```

---

## 📂 Directory Layout

```text
frontend/
├── package.json              # Project scripts and dependencies (Next.js 16, React 19)
├── package-lock.json         # Lockfile — npm is the mandatory package manager
├── tsconfig.json             # TypeScript compiler settings & path aliases (@/*)
├── next.config.ts            # Next.js framework configuration
├── eslint.config.mjs         # ESLint configuration with Next.js core vitals
├── public/                   # Static SVG icons and image assets
└── src/
    └── app/
        ├── favicon.ico       # Browser tab favicon
        ├── globals.css       # Tailwind CSS v4 directives & theme definitions
        ├── layout.tsx        # Root HTML layout with Geist font optimization
        └── page.tsx          # Real-time backend system health indicator page
```

---

## ⚡ Quick Start

### 1. Prerequisites

- Node.js `>= 20.x`
- npm (do not use Yarn, pnpm, or Bun; `package-lock.json` is authoritative)
- Backend running on `http://localhost:8000`

### 2. Install Dependencies

```sh
cd frontend
npm ci
```

### 3. Configure Local Environment

Create `.env.local` in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Run Development Server

```sh
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the live health monitor.

---

## ⚙️ Configuration

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend for client-side API requests | `http://localhost:8000` |

---

## 🛠️ Available Scripts

All scripts are configured in `package.json`:

| Command | Purpose |
|---|---|
| `npm run dev` | Starts local Next.js dev server with Fast Refresh on port 3000 |
| `npm run build` | Compiles optimized production build into `.next/` |
| `npm run start` | Serves the pre-compiled production build |
| `npm run lint` | Runs ESLint according to `eslint.config.mjs` |

---

## 📌 Current Implementation Status

> [!NOTE]
> The current frontend is an operational status probe for developer onboarding and infrastructure verification. The complete multi-tenant CRM workspace UI (authentication and user administration) is scheduled in upcoming implementation phases.

| Feature Area | Status | Notes |
|---|---|---|
| **System Diagnostics** | ✅ Live | Fetches `/health` on mount, displaying PostgreSQL and Redis statuses |
| **Typography & Theme** | ✅ Live | Vercel Geist fonts with responsive dark-mode styling via Tailwind CSS 4 |
| **Auth UI & Login** | 🔲 Planned | Authentication pages (login, registration, MFA challenge modal) |
| **Workspace & Members UI** | 🔲 Planned | Team member invitation, role assignment table, switch workspace |

---

## 📖 Related Documentation

- [Root Repository README](../README.md)
- [Backend Service README](../backend/README.md)
- [Local Development Guide](../docs/02-setup/local-development.md)
- [Developer Command Cheat Sheet](../docs/02-setup/developer-commands.md)
- [Engineering Standards & AI Agent Guidelines](../AGENTS.md)
