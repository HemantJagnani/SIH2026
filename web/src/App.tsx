import { useState, useEffect, useCallback } from 'react';
import { api, type Run } from './api';
import IndexView from './views/IndexView';
import BookingCurvesView from './views/BookingCurvesView';
import MethodView from './views/MethodView';
import LandingPage from './views/LandingPage';

type Tab = 'index' | 'curves' | 'method';

/** Read/write the selected date from the URL search params. */
function getDateFromUrl(): string | null {
  const p = new URLSearchParams(window.location.search);
  return p.get('d');
}

function setDateInUrl(d: string | null) {
  const p = new URLSearchParams(window.location.search);
  if (d) p.set('d', d);
  else p.delete('d');
  const next = p.toString() ? `?${p}` : window.location.pathname;
  window.history.replaceState(null, '', next);
}

/** Format "Data through 19 Sep 2026" */
function fmtThrough(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00Z');
  return `Data through ${d.toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  })}`;
}

const TAB_LABELS: Record<Tab, string> = {
  index: 'Index',
  curves: 'Booking curves',
  method: 'Method',
};

export default function App() {
  // Auth gate — persists across page reloads within the session
  const [authed, setAuthed] = useState<boolean>(() => {
    try { return sessionStorage.getItem('apix_authed') === '1'; } catch { return false; }
  });

  const handleAuthenticated = useCallback(() => {
    try { sessionStorage.setItem('apix_authed', '1'); } catch {}
    setAuthed(true);
  }, []);

  // Show landing until authenticated
  if (!authed) {
    return <LandingPage onAuthenticated={handleAuthenticated} />;
  }

  return <Dashboard />;
}

/* ── Dashboard (shown after auth) ───────────────────────────────────────── */
function Dashboard() {
  const [tab, setTab] = useState<Tab>('index');
  const [runs, setRuns] = useState<Run[]>([]);
  const [lastRunDate, setLastRunDate] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(getDateFromUrl());

  useEffect(() => {
    api.runs().then(r => {
      setRuns(r);
      if (r.length > 0) setLastRunDate(r[0].run_date);
    }).catch(() => {});
  }, []);

  const handleSetDate = useCallback((d: string | null) => {
    setSelectedDate(d);
    setDateInUrl(d);
  }, []);

  return (
    <>
      <header className="site-header" role="banner">
        <a href="/" className="site-header__brand" aria-label="APIx home">
          APIx
        </a>
        <nav aria-label="Main navigation">
          <ul className="site-header__nav" role="tablist">
            {(['index', 'curves', 'method'] as Tab[]).map(t => (
              <li key={t} role="none">
                <button
                  id={`tab-${t}`}
                  role="tab"
                  aria-selected={tab === t}
                  aria-controls={`panel-${t}`}
                  className={`nav-btn${tab === t ? ' active' : ''}`}
                  onClick={() => setTab(t)}
                >
                  {TAB_LABELS[t]}
                </button>
              </li>
            ))}
          </ul>
        </nav>
        {lastRunDate && (
          <span className="site-header__status font-num">
            {fmtThrough(lastRunDate)}
          </span>
        )}
      </header>

      <main>
        <div
          id="panel-index"
          role="tabpanel"
          aria-labelledby="tab-index"
          hidden={tab !== 'index'}
        >
          {tab === 'index' && (
            <IndexView
              selectedDate={selectedDate}
              onSelectDate={handleSetDate}
            />
          )}
        </div>
        <div
          id="panel-curves"
          role="tabpanel"
          aria-labelledby="tab-curves"
          hidden={tab !== 'curves'}
        >
          {tab === 'curves' && (
            <BookingCurvesView
              selectedDate={selectedDate}
              onSelectDate={handleSetDate}
            />
          )}
        </div>
        <div
          id="panel-method"
          role="tabpanel"
          aria-labelledby="tab-method"
          hidden={tab !== 'method'}
        >
          {tab === 'method' && <MethodView runs={runs} />}
        </div>
      </main>
    </>
  );
}
