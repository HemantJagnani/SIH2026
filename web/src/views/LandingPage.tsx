/**
 * LandingPage.tsx
 *
 * Split layout:
 *   LEFT  – brand, index teaser chart + three key stats (static/demo until auth)
 *   RIGHT – sign-up / log-in tabs with form
 *
 * Design follows the "chart paper" direction from APIX_FRONTEND_REVAMP.md:
 *   --vellum surface, --ink type, no cards, direct labels, B612 mono.
 */

import { useState, useId } from 'react';

/* ── tiny sparkline drawn as SVG polyline ─────────────────────────────── */
function Sparkline({
  values,
  width = 260,
  height = 64,
  color,
}: {
  values: number[];
  width?: number;
  height?: number;
  color: string;
}) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 8) - 4;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg
      width={width}
      height={height}
      aria-hidden="true"
      style={{ display: 'block', overflow: 'visible' }}
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ── illustrative index values (will be replaced by real API data) ─────── */
const DEMO_VALUES = [
  100, 100.4, 101.1, 100.7, 99.8, 100.2, 101.5, 102.1, 101.8, 102.6,
  103.0, 102.4, 101.9, 102.8, 103.4, 104.1, 103.7, 104.5, 105.0, 104.8,
  105.3, 106.0, 105.7, 106.4, 107.0, 106.6, 107.3, 108.1, 107.8, 108.4,
];

/* ── form ──────────────────────────────────────────────────────────────── */
type AuthMode = 'login' | 'signup';

interface FormProps {
  mode: AuthMode;
  onSuccess: () => void;
}

function AuthForm({ mode, onSuccess }: FormProps) {
  const emailId  = useId();
  const passId   = useId();
  const nameId   = useId();
  const [email, setEmail]   = useState('');
  const [pass, setPass]     = useState('');
  const [name, setName]     = useState('');
  const [error, setError]   = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!email || !pass) { setError('Email and password are required.'); return; }
    if (mode === 'signup' && !name) { setError('Name is required.'); return; }
    setLoading(true);
    // Stub: replace with real auth API call
    await new Promise(r => setTimeout(r, 600));
    setLoading(false);
    onSuccess();
  }

  return (
    <form
      className="auth-form"
      onSubmit={handleSubmit}
      noValidate
      aria-label={mode === 'login' ? 'Log in' : 'Create account'}
    >
      {mode === 'signup' && (
        <div className="auth-field">
          <label htmlFor={nameId} className="auth-label">Full name</label>
          <input
            id={nameId}
            type="text"
            className="auth-input"
            autoComplete="name"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Priya Sharma"
            aria-required="true"
          />
        </div>
      )}

      <div className="auth-field">
        <label htmlFor={emailId} className="auth-label">Email</label>
        <input
          id={emailId}
          type="email"
          className="auth-input"
          autoComplete={mode === 'login' ? 'username' : 'email'}
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="you@example.com"
          aria-required="true"
        />
      </div>

      <div className="auth-field">
        <label htmlFor={passId} className="auth-label">
          {mode === 'signup' ? 'Choose a password' : 'Password'}
        </label>
        <input
          id={passId}
          type="password"
          className="auth-input"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          value={pass}
          onChange={e => setPass(e.target.value)}
          placeholder="••••••••"
          aria-required="true"
        />
      </div>

      {error && (
        <p className="auth-error" role="alert">{error}</p>
      )}

      <button
        type="submit"
        id={`auth-submit-${mode}`}
        className="auth-submit"
        disabled={loading}
        aria-busy={loading}
      >
        {loading
          ? (mode === 'login' ? 'Signing in…' : 'Creating account…')
          : (mode === 'login' ? 'Sign in' : 'Create account')
        }
      </button>

      {mode === 'login' && (
        <p className="auth-forgot">
          <a href="#reset" className="auth-link">Forgot password?</a>
        </p>
      )}
    </form>
  );
}

/* ── main component ────────────────────────────────────────────────────── */
interface Props {
  onAuthenticated: () => void;
}

export default function LandingPage({ onAuthenticated }: Props) {
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const tabLoginId  = useId();
  const tabSignupId = useId();

  return (
    <div className="landing-root">

      {/* ── LEFT: brand + teaser ─────────────────────────────────────── */}
      <div className="landing-left" aria-label="Product overview">
        <div className="landing-brand">
          <span className="landing-wordmark">APIx</span>
          <span className="landing-tagline">
            India&rsquo;s airfare price index&ensp;·&ensp;research prototype
          </span>
        </div>

        {/* teaser chart */}
        <div className="landing-chart-block" aria-hidden="true">
          <div className="landing-chart-label">
            Overall index &nbsp;·&nbsp; last 30 observations
          </div>
          <Sparkline values={DEMO_VALUES} color="var(--ink)" width={320} height={72} />
          <div className="landing-chart-axis">
            <span>100 (base)</span>
            <span>+{(DEMO_VALUES.at(-1)! - 100).toFixed(1)} pts</span>
          </div>
          <div className="landing-route-sparks">
            <div className="landing-route-row">
              <span style={{ color: 'var(--route-blue)' }}>DEL–BOM</span>
              <Sparkline
                values={DEMO_VALUES.map(v => v * 0.5 + 50 + Math.sin(v) * 0.4)}
                color="var(--route-blue)" width={120} height={32}
              />
            </div>
            <div className="landing-route-row">
              <span style={{ color: 'var(--route-mag)' }}>DEL–BLR</span>
              <Sparkline
                values={DEMO_VALUES.map(v => v * 0.3 + 70 + Math.cos(v) * 0.3)}
                color="var(--route-mag)" width={120} height={32}
              />
            </div>
            <div className="landing-route-row">
              <span style={{ color: 'var(--route-teal)' }}>BOM–BLR</span>
              <Sparkline
                values={DEMO_VALUES.map(v => v * 0.2 + 80 + Math.sin(v * 0.7) * 0.3)}
                color="var(--route-teal)" width={120} height={32}
              />
            </div>
          </div>
        </div>

        {/* three key facts */}
        <ul className="landing-facts" aria-label="Key facts">
          <li>
            <span className="landing-fact-num">3</span>
            <span className="landing-fact-label">routes tracked daily</span>
          </li>
          <li>
            <span className="landing-fact-num">4</span>
            <span className="landing-fact-label">lead-time windows</span>
          </li>
          <li>
            <span className="landing-fact-num">100</span>
            <span className="landing-fact-label">base value (Laspeyres-chain)</span>
          </li>
        </ul>

        <p className="landing-disclaimer">
          Fares collected via <code>flight.easemytrip.com</code>.
          This is a non-commercial research prototype.
          Weights and coverage shown are indicative.
        </p>
      </div>

      {/* ── RIGHT: auth panel ─────────────────────────────────────────── */}
      <div className="landing-right" role="main" aria-label="Sign in or create account">
        <div className="auth-panel">

          {/* tabs */}
          <div
            className="auth-tabs"
            role="tablist"
            aria-label="Authentication mode"
          >
            <button
              id={tabLoginId}
              role="tab"
              aria-selected={authMode === 'login'}
              aria-controls="auth-panel-login"
              className={`auth-tab${authMode === 'login' ? ' active' : ''}`}
              onClick={() => setAuthMode('login')}
            >
              Sign in
            </button>
            <button
              id={tabSignupId}
              role="tab"
              aria-selected={authMode === 'signup'}
              aria-controls="auth-panel-signup"
              className={`auth-tab${authMode === 'signup' ? ' active' : ''}`}
              onClick={() => setAuthMode('signup')}
            >
              Create account
            </button>
          </div>

          {/* form panel */}
          <div
            id={authMode === 'login' ? 'auth-panel-login' : 'auth-panel-signup'}
            role="tabpanel"
            aria-labelledby={authMode === 'login' ? tabLoginId : tabSignupId}
          >
            <AuthForm mode={authMode} onSuccess={onAuthenticated} />
          </div>

          <p className="auth-switch">
            {authMode === 'login' ? (
              <>No account?{' '}
                <button
                  className="auth-link"
                  id="switch-to-signup"
                  onClick={() => setAuthMode('signup')}
                >
                  Create one
                </button>
              </>
            ) : (
              <>Already have one?{' '}
                <button
                  className="auth-link"
                  id="switch-to-login"
                  onClick={() => setAuthMode('login')}
                >
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
