export function WobbleFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false">
      <filter id="wobble">
        <feTurbulence
          type="fractalNoise"
          baseFrequency="0.014"
          numOctaves="3"
          seed="7"
          result="noise"
        />
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" />
      </filter>
    </svg>
  )
}
