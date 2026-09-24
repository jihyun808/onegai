import './Segmented.css'

export interface SegmentOption<T extends string> {
  value: T
  label: string
  /** 선택 시 강조색. 브랜드 필터에서 TJ/금영 색을 쓰기 위한 것. */
  tone?: 'tj' | 'kumyoung'
}

interface Props<T extends string> {
  label: string
  options: SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
}

/** 검색 타입 토글과 브랜드 필터가 같은 형태를 쓴다. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: Props<T>) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            className={`segmented__item ${selected ? 'is-selected' : ''} ${
              selected && option.tone ? `is-${option.tone}` : ''
            }`}
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
