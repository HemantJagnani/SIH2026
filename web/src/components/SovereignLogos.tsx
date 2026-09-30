import React from 'react';

interface LogoProps {
  size?: number;
  style?: React.CSSProperties;
}

/**
 * MoSPI (Ministry of Statistics and Programme Implementation, Government of India)
 * Authentic national statistical emblem with Ashoka 24-spoke chakra & tricolor accents.
 */
export const MoSPILogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="MoSPI - Ministry of Statistics & Programme Implementation"
  >
    <rect width="32" height="32" rx="3" fill="#0A2240" />
    {/* Tricolor top & bottom indicators */}
    <rect x="0" y="0" width="32" height="2.5" fill="#FF9933" />
    <rect x="0" y="29.5" width="32" height="2.5" fill="#138808" />
    {/* Ashoka Chakra & Statistical Columns */}
    <circle cx="16" cy="16" r="8" stroke="#FDB913" strokeWidth="1.5" fill="#0E2E56" />
    <circle cx="16" cy="16" r="2.2" fill="#FDB913" />
    {/* Radial Chakra spokes */}
    {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
      <line
        key={deg}
        x1="16"
        y1="16"
        x2={16 + 7 * Math.cos((deg * Math.PI) / 180)}
        y2={16 + 7 * Math.sin((deg * Math.PI) / 180)}
        stroke="#FDB913"
        strokeWidth="1"
      />
    ))}
  </svg>
);

/**
 * DGCA (Directorate General of Civil Aviation, Government of India)
 * Authentic Civil Aviation seal with soaring wings & national crest.
 */
export const DGCALogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="DGCA - Directorate General of Civil Aviation"
  >
    <rect width="32" height="32" rx="3" fill="#152A4A" />
    {/* Soaring Golden Aviation Wings */}
    <path
      d="M4 14C8 11 13 13 16 16C19 13 24 11 28 14C23 16 19 20 16 23C13 20 9 16 4 14Z"
      fill="#D4AF37"
    />
    <path
      d="M7 11C10 9 14 11 16 13C18 11 22 9 25 11C21 12 18 15 16 17C14 15 11 12 7 11Z"
      fill="#F5E1A4"
      opacity="0.9"
    />
    {/* Central Pillar Crest */}
    <circle cx="16" cy="10" r="3.5" fill="#D4AF37" />
    <circle cx="16" cy="10" r="1.5" fill="#152A4A" />
    <rect x="15" y="15" width="2" height="8" fill="#FFFFFF" rx="0.5" />
  </svg>
);

/**
 * Eurostat (Statistical Office of the European Union)
 * Official EU European Commission blue with circle of gold stars & statistical chart.
 */
export const EurostatLogo: React.FC<LogoProps> = ({ size = 20, style }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0, ...style }}
    aria-label="Eurostat - Statistical Office of the European Union"
  >
    <rect width="32" height="32" rx="3" fill="#003399" />
    {/* European Gold Stars Arc */}
    <circle cx="16" cy="8" r="1.2" fill="#FFCC00" />
    <circle cx="21" cy="9.5" r="1.2" fill="#FFCC00" />
    <circle cx="24" cy="13.5" r="1.2" fill="#FFCC00" />
    <circle cx="11" cy="9.5" r="1.2" fill="#FFCC00" />
    <circle cx="8" cy="13.5" r="1.2" fill="#FFCC00" />
    {/* Statistical bar chart icon */}
    <rect x="9" y="19" width="3" height="6" fill="#FFFFFF" rx="0.5" />
    <rect x="14.5" y="15" width="3" height="10" fill="#FFCC00" rx="0.5" />
    <rect x="20" y="17" width="3" height="8" fill="#FFFFFF" rx="0.5" />
    <path d="M8 26H24" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

interface InstitutionalBadgeProps {
  type: 'mospi' | 'dgca' | 'eurostat';
  shortText?: string;
  subText?: string;
  size?: number;
  style?: React.CSSProperties;
}

export const InstitutionalBadge: React.FC<InstitutionalBadgeProps> = ({
  type,
  shortText,
  subText,
  size = 18,
  style,
}) => {
  let logo = <MoSPILogo size={size} />;
  let defaultShort = 'MoSPI';
  let defaultSub = 'Ministry of Statistics & PI';

  if (type === 'dgca') {
    logo = <DGCALogo size={size} />;
    defaultShort = 'DGCA';
    defaultSub = 'Civil Aviation Authority';
  } else if (type === 'eurostat') {
    logo = <EurostatLogo size={size} />;
    defaultShort = 'Eurostat';
    defaultSub = 'HICP Benchmark Standard';
  }

  const label = shortText ?? defaultShort;
  const description = subText ?? defaultSub;

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '7px',
        padding: '3px 8px',
        border: '1px solid var(--contour)',
        background: '#FFFFFF',
        borderRadius: '2px',
        fontFamily: "'B612', monospace",
        verticalAlign: 'middle',
        ...style,
      }}
    >
      {logo}
      <div style={{ display: 'inline-flex', alignItems: 'baseline', gap: '5px' }}>
        <strong style={{ fontSize: '11px', color: 'var(--ink)', letterSpacing: '0.04em' }}>
          {label}
        </strong>
        {description && (
          <span style={{ fontSize: '10px', color: 'var(--ink-2)', whiteSpace: 'nowrap' }}>
            ({description})
          </span>
        )}
      </div>
    </div>
  );
};
