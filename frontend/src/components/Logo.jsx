import React from 'react';

/**
 * Universal Analyst mark — a query bracket holding a rising column of
 * measurement ticks, with an amber signal at the peak. Reads as
 * "a question asked of measured data". Monoline; scales to favicon size.
 *
 * The bracket uses currentColor (inherits ink), so place it on any surface.
 */
const Logo = ({ className = 'h-5 w-5', title = 'Universal Analyst' }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    role="img"
    aria-label={title}
    fill="none"
  >
    {/* Query bracket */}
    <path
      d="M8.5 4.5H6.25A1.75 1.75 0 0 0 4.5 6.25v11.5A1.75 1.75 0 0 0 6.25 19.5H8.5"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity="0.85"
    />
    {/* Rising data ticks (indigo) */}
    <rect x="10.5" y="15" width="2.2" height="4.5" rx="0.7" fill="#6366F1" />
    <rect x="14" y="11" width="2.2" height="8.5" rx="0.7" fill="#9098FB" />
    <rect x="17.5" y="7" width="2.2" height="12.5" rx="0.7" fill="#6366F1" />
    {/* Signal point at the peak (amber) */}
    <circle cx="18.6" cy="4.7" r="1.5" fill="#F0A92B" />
  </svg>
);

export default Logo;
