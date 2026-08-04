import './SearchInput.css'

interface Props {
  value: string
  onChange: (value: string) => void
  busy?: boolean
}

export function SearchInput({ value, onChange, busy }: Props) {
  return (
    <div className="search sketch">
      <input
        className="search__input"
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="곡명 또는 가수명으로 검색"
        aria-label="곡명 또는 가수명으로 검색"
        autoComplete="off"
        // 일본어 입력을 자주 쓰므로 자동 대문자/교정은 끈다
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        maxLength={100}
      />

      {value && (
        <button
          className="search__clear"
          type="button"
          onClick={() => onChange('')}
          aria-label="검색어 지우기"
        >
          <svg viewBox="0 0 10 10" width="9" height="9" aria-hidden="true">
            <path
              d="M1.5 1.5 8.5 8.5M8.5 1.5 1.5 8.5"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </button>
      )}

      {busy ? (
        <span className="search__spinner" aria-hidden="true" />
      ) : (
        <svg
          className="search__icon"
          viewBox="0 0 18 18"
          width="17"
          height="17"
          aria-hidden="true"
        >
          <circle
            cx="7.5"
            cy="7.5"
            r="5.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
          />
          <path
            d="M11.6 11.6 16 16"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
        </svg>
      )}
    </div>
  )
}
