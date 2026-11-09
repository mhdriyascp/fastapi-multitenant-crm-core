interface HealthResponse {
  status: string;
  environment: string;
  services: {
    postgres: { status: string; details?: string };
    redis: { status: string; details?: string };
  };
}

async function getHealth(): Promise<HealthResponse | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    console.error("Failed to fetch health check from FastAPI:", error);
    return null;
  }
}

export default async function HomePage() {
  const health = await getHealth();

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
        <h1 className="text-2xl font-bold tracking-tight mb-2 text-white">
          Enterprise CRM
        </h1>
        <p className="text-sm text-slate-400 mb-6">
          Full-Stack Architecture Verification
        </p>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-sm font-medium">FastAPI Status</span>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-semibold uppercase ${
                health?.status === "healthy"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                  : "bg-rose-950 text-rose-400 border border-rose-800"
              }`}
            >
              {health?.status ?? "Offline"}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-sm font-medium">PostgreSQL (pgvector)</span>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-semibold uppercase ${
                health?.services?.postgres?.status === "healthy"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                  : "bg-rose-950 text-rose-400 border border-rose-800"
              }`}
            >
              {health?.services?.postgres?.status ?? "Offline"}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-sm font-medium">Redis Cache</span>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-semibold uppercase ${
                health?.services?.redis?.status === "healthy"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                  : "bg-rose-950 text-rose-400 border border-rose-800"
              }`}
            >
              {health?.services?.redis?.status ?? "Offline"}
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-500 mt-6 text-center">
          Environment: <span className="text-slate-400 font-mono">{health?.environment ?? "Unknown"}</span>
        </p>
      </div>
    </main>
  );
}
