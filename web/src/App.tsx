import { useState, useEffect, useCallback } from 'react';
import { api, type Run } from './api';
import LandingView, { type UserAccount } from './views/LandingView';
import OverviewView from './views/OverviewView';
import IndexView from './views/IndexView';
import BookingCurvesView from './views/BookingCurvesView';
import MethodView from './views/MethodView';

export type Tab = 'landing' | 'overview' | 'index' | 'curves' | 'method';

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
  landing: 'Landing',
  overview: 'Overview',
  index: 'Index',
  curves: 'Booking curves',
  method: 'Method',
};

const TABS: Tab[] = ['landing', 'overview', 'index', 'curves', 'method'];

export default function App() {
  const [tab, setTab] = useState<Tab>('landing');
  const [runs, setRuns] = useState<Run[]>([]);
  const [lastRunDate, setLastRunDate] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(getDateFromUrl());

  const [user, setUser] = useState<UserAccount | null>(() => {
    try {
      const saved = localStorage.getItem('apix_user');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.name?.includes('Vraj')) {
          parsed.name = 'Admin User';
          parsed.email = 'admin@apix.gov.in';
          parsed.role = 'System Administrator / Lead Analyst';
          localStorage.setItem('apix_user', JSON.stringify(parsed));
        }
        return parsed;
      }
      return null;
    } catch {
      return null;
    }
  });

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

  const handleLogin = (u: UserAccount) => {
    setUser(u);
    try {
      localStorage.setItem('apix_user', JSON.stringify(u));
    } catch {}
  };

  const handleLogout = () => {
    setUser(null);
    try {
      localStorage.removeItem('apix_user');
    } catch {}
    setTab('landing');
  };

  return (
    <>
      <header className="site-header" role="banner">
        <a
          href="/"
          className="site-header__brand"
          aria-label="APIx home"
          onClick={(e) => {
            e.preventDefault();
            setTab('landing');
          }}
        >
          APIx
        </a>
        <nav aria-label="Main navigation">
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

        <div className="site-header__auth">
          {user ? (
            <div className="site-header__user-pill">
              <span className="user-pill-icon">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
                </svg>
              </span>
              <span className="user-pill-name">{user.name}</span>
              <button
                type="button"
                className="user-pill-logout"
                onClick={handleLogout}
                title="Sign out of terminal"
              >
                Sign out
              </button>
            </div>
          ) : (
            tab !== 'landing' && (
              <button
                type="button"
                className="site-header__signin-btn"
                onClick={() => setTab('landing')}
              >
                Sign In
              </button>
            )
          )}
        </div>
      </header>

      <main>
        <div
          id="panel-landing"
          role="tabpanel"
          aria-labelledby="tab-landing"
          hidden={tab !== 'landing'}
        >
          {tab === 'landing' && (
            <LandingView
              onEnterApp={(target) => setTab(target ?? 'overview')}
              onLogin={handleLogin}
              currentUser={user}
            />
          )}
        </div>
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
