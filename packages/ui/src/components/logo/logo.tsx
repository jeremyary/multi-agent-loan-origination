export function Logo() {
  return (
    <svg
      width="44"
      height="44"
      viewBox="0 0 44 44"
      fill="none"
      className="h-12 w-12"
      aria-hidden="true"
    >
      <rect x="8" y="14" width="28" height="20" rx="6" fill="url(#robot-body)" />
      <rect x="21" y="9.5" width="2" height="4" rx="1" fill="url(#robot-head)" />
      <rect x="20.3" y="4.8" width="3.5" height="3.5" rx="2" fill="url(#robot-head)" />
      <rect x="13" y="21" width="4" height="4" rx="2" fill="#fff" />
      <rect x="27" y="21" width="4" height="4" rx="2" fill="#fff" />
      <defs>
        <linearGradient
          id="robot-body"
          x1="8"
          y1="14"
          x2="36"
          y2="32"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#38bdf8" />
          <stop offset="0.5" stopColor="#8b5cf6" />
          <stop offset="1" stopColor="#f472b6" />
        </linearGradient>
        <linearGradient
          id="robot-head"
          x1="16"
          y1="4"
          x2="28"
          y2="12"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#38bdf8" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}