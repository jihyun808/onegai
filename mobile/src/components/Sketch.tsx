import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { StyleSheet, View, type LayoutChangeEvent, type StyleProp, type ViewStyle } from 'react-native'
import Svg, { Path } from 'react-native-svg'

import { colors } from '../theme'

const SHAPES = [
  [140, 18, 130, 20, 20, 120, 22, 130],
  [20, 130, 22, 140, 130, 20, 120, 24],
  [120, 24, 140, 18, 24, 140, 18, 120],
] as const

const AMPLITUDE = 1.3
const STEP = 3
const PAD = 4

export const SKETCH_STROKE = 1

function random(seed: number) {
  let s = seed || 1
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

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

  type Seg = { len: number; at: (t: number) => [number, number, number, number] }
  const line = (x0: number, y0: number, x1: number, y1: number, nx: number, ny: number): Seg => ({
    len: Math.hypot(x1 - x0, y1 - y0),
    at: (t) => [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, nx, ny],
  })
  const arc = (cx: number, cy: number, rx: number, ry: number, a0: number, a1: number): Seg => ({
    len: (Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)))) / 4,
    at: (t) => {
      const a = a0 + (a1 - a0) * t
      const x = cx + rx * Math.cos(a)
      const y = cy + ry * Math.sin(a)
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

export function hashSeed(text: string) {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h) % 2147483646 || 7
}

interface Props {
  variant?: number
  seed?: number
  style?: StyleProp<ViewStyle>
  children?: React.ReactNode
}

export function Sketch({ variant = 0, seed, style, children }: Props) {
  const ref = useRef<View>(null)
  const [size, setSize] = useState<{ w: number; h: number } | null>(null)

  function resize(width: number, height: number) {
    const w = Math.round(width)
    const h = Math.round(height)
    setSize((prev) => (prev && prev.w === w && prev.h === h ? prev : { w, h }))
  }

  useLayoutEffect(() => {
    ref.current?.measure((_x, _y, width, height) => resize(width, height))
  }, [])

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
