/**
 * 손그림 테두리를 만드는 SVG 왜곡 필터.
 *
 * feTurbulence로 노이즈를 만들고 feDisplacementMap으로 선을 밀어 구불거리게 한다.
 * 앱에 한 번만 심어두면 CSS에서 filter: url(#wobble) 로 갖다 쓴다.
 */
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
        {/* scale이 클수록 많이 흔들린다. 2.5 정도가 '대충 그린' 느낌 */}
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" />
      </filter>
    </svg>
  )
}
