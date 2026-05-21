# Trolley to LLM Frontend

React, TypeScript, Tailwind CSS, and Vite frontend for the Trolley to LLM comparison tool.

## Package Manager

Use pnpm only in this directory. Do not run npm or yarn for frontend dependencies or scripts.

The expected package manager is declared in `package.json`:

```json
"packageManager": "pnpm@11.1.2"
```

## Setup

Install dependencies:

```bash
pnpm install
```

Start the development server:

```bash
pnpm dev
```

The app runs at `http://localhost:5173` and expects the backend API at `http://localhost:8000`.

## Available Commands

| Command | Purpose |
|---|---|
| `pnpm dev` | Start the Vite development server |
| `pnpm lint` | Run ESLint |
| `pnpm build` | Type-check and build the frontend |
| `pnpm preview` | Preview a production build locally |

## Source Map

| Path | Purpose |
|---|---|
| `src/App.tsx` | Main application flow and page composition |
| `src/api.ts` | Backend API client functions |
| `src/types.ts` | Shared frontend TypeScript types |
| `src/components/` | Reusable UI components for questions, slots, results, import, and export |
