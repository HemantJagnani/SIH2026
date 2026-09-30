import React, { useMemo } from 'react';
import katex from 'katex';

interface MathBlockProps {
  formula: string;
  caption?: string;
  block?: boolean;
  style?: React.CSSProperties;
}

export const MathBlock: React.FC<MathBlockProps> = ({
  formula,
  caption,
  block = true,
  style,
}) => {
  const renderedHtml = useMemo(() => {
    try {
      return katex.renderToString(formula, {
        displayMode: block,
        throwOnError: false,
      });
    } catch {
      return formula;
    }
  }, [formula, block]);

  return (
    <div
      style={{
        margin: '10px 0',
        padding: '12px 18px',
        background: 'var(--vellum)',
        border: '1px solid var(--contour)',
        overflowX: 'auto',
        ...style,
      }}
    >
      <div
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
        style={{
          fontSize: '18px',
          color: 'var(--ink)',
          lineHeight: 1.4,
        }}
      />
      {caption && (
        <div
          style={{
            fontFamily: "'B612', monospace",
            fontSize: '11px',
            color: 'var(--ink-2)',
            marginTop: '6px',
            borderTop: '1px solid var(--contour)',
            paddingTop: '4px',
          }}
        >
          {caption}
        </div>
      )}
    </div>
  );
};