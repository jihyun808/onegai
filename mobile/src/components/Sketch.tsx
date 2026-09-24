import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { StyleSheet, View, type LayoutChangeEvent, type StyleProp, type ViewStyle } from 'react-native'
import Svg, { Path } from 'react-native-svg'

import { colors } from '../theme'

/**
 * 손그림 테두리.
 *
 * 웹은 테두리에 SVG 왜곡 필터(feTurbulence + feDisplacementMap)를 걸어 선을
 * 구불거리게 했다. 네이티브에는 그 필터가 없어서 **선을 직접 그린다** —
 * 상자 둘레를 따라 점을 찍고, 부드러운 노이즈만큼 바깥/안쪽으로 밀어 잇는다.
 *
 * 모서리는 웹과 같은 불규칙한 타원 반경을 쓴다
 * (`140px 18px 130px 20px / 20px 120px 22px 130px`). 카드마다 모양과 흔들림을
 * 조금씩 달리한다 — 같은 도형이 반복되면 손그림 느낌이 죽는다.
 */

/** [가로 TL, TR, BR, BL, 세로 TL, TR, BR, BL] — 웹 global.css의 .sketch 세 가지 */
const SHAPES = [
  [140, 18, 130, 20, 20, 120, 22, 130],
  [20, 130, 22, 140, 130, 20, 120, 24],
  [120, 24, 140, 18, 24, 140, 18, 120],
] as const

/** 흔들림 폭. 웹 필터의 scale 2.5 → 최대 ±1.25px 정도 밀린다. */
const AMPLITUDE = 1.3
/** 점 간격(px). 촘촘할수록 매끄럽다. */
const STEP = 3
/** 흔들린 선이 잘리지 않게 캔버스를 이만큼 넓힌다 */
const PAD = 4

export const SKETCH_STROKE = 1

/** 씨앗이 같으면 같은 모양. 리렌더마다 선이 떨리면 안 된다. */
function random(seed: number) {
  let s = seed || 1
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

/** 둘레 길이 s에서의 밀림 값. 파장이 다른 사인 셋을 겹쳐 규칙성을 숨긴다. */
function makeNoise(seed: number) {
  const rand = random(seed)
  const waves = [55, 90, 140].map((wavelength) => ({
    k: (2 * Math.PI) / (wavelength * (0.8 + rand() * 0.4)),
    phase: rand() * Math.PI * 2,
    weight: 0.4 + rand() * 0.6,
  }))
  const total = waves.reduce((sum, w) => sum + w.weight, 0)
  return (s: number) =>
    (waves.reduce((sum, w) => sum + w.weight * Math.sin(w.k * s + w.phase), 0) / total) *
    AMPLITUDE
}

export function sketchPath(width: number, height: number, variant: number, seed: number) {
  const [hTL, hTR, hBR, hBL, vTL, vTR, vBR, vBL] = SHAPES[variant % SHAPES.length]

  // CSS와 같은 규칙으로 반경을 줄인다: 한 변에 붙은 두 반경의 합이 변보다 길면
  // 모든 반경을 같은 비율로 줄인다. 그래서 넓은 카드는 둥근 렌즈 모양이 된다.
  const f = Math.min(
    1,
    width / (hTL + hTR),
    width / (hBL + hBR),
    height / (vTL + vBL),
    height / (vTR + vBR),
  )
  const r = {
    tl: [hTL * f, vTL * f],
    tr: [hTR * f, vTR * f],
    br: [hBR * f, vBR * f],
    bl: [hBL * f, vBL * f],
  }

  // 둘레를 이루는 조각들. 각 조각은 t∈[0,1]에서 점과 바깥쪽 법선을 돌려준다.
  type Seg = { len: number; at: (t: number) => [number, number, number, number] }
  const line = (x0: number, y0: number, x1: number, y1: number, nx: number, ny: number): Seg => ({
    len: Math.hypot(x1 - x0, y1 - y0),
    at: (t) => [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, nx, ny],
  })
  // 타원 사분호. a0→a1 각도(라디안)로 돈다.
  const arc = (cx: number, cy: number, rx: number, ry: number, a0: number, a1: number): Seg => ({
    // 라마누잔 근사의 1/4
    len: (Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)))) / 4,
    at: (t) => {
      const a = a0 + (a1 - a0) * t
      const x = cx + rx * Math.cos(a)
      const y = cy + ry * Math.sin(a)
      // 타원의 바깥 법선
      const nx = Math.cos(a) / (rx || 1)
      const ny = Math.sin(a) / (ry || 1)
      const n = Math.hypot(nx, ny) || 1
      return [x, y, nx / n, ny / n]
    },
  })

  const w = width
  const h = height
  const P = Math.PI
  const segs: Seg[] = [
    line(r.tl[0], 0, w - r.tr[0], 0, 0, -1),
    arc(w - r.tr[0], r.tr[1], r.tr[0], r.tr[1], -P / 2, 0),
    line(w, r.tr[1], w, h - r.br[1], 1, 0),
    arc(w - r.br[0], h - r.br[1], r.br[0], r.br[1], 0, P / 2),
    line(w - r.br[0], h, r.bl[0], h, 0, 1),
    arc(r.bl[0], h - r.bl[1], r.bl[0], r.bl[1], P / 2, P),
    line(0, h - r.bl[1], 0, r.tl[1], -1, 0),
    arc(r.tl[0], r.tl[1], r.tl[0], r.tl[1], P, (3 * P) / 2),
  ]

  const noise = makeNoise(seed)
  const perimeter = segs.reduce((sum, seg) => sum + seg.len, 0)
  // 끝점에서 이음매가 튀지 않도록 마지막 구간은 시작 값으로 서서히 되돌린다
  const closeSpan = Math.min(40, perimeter / 4)
  const offsetAt = (s: number) => {
    const d = noise(s)
    const fromEnd = perimeter - s
    if (fromEnd >= closeSpan) return d
    const t = fromEnd / closeSpan
    return d * t + noise(0) * (1 - t)
  }

  const points: string[] = []
  let s = 0
  for (const seg of segs) {
    const n = Math.max(1, Math.ceil(seg.len / STEP))
    for (let i = 0; i < n; i++) {
      const [x, y, nx, ny] = seg.at(i / n)
      const d = offsetAt(s + (seg.len * i) / n)
      points.push(`${(x + nx * d + PAD).toFixed(2)},${(y + ny * d + PAD).toFixed(2)}`)
    }
    s += seg.len
  }
  return `M${points.join('L')}Z`
}

/** 문자열에서 씨앗을 만든다. 같은 곡 카드는 언제 봐도 같은 선이다. */
export function hashSeed(text: string) {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h) % 2147483646 || 7
}

interface Props {
  /** 모서리 모양. 목록에서는 순번을 넘겨 카드마다 달리한다. */
  variant?: number
  /** 흔들림 씨앗. 생략하면 variant에서 만든다. */
  seed?: number
  style?: StyleProp<ViewStyle>
  children?: React.ReactNode
}

export function Sketch({ variant = 0, seed, style, children }: Props) {
  const ref = useRef<View>(null)
  const [size, setSize] = useState<{ w: number; h: number } | null>(null)

  function resize(width: number, height: number) {
    // 소수점 떨림으로 경로를 매번 다시 만들지 않게 반올림해서 비교한다
    const w = Math.round(width)
    const h = Math.round(height)
    setSize((prev) => (prev && prev.w === w && prev.h === h ? prev : { w, h }))
  }

  // **첫 그림부터 테두리가 있어야 한다.** onLayout만 쓰면 테두리 없이 한 번 칠해진
  // 뒤에야 크기가 도착해서, 카드가 먼저 뜨고 낙서가 한 박자 늦게 따라온다.
  // 새 아키텍처에서는 레이아웃 이펙트 안의 measure가 칠하기 전에 동기로 답한다.
  useLayoutEffect(() => {
    ref.current?.measure((_x, _y, width, height) => resize(width, height))
  }, [])

  // 크기가 바뀌는 경우(제목이 두 줄이 되는 등)는 onLayout이 따라잡는다
  function onLayout(event: LayoutChangeEvent) {
    const { width, height } = event.nativeEvent.layout
    resize(width, height)
  }

  const d = useMemo(
    () => (size ? sketchPath(size.w, size.h, variant, seed ?? variant * 7919 + 7) : null),
    [size, variant, seed],
  )

  return (
    <View ref={ref} style={style} onLayout={onLayout}>
      {size && d && (
        <Svg
          width={size.w + PAD * 2}
          height={size.h + PAD * 2}
          style={styles.canvas}
          pointerEvents="none"
        >
          {/* 면도 함께 칠해 배경이 손그림 선을 따라가게 한다 */}
          <Path
            d={d}
            fill={colors.paper}
            stroke={colors.line}
            strokeWidth={SKETCH_STROKE}
            strokeLinejoin="round"
          />
        </Svg>
      )}
      {children}
    </View>
  )
}

const styles = StyleSheet.create({
  canvas: { position: 'absolute', left: -PAD, top: -PAD },
})
