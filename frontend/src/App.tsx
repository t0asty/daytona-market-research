import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type FixturePreview = {
  file: string;
  source_role: string;
  headline: string;
};

type AgentStatus = "idle" | "running" | "done";

type AgentRow = {
  role: string;
  file: string;
  status: AgentStatus;
};

type FixturesResponse = {
  fixtures: FixturePreview[];
  directory: string;
};

function StatusDot({ status }: { status: AgentStatus }) {
  if (status === "done") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40">
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="relative flex h-6 w-6 items-center justify-center">
        <span className="absolute h-4 w-4 animate-ping rounded-full bg-indigo-400/60" />
        <span className="relative h-2.5 w-2.5 rounded-full bg-indigo-400 shadow-glow" />
      </span>
    );
  }
  return <span className="h-6 w-6 rounded-full border border-white/15 bg-white/5" />;
}

export default function App() {
  const [fixtures, setFixtures] = useState<FixturePreview[]>([]);
  const [fixturesDir, setFixturesDir] = useState("");
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [phase, setPhase] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [reportReady, setReportReady] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const streamActiveRef = useRef(false);

  useEffect(() => {
    fetch("/api/fixtures")
      .then((r) => {
        if (!r.ok) throw new Error(`Fixtures HTTP ${r.status}`);
        return r.json() as Promise<FixturesResponse>;
      })
      .then((data) => {
        setFixtures(data.fixtures);
        setFixturesDir(data.directory);
        setAgents(
          data.fixtures.map((f) => ({
            role: f.source_role,
            file: f.file,
            status: "idle" as AgentStatus,
          })),
        );
      })
      .catch((e: Error) => setLoadErr(e.message));
  }, []);

  const resetAgents = useCallback(() => {
    setAgents((prev) => prev.map((a) => ({ ...a, status: "idle" as AgentStatus })));
  }, []);

  const runAnalysis = useCallback(() => {
    if (busy) return;
    setBusy(true);
    setRunError(null);
    setMarkdown("");
    setReportReady(false);
    setPhase("Starting…");
    resetAgents();
    streamActiveRef.current = true;

    const es = new EventSource("/api/run/stream");

    const finishStream = () => {
      streamActiveRef.current = false;
      es.close();
    };

    es.addEventListener("message", (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data as string) as Record<string, unknown>;
        const t = msg.type as string;

        if (t === "run_started") {
          const total = (msg.total as number) ?? 0;
          setPhase(`Running ${total} analyst agents…`);
          setAgents((prev) =>
            prev.map((a) => ({ ...a, status: "idle" as AgentStatus })),
          );
        } else if (t === "agent_started") {
          const idx = msg.index as number;
          setAgents((prev) =>
            prev.map((a, i) => (i === idx ? { ...a, status: "running" } : a)),
          );
        } else if (t === "agent_finished") {
          const idx = msg.index as number;
          setAgents((prev) =>
            prev.map((a, i) => (i === idx ? { ...a, status: "done" } : a)),
          );
        } else if (t === "merging") {
          setPhase("Merging findings into executive report…");
        } else if (t === "report_ready") {
          finishStream();
          setPhase(null);
          fetch("/api/report")
            .then((r) => r.json())
            .then((body: { markdown?: string; ready?: boolean }) => {
              setMarkdown(body.markdown ?? "");
              setReportReady(!!body.ready);
            })
            .catch((e: Error) => setRunError(e.message))
            .finally(() => setBusy(false));
        } else if (t === "error") {
          finishStream();
          setRunError((msg.message as string) || "Run failed");
          setPhase(null);
          setBusy(false);
        }
      } catch {
        finishStream();
        setRunError("Invalid server event");
        setBusy(false);
      }
    });

    es.onerror = () => {
      const wasActive = streamActiveRef.current;
      finishStream();
      setBusy(false);
      setPhase(null);
      if (wasActive) {
        setRunError("Connection lost — is the API on port 8000?");
      }
    };
  }, [busy, resetAgents]);

  const downloadPdf = useCallback(async () => {
    if (!reportReady || pdfBusy) return;
    setPdfBusy(true);
    try {
      const r = await fetch("/api/report.pdf");
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail || r.statusText);
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "marketing-performance-report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : "PDF download failed");
    } finally {
      setPdfBusy(false);
    }
  }, [reportReady, pdfBusy]);

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,rgba(99,102,241,0.35),transparent)] bg-ink-950 text-slate-200">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_80%_60%,rgba(139,92,246,0.12),transparent_45%)]" />

      <header className="relative border-b border-white/10 bg-ink-900/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-indigo-300/90">
              Daytona hackathon
            </p>
            <h1 className="font-display mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Marketing intelligence
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400">
              Parallel analyst agents produce structured findings; this console merges them into an executive-ready
              narrative. One click simulates the full multi-agent run (fixtures today, sandboxes tomorrow).
            </p>
          </div>
          <div className="flex flex-wrap gap-3 pt-2 sm:pt-0">
            <button
              type="button"
              onClick={runAnalysis}
              disabled={busy || !!loadErr || agents.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-glow transition hover:from-indigo-500 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Running agents…
                </>
              ) : (
                <>
                  <span className="text-lg leading-none">⚡</span>
                  Run analyst agents
                </>
              )}
            </button>
            <button
              type="button"
              onClick={downloadPdf}
              disabled={!reportReady || pdfBusy}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-35"
            >
              {pdfBusy ? "Preparing PDF…" : "Download PDF"}
            </button>
          </div>
        </div>
      </header>

      <main className="relative mx-auto grid max-w-6xl gap-8 px-6 py-10 lg:grid-cols-[minmax(0,320px)_1fr]">
        <aside className="space-y-6">
          <section className="rounded-2xl border border-white/10 bg-ink-900/50 p-5 shadow-xl backdrop-blur-md">
            <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-slate-400">Agent fleet</h2>
            {loadErr ? (
              <p className="mt-4 text-sm text-rose-400">{loadErr}</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {agents.map((a) => (
                  <li
                    key={a.file}
                    className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-3"
                  >
                    <StatusDot status={a.status} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-xs text-indigo-300/90">{a.role}</p>
                      <p className="truncate text-xs text-slate-500">{a.file}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {fixturesDir ? (
              <p className="mt-4 border-t border-white/10 pt-4 font-mono text-[10px] leading-relaxed text-slate-600">
                {fixturesDir}
              </p>
            ) : null}
          </section>

          {fixtures.length > 0 ? (
            <section className="rounded-2xl border border-white/10 bg-ink-900/40 p-5">
              <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-slate-400">Upcoming signals</h2>
              <ul className="mt-3 space-y-2 text-xs text-slate-500">
                {fixtures.map((f) => (
                  <li key={f.file} className="leading-snug">
                    <span className="text-indigo-400/90">{f.source_role}</span>
                    {f.headline ? ` — ${f.headline}` : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {phase ? (
            <p className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-3 text-sm text-indigo-200">
              {phase}
            </p>
          ) : null}

          {runError ? (
            <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {runError}
            </p>
          ) : null}
        </aside>

        <section className="min-h-[60vh] rounded-2xl border border-white/10 bg-ink-900/40 p-6 shadow-2xl backdrop-blur-md sm:p-10">
          {!markdown && !reportReady ? (
            <div className="flex h-full min-h-[50vh] flex-col items-center justify-center text-center">
              <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] px-10 py-16">
                <p className="font-display text-lg font-medium text-slate-300">Report preview</p>
                <p className="mt-2 max-w-sm text-sm text-slate-500">
                  Run the analyst agents to merge channel findings into a single markdown report. Tables, evidence, and
                  recommendations render here for leadership review.
                </p>
              </div>
            </div>
          ) : (
            <article className="report-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </article>
          )}
        </section>
      </main>

      <footer className="relative border-t border-white/10 py-8 text-center text-xs text-slate-600">
        PDF export uses headless Chromium via Playwright — install browsers once:{" "}
        <code className="rounded bg-white/5 px-1.5 py-0.5 text-slate-400">playwright install chromium</code>
      </footer>
    </div>
  );
}
