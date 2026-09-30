import { useState, useEffect, useCallback } from 'react';
import { api, type Run } from './api';
import OverviewView from './views/OverviewView';
import IndexView from './views/IndexView';
import BookingCurvesView from './views/BookingCurvesView';
import BacktestView from './views/BacktestView';
import MethodView from './views/MethodView';

export type Tab = 'overview' | 'index' | 'curves' | 'backtest' | 'method';

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
  overview: 'Overview',
  index: 'Index',
  curves: 'Booking curves',
  backtest: 'Backtest / Validation',
  method: 'Method',
};

const TABS: Tab[] = ['overview', 'index', 'curves', 'backtest', 'method'];

export default function App() {
  const [tab, setTab] = useState<Tab>('overview');
  const [runs, setRuns] = useState<Run[]>([]);
  const [lastRunDate, setLastRunDate] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(getDateFromUrl());

  useEffect(() => {
    let mounted = true;
    const fetchRuns = () => {
      api.runs().then(r => {
        if (!mounted) return;
        setRuns(r);
        if (r.length > 0) setLastRunDate(r[0].run_date);
      }).catch(() => {});
    };
    fetchRuns();

    const interval = setInterval(fetchRuns, 30000);
    const handleFocus = () => fetchRuns();
    window.addEventListener('focus', handleFocus);

    return () => {
      mounted = false;
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  const handleSetDate = useCallback((d: string | null) => {
    setSelectedDate(d);
    setDateInUrl(d);
  }, []);

  return (
    <>
      <header className="site-header" role="banner">
        <a
          href="/"
          className="site-header__brand"
          aria-label="AERIX home"
          onClick={(e) => {
            e.preventDefault();
            setTab('overview');
          }}
        >
          AERIX
        </a>
        <nav aria-label="Main navigation" className="site-header__nav-wrap">
          <ul className="site-header__nav" role="tablist">
            {TABS.map(t => (
              <li key={t} role="none">
                <button
                  id={`tab-${t}`}
                  type="button"
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
          id="panel-overview"
          role="tabpanel"
          aria-labelledby="tab-overview"
          hidden={tab !== 'overview'}
        >
          {tab === 'overview' && (
            <OverviewView onNavigate={(nextTab) => setTab(nextTab)} />
          )}
        </div>
        <div
          id="panel-index"
          role="tabpanel"
          aria-labelledby="tab-index"
          hidden={tab !== 'index'}
        >
          {tab === 'index' && (
            <IndexView
              key={lastRunDate || 'initial'}
              selectedDate={selectedDate}
              onSelectDate={handleSetDate}
              onNavigate={(nextTab) => setTab(nextTab)}
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
              key={lastRunDate || 'initial'}
              selectedDate={selectedDate}
              onSelectDate={handleSetDate}
            />
          )}
        </div>
        <div
          id="panel-backtest"
          role="tabpanel"
          aria-labelledby="tab-backtest"
          hidden={tab !== 'backtest'}
        >
          {tab === 'backtest' && <BacktestView />}
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
