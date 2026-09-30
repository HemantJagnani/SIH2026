import React from 'react';

interface LogoProps {
  size?: number;
  style?: React.CSSProperties;
}

export const IndiGoLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="IndiGo"
  >
    <rect width="32" height="32" rx="4" fill="#001B94" />
    {/* Stylized IndiGo dot matrix wing and 6E insignia */}
    <circle cx="8" cy="16" r="2.2" fill="#FFFFFF" />
    <circle cx="13" cy="11.5" r="2.2" fill="#FFFFFF" />
    <circle cx="18" cy="8.5" r="2.2" fill="#FFFFFF" />
    <circle cx="23" cy="7" r="2.2" fill="#FFFFFF" />
    <circle cx="13" cy="20.5" r="2.2" fill="#FFFFFF" opacity="0.8" />
    <circle cx="18" cy="23.5" r="2.2" fill="#FFFFFF" opacity="0.8" />
    <circle cx="23" cy="25" r="2.2" fill="#FFFFFF" opacity="0.8" />
    <path
      d="M17 14.5L25 10L24 16L17 17.5V14.5Z"
      fill="#00AEEF"
    />
  </svg>
);

export const AirIndiaLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Air India"
  >
    <rect width="32" height="32" rx="4" fill="#C8102E" />
    {/* Golden Sun & Red Swan arch */}
    <circle cx="14" cy="15" r="5" fill="#FDB913" />
    <path
      d="M9 22C11 16 16 10 24 8C20 12 18 17 19 22C16 19 12 19 9 22Z"
      fill="#FFFFFF"
    />
    <path
      d="M24 8C21 11 19 14 18 19C17 15 19 11 24 8Z"
      fill="#FDB913"
    />
  </svg>
);

export const VistaraLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Vistara"
  >
    <rect width="32" height="32" rx="4" fill="#4B1238" />
    {/* Vistara 8-point geometric star */}
    <path
      d="M16 6L18 12.5L24.5 10.5L20.5 16L26 19L19.5 20L19 26.5L15 21.5L9.5 24.5L12 18.5L6 16L12.5 13.5L10 7L16 11.5V6Z"
      fill="#DAAA00"
    />
    <circle cx="16" cy="16" r="2.5" fill="#FFFFFF" />
  </svg>
);

export const AkasaAirLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Akasa Air"
  >
    <rect width="32" height="32" rx="4" fill="#FF5E00" />
    {/* Soaring Purple & Sunrise Chevron */}
    <path
      d="M8 24L16 10L24 24L16 20L8 24Z"
      fill="#4F2683"
    />
    <path
      d="M11 21L16 13L21 21L16 18.5L11 21Z"
      fill="#FFFFFF"
    />
  </svg>
);

export const SpiceJetLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="SpiceJet"
  >
    <rect width="32" height="32" rx="4" fill="#ED1C24" />
    {/* Signature SpiceJet 5-chili dots / burst */}
    <circle cx="9" cy="16" r="2.8" fill="#FFFFFF" />
    <circle cx="14" cy="11" r="2.5" fill="#FFFFFF" />
    <circle cx="19" cy="8" r="2.2" fill="#FFFFFF" />
    <circle cx="23" cy="15" r="2.6" fill="#FDB913" />
    <circle cx="16" cy="22" r="2.8" fill="#FFFFFF" />
  </svg>
);

export const AirlineLogo: React.FC<{ code: string; name?: string; size?: number }> = ({
  code,
  name,
  size = 22,
}) => {
  const c = code.toUpperCase();
  if (c.includes('6E') || name?.toLowerCase().includes('indigo')) {
    return <IndiGoLogo size={size} />;
  }
  if (c.includes('AI') || name?.toLowerCase().includes('air india')) {
    return <AirIndiaLogo size={size} />;
  }
  if (c.includes('UK') || name?.toLowerCase().includes('vistara')) {
    return <VistaraLogo size={size} />;
  }
  if (c.includes('QP') || name?.toLowerCase().includes('akasa')) {
    return <AkasaAirLogo size={size} />;
  }
  if (c.includes('SG') || name?.toLowerCase().includes('spicejet')) {
    return <SpiceJetLogo size={size} />;
  }
  // Generic fallback aviation badge
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-label={code}>
      <rect width="32" height="32" rx="4" fill="#1A2B3C" />
      <path
        d="M16 7L18.5 14L25 16L18.5 18L16 25L13.5 18L7 16L13.5 14L16 7Z"
        fill="#FFFFFF"
      />
    </svg>
  );
};

export const EaseMyTripLogo: React.FC<LogoProps> = ({ size = 22, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="EaseMyTrip"
  >
    <rect width="32" height="32" rx="4" fill="#0A58CA" />
    {/* EaseMyTrip signature paper plane & speed sweep */}
    <path
      d="M7 16L25 9L18 25L14.5 18.5L7 16Z"
      fill="#FFFFFF"
    />
    <path
      d="M14.5 18.5L25 9L16 20.5L14.5 18.5Z"
      fill="#00D2FF"
    />
  </svg>
);

export const GoogleFlightsLogo: React.FC<LogoProps> = ({ size = 22, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Google Flights"
  >
    <rect width="32" height="32" rx="4" fill="#FFFFFF" stroke="#C9D0CB" strokeWidth="1" />
    {/* Google 4-color airplane icon */}
    <path
      d="M16 6L19 13.5L25.5 16L19 18.5L16 26L13 18.5L6.5 16L13 13.5L16 6Z"
      fill="#4285F4"
    />
    <path d="M16 6L19 13.5L16 16L13 13.5L16 6Z" fill="#EA4335" />
    <path d="M19 13.5L25.5 16L19 18.5L16 16L19 13.5Z" fill="#FBBC05" />
    <path d="M16 16L19 18.5L16 26L13 18.5L16 16Z" fill="#34A853" />
  </svg>
);

export const OTAConsensusLogo: React.FC<LogoProps> = ({ size = 22, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="OTA Consensus"
  >
    <rect width="32" height="32" rx="4" fill="#2F7D6D" />
    {/* Verified Consensus Node Check */}
    <circle cx="16" cy="16" r="9" stroke="#FFFFFF" strokeWidth="2" fill="none" />
    <path
      d="M12 16.5L15 19.5L20.5 13"
      stroke="#FFFFFF"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const ScraperSourceBadge: React.FC<{ source: string; size?: number }> = ({
  source,
  size = 18,
}) => {
  const s = source.toLowerCase();
  if (s.includes('easemytrip') || s.includes('emt')) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
        <EaseMyTripLogo size={size} />
        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>EaseMyTrip</span>
      </div>
    );
  }
  if (s.includes('google')) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
        <GoogleFlightsLogo size={size} />
        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>Google Flights</span>
      </div>
    );
  }
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
      <OTAConsensusLogo size={size} />
      <span style={{ fontWeight: 600, color: 'var(--ink)' }}>OTA Consensus</span>
    </div>
  );
};
