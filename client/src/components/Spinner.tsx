import './Spinner.css'

interface Props {
  label?: string
}

export function Spinner({ label }: Props) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <svg className="spinner__wheel" viewBox="0 0 40 40" width="30" height="30">
        {Array.from({ length: 12 }, (_, i) => (
          <rect
            key={i}
            x="18.5"
            y="3"
            width="3"
            height="9"
            rx="1.5"
            transform={`rotate(${i * 30} 20 20)`}
            style={{ animationDelay: `${(i * 1) / 12}s` }}
          />
        ))}
      </svg>
      {label && <span className="spinner__label">{label}</span>}
    </div>
  )
}
