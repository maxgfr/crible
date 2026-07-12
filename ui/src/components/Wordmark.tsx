// T-016 — the crible wordmark: sieve glyph (circle + interrupted diagonal
// hatching — the lines that pass through) + « crible » in the tool's mono
// voice. Amber on dark, ink on light (see styles.css .wordmark).

export function Wordmark() {
  return (
    <h1 className="wordmark">
      <svg
        aria-hidden="true"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
      >
        <defs>
          <clipPath id="sieve-bowl">
            <circle cx="12" cy="12" r="8.2" />
          </clipPath>
        </defs>
        <circle cx="12" cy="12" r="9" strokeWidth="1.75" />
        <g clipPath="url(#sieve-bowl)" strokeWidth="1.4" strokeDasharray="3 2.4">
          <line x1="2" y1="16" x2="16" y2="2" />
          <line x1="5" y1="21" x2="21" y2="5" />
          <line x1="10" y1="24" x2="24" y2="10" />
        </g>
      </svg>
      crible
    </h1>
  );
}
