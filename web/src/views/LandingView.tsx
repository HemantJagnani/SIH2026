import { useState, useId } from 'react';

export interface UserAccount {
  name: string;
  email: string;
  organization: string;
  role: string;
}

interface LandingViewProps {
  onEnterApp: (targetTab?: 'overview' | 'index') => void;
  onLogin: (user: UserAccount) => void;
  currentUser: UserAccount | null;
}

export default function LandingView({ onEnterApp, onLogin, currentUser }: LandingViewProps) {
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [showPassword, setShowPassword] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Sign In state
  const [signInEmail, setSignInEmail] = useState('analyst@aviation.gov.in');
  const [signInPassword, setSignInPassword] = useState('••••••••••••');
  const [rememberMe, setRememberMe] = useState(true);

  // Sign Up state
  const [signUpName, setSignUpName] = useState('');
  const [signUpEmail, setSignUpEmail] = useState('');
  const [signUpOrg, setSignUpOrg] = useState('Ministry of Statistics (MoSPI)');
  const [signUpPassword, setSignUpPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(true);

  const emailId = useId();
  const passId = useId();
  const upNameId = useId();
  const upEmailId = useId();
  const upOrgId = useId();
  const upPassId = useId();

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    if (!signInEmail) {
      setStatusMessage('Please enter your official email or terminal ID.');
      return;
    }
    const user: UserAccount = {
      name: signInEmail.split('@')[0].replace('.', ' ').toUpperCase(),
      email: signInEmail,
      organization: 'MoSPI Civil Aviation Analytics',
      role: 'Senior Statistical Officer',
    };
    setStatusMessage('Authentication verified. Connecting to APIx Terminal...');
    setTimeout(() => {
      onLogin(user);
      onEnterApp('overview');
    }, 450);
  };

  const handleQuickDemo = () => {
    const demoUser: UserAccount = {
      name: 'Vraj Verma',
      email: 'vraj@aviation.gov.in',
      organization: 'MoSPI National Accounts',
      role: 'Principal Aviation Analyst',
    };
    setStatusMessage('Access granted as Principal Aviation Analyst...');
    setTimeout(() => {
      onLogin(demoUser);
      onEnterApp('overview');
    }, 350);
  };

  const handleSignUp = (e: React.FormEvent) => {
    e.preventDefault();
    if (!signUpName || !signUpEmail) {
      setStatusMessage('Please enter your full name and institutional email.');
      return;
    }
    const user: UserAccount = {
      name: signUpName,
      email: signUpEmail,
      organization: signUpOrg,
      role: 'Research Analyst',
    };
    setStatusMessage(`Account created for ${signUpName}. Launching dashboard...`);
    setTimeout(() => {
      onLogin(user);
      onEnterApp('overview');
    }, 450);
  };

  return (
    <div className="akasa-landing-root">
      <div className="akasa-landing-shell">
        <div className="akasa-modal-card">
          {/* ── LEFT PANEL: Warm Neutral with apix, Features & Aeroplane Under It ── */}
          <section className="akasa-left-panel" aria-label="APIx Introduction">
            <div className="akasa-left-content">
              {/* Accreditation Badge */}
              <div className="akasa-accreditation-pill">
                <span className="akasa-pill-dot" />
                <span>SIH 2026 • MoSPI ALIGNED • CPI 2024 = 100</span>
              </div>

              {/* apix Brand Heading */}
              <div className="akasa-brand-header">
                <h1 className="akasa-brand-title">apix</h1>
                <span className="akasa-brand-sub">E L E V A T E</span>
              </div>

              {/* Same text as before */}
              <h2 className="akasa-tagline">
                Indian Airfare Price Index & High-Frequency Aviation Econometric Terminal
              </h2>

              <p className="akasa-description">
                Standardised hedonic price measurement across India's domestic aviation network.
                Powered by daily Jevons geometric aggregates, lead-time booking curve tracking,
                and real-time what-if basket reweighting.
              </p>

              {/* Feature items with clean circular outline SVG icons (no emojis) */}
              <div className="akasa-features-list">
                <div className="akasa-feature-row">
                  <div className="akasa-feature-icon-circle">
                    {/* Trending Chart Line SVG */}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
                      <polyline points="16 7 22 7 22 13" />
                    </svg>
                  </div>
                  <div className="akasa-feature-text">
                    <strong>MoSPI Jevons Formula</strong>
                    <span>Geometric price relatives without arbitrary arithmetic bias</span>
                  </div>
                </div>

                <div className="akasa-feature-row">
                  <div className="akasa-feature-icon-circle">
                    {/* Clock / Lead Times SVG */}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <div className="akasa-feature-text">
                    <strong>6 Lead-Time Curves</strong>
                    <span>Daily tracking across 1d, 7d, 15d, 21d, 30d and 45d advance tiers</span>
                  </div>
                </div>

                <div className="akasa-feature-row">
                  <div className="akasa-feature-icon-circle">
                    {/* Sliders / Tuning SVG */}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="4" y1="21" x2="4" y2="14" />
                      <line x1="4" y1="10" x2="4" y2="3" />
                      <line x1="12" y1="21" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12" y2="3" />
                      <line x1="20" y1="21" x2="20" y2="16" />
                      <line x1="20" y1="12" x2="20" y2="3" />
                      <line x1="1" y1="14" x2="7" y2="14" />
                      <line x1="9" y1="8" x2="15" y2="8" />
                      <line x1="17" y1="16" x2="23" y2="16" />
                    </svg>
                  </div>
                  <div className="akasa-feature-text">
                    <strong>Real-Time Sensitivity</strong>
                    <span>Instant browser recomputation of route & booking window weights</span>
                  </div>
                </div>

                <div className="akasa-feature-row">
                  <div className="akasa-feature-icon-circle">
                    {/* Shield / Audit Verification SVG */}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                  </div>
                  <div className="akasa-feature-text">
                    <strong>Audited Pipeline</strong>
                    <span>Daily scheduled ingestion with anomaly screening & duplicate logs</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Aeroplane Under It (Rising from the bottom-left corner like the Akasa visual) ── */}
            <div className="akasa-aeroplane-underlay" aria-hidden="true">
              <svg
                className="akasa-aeroplane-svg"
                viewBox="0 0 540 280"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <linearGradient id="akasaFuselage" x1="40" y1="260" x2="480" y2="80" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#CBD5E1" />
                    <stop offset="25%" stopColor="#FFFFFF" />
                    <stop offset="70%" stopColor="#E2E8F0" />
                    <stop offset="100%" stopColor="#64748B" />
                  </linearGradient>

                  <linearGradient id="akasaWing" x1="120" y1="270" x2="350" y2="70" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#1E293B" />
                    <stop offset="45%" stopColor="#2A5FA5" />
                    <stop offset="75%" stopColor="#FA5A00" />
                    <stop offset="100%" stopColor="#FF7A00" />
                  </linearGradient>

                  <linearGradient id="akasaContrail" x1="0" y1="280" x2="320" y2="110" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="rgba(250,90,0,0)" />
                    <stop offset="60%" stopColor="rgba(250,90,0,0.15)" />
                    <stop offset="100%" stopColor="rgba(42,95,165,0.35)" />
                  </linearGradient>
                </defs>

                {/* Ascending Flight Vector / Contrail lines */}
                <path
                  d="M0 270 C80 250, 160 210, 310 135"
                  stroke="url(#akasaContrail)"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  strokeDasharray="5 5"
                />
                <path
                  d="M20 280 C110 260, 190 220, 335 150"
                  stroke="url(#akasaContrail)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />

                {/* Compass & Waypoint Grid rings */}
                <circle cx="360" cy="130" r="110" stroke="rgba(26,43,60,0.06)" strokeWidth="1" strokeDasharray="3 3" />
                <circle cx="360" cy="130" r="65" stroke="rgba(250,90,0,0.12)" strokeWidth="1" />

                {/* Angled Passenger Airliner soaring upwards */}
                <g transform="translate(140, 40) rotate(-26 180 120)">
                  {/* Left Wing */}
                  <path
                    d="M160 110 L100 24 Q95 18 108 20 L140 24 L210 108 Z"
                    fill="url(#akasaWing)"
                    stroke="#1E293B"
                    strokeWidth="1.2"
                  />
                  {/* Left Winglet in vibrant Akasa orange */}
                  <path d="M102 20 L96 6 L110 10 L107 22 Z" fill="#FA5A00" />
                  <circle cx="98" cy="8" r="3" fill="#EF4444" />

                  {/* Port Engine */}
                  <rect x="145" y="78" width="46" height="13" rx="6" fill="#334155" />
                  <ellipse cx="188" cy="84.5" rx="3" ry="6" fill="#FA5A00" />

                  {/* Tailplane */}
                  <path d="M40 115 L5 78 L20 76 L70 114 Z" fill="#475569" />
                  <path d="M40 125 L5 162 L20 164 L70 126 Z" fill="#475569" />

                  {/* Right Wing */}
                  <path
                    d="M160 130 L100 216 Q95 222 108 220 L140 216 L210 132 Z"
                    fill="url(#akasaWing)"
                    stroke="#1E293B"
                    strokeWidth="1.2"
                  />
                  {/* Right Winglet in vibrant Akasa orange */}
                  <path d="M102 220 L96 234 L110 230 L107 218 Z" fill="#FA5A00" />
                  <circle cx="98" cy="232" r="3" fill="#10B981" />

                  {/* Starboard Engine */}
                  <rect x="145" y="149" width="46" height="13" rx="6" fill="#334155" />
                  <ellipse cx="188" cy="155.5" rx="3" ry="6" fill="#FA5A00" />

                  {/* Central Aerodynamic Fuselage */}
                  <path
                    d="M15 120 C15 115, 45 109, 90 109 L310 109 C345 109, 375 115, 390 120 C375 125, 345 131, 310 131 L90 131 C45 131, 15 125, 15 120 Z"
                    fill="url(#akasaFuselage)"
                    stroke="#1A2B3C"
                    strokeWidth="1.8"
                  />

                  {/* Cockpit Windshield */}
                  <polygon points="348,116 368,119 368,121 348,124 346,120" fill="#0F172A" />
                  <polygon points="352,117 365,119 365,121 352,123" fill="#38BDF8" opacity="0.9" />

                  {/* Passenger Windows */}
                  {Array.from({ length: 16 }).map((_, idx) => (
                    <circle key={idx} cx={110 + idx * 12} cy={120} r={1.6} fill="#1E293B" opacity="0.8" />
                  ))}

                  {/* Akasa Sunset Speedline Livery */}
                  <path
                    d="M90 119 L320 119 C340 119, 355 119.5, 365 120 C355 120.5, 340 121, 320 121 L90 121 Z"
                    fill="#FA5A00"
                  />

                  {/* Vertical Stabilizer Tail */}
                  <path d="M25 120 L65 120 L45 108 L20 109 Z" fill="#2A5FA5" />
                </g>
              </svg>

              <div className="akasa-telemetry-pill font-num">
                <span>DEL ➔ BOM ➔ BLR</span>
                <span className="telemetry-sep">•</span>
                <span>FL370</span>
                <span className="telemetry-sep">•</span>
                <span>M 0.78</span>
              </div>
            </div>
          </section>

          {/* ── RIGHT PANEL: Clean Minimalist Authentication ── */}
          <section className="akasa-right-panel" aria-label="Terminal Login and Registration">
            {/* Top Action Buttons (Akasa Style) */}
            <div className="akasa-top-cta-group">
              <button
                type="button"
                className={`akasa-cta-join${authMode === 'signup' ? ' active' : ''}`}
                onClick={() => {
                  setAuthMode('signup');
                  setStatusMessage(null);
                }}
              >
                Join APIx Terminal
              </button>

              <div className="akasa-cta-divider">
                <span>Already a member?</span>
              </div>

              <button
                type="button"
                className={`akasa-cta-login${authMode === 'signin' ? ' active' : ''}`}
                onClick={() => {
                  setAuthMode('signin');
                  setStatusMessage(null);
                }}
              >
                Login
              </button>
            </div>

            {/* Notification Banner */}
            {statusMessage && (
              <div className="akasa-status-toast" role="alert">
                <span className="akasa-toast-indicator" />
                <span>{statusMessage}</span>
              </div>
            )}

            {/* Active User Alert if logged in */}
            {currentUser && (
              <div className="akasa-logged-card">
                <div>
                  <div className="akasa-logged-title">Signed In</div>
                  <div className="akasa-logged-user font-num">
                    {currentUser.name} ({currentUser.organization})
                  </div>
                </div>
                <button
                  type="button"
                  className="akasa-direct-dash-btn"
                  onClick={() => onEnterApp('overview')}
                >
                  Enter Terminal &rarr;
                </button>
              </div>
            )}

            {/* ── Sign In Form ── */}
            {authMode === 'signin' && (
              <form className="akasa-auth-form" onSubmit={handleSignIn}>
                <div className="akasa-form-header">
                  <h3 className="akasa-form-title">Terminal Sign In</h3>
                  <p className="akasa-form-sub">
                    Access verified national airfare series, micro-indexes, and booking curves.
                  </p>
                </div>

                <div className="akasa-field-group">
                  <label htmlFor={emailId} className="akasa-field-label">
                    Official Work Email / Terminal ID
                  </label>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      {/* Mail SVG Icon */}
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                        <polyline points="22,6 12,13 2,6" />
                      </svg>
                    </span>
                    <input
                      id={emailId}
                      type="email"
                      className="akasa-input"
                      placeholder="analyst@aviation.gov.in"
                      value={signInEmail}
                      onChange={(e) => setSignInEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="akasa-field-group">
                  <div className="akasa-label-split">
                    <label htmlFor={passId} className="akasa-field-label">
                      Terminal Password
                    </label>
                    <button
                      type="button"
                      className="akasa-text-link"
                      onClick={() => setStatusMessage('Password reset link dispatched to authorized gateway.')}
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      {/* Lock SVG Icon */}
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      id={passId}
                      type={showPassword ? 'text' : 'password'}
                      className="akasa-input"
                      value={signInPassword}
                      onChange={(e) => setSignInPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="akasa-eye-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="akasa-checkbox-row">
                  <label className="akasa-checkbox-label">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                    />
                    <span>Remember terminal authentication</span>
                  </label>
                </div>

                <button type="submit" className="akasa-submit-btn">
                  Sign In to Terminal &rarr;
                </button>

                {/* Instant Evaluator Demo Access (No emojis) */}
                <div className="akasa-form-divider">
                  <span>OR EVALUATOR DEMO</span>
                </div>

                <button
                  type="button"
                  className="akasa-demo-button"
                  onClick={handleQuickDemo}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                  <span>Instant Demo: MoSPI Principal Analyst</span>
                </button>

                <div className="akasa-guest-wrap">
                  <button
                    type="button"
                    className="akasa-guest-link"
                    onClick={() => onEnterApp('overview')}
                  >
                    Continue as Guest Observer &rarr;
                  </button>
                </div>
              </form>
            )}

            {/* ── Sign Up Form ── */}
            {authMode === 'signup' && (
              <form className="akasa-auth-form" onSubmit={handleSignUp}>
                <div className="akasa-form-header">
                  <h3 className="akasa-form-title">Join APIx Terminal</h3>
                  <p className="akasa-form-sub">
                    Register for authorized analyst privileges on the Indian Airfare Price Index.
                  </p>
                </div>

                <div className="akasa-field-group">
                  <label htmlFor={upNameId} className="akasa-field-label">
                    Full Name
                  </label>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </span>
                    <input
                      id={upNameId}
                      type="text"
                      className="akasa-input"
                      placeholder="e.g. Vraj Verma"
                      value={signUpName}
                      onChange={(e) => setSignUpName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="akasa-field-group">
                  <label htmlFor={upEmailId} className="akasa-field-label">
                    Institutional Email
                  </label>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                        <polyline points="22,6 12,13 2,6" />
                      </svg>
                    </span>
                    <input
                      id={upEmailId}
                      type="email"
                      className="akasa-input"
                      placeholder="name@organization.gov.in"
                      value={signUpEmail}
                      onChange={(e) => setSignUpEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="akasa-field-group">
                  <label htmlFor={upOrgId} className="akasa-field-label">
                    Department / Organization
                  </label>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
                        <line x1="9" y1="22" x2="9" y2="2" />
                      </svg>
                    </span>
                    <select
                      id={upOrgId}
                      className="akasa-select"
                      value={signUpOrg}
                      onChange={(e) => setSignUpOrg(e.target.value)}
                    >
                      <option value="Ministry of Statistics (MoSPI)">Ministry of Statistics (MoSPI)</option>
                      <option value="Directorate General of Civil Aviation (DGCA)">DGCA / Ministry of Civil Aviation</option>
                      <option value="Airline Revenue Management (IndiGo, Air India)">Airline Revenue Management & Pricing</option>
                      <option value="Aviation Economics & Policy Research">Aviation Economics / Policy Think Tank</option>
                      <option value="Academic & Statistical Research">Academic & Econometric Research</option>
                    </select>
                  </div>
                </div>

                <div className="akasa-field-group">
                  <label htmlFor={upPassId} className="akasa-field-label">
                    Create Password
                  </label>
                  <div className="akasa-input-box">
                    <span className="akasa-input-svg">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      id={upPassId}
                      type={showPassword ? 'text' : 'password'}
                      className="akasa-input"
                      placeholder="Minimum 8 characters"
                      value={signUpPassword}
                      onChange={(e) => setSignUpPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="akasa-checkbox-row">
                  <label className="akasa-checkbox-label">
                    <input
                      type="checkbox"
                      checked={agreeTerms}
                      onChange={(e) => setAgreeTerms(e.target.checked)}
                      required
                    />
                    <span>I adhere to statistical data governance protocols</span>
                  </label>
                </div>

                <button type="submit" className="akasa-submit-btn">
                  Register & Launch Terminal &rarr;
                </button>

                <div className="akasa-switch-row">
                  Already have access?{' '}
                  <button
                    type="button"
                    className="akasa-text-link"
                    onClick={() => setAuthMode('signin')}
                  >
                    Sign in here
                  </button>
                </div>
              </form>
            )}

            {/* Footer Compliance Security */}
            <div className="akasa-card-footer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>256-Bit Encrypted Research Gateway • MoSPI Compliance Standard</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
