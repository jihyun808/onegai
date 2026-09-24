import './Logo.css'

export function Logo() {
  return (
    <div className="logo">
      <span className="logo__notes" aria-hidden="true">
        <svg viewBox="0 0 60 30" width="52" height="26">
          <g className="logo__note logo__note--1">
            <path d="M8 21V9l7-2v12" />
            <ellipse cx="5.4" cy="21.4" rx="3.4" ry="2.8" />
            <ellipse cx="12.4" cy="19.4" rx="3.4" ry="2.8" />
          </g>
          <g className="logo__note logo__note--2">
            <path d="M28 18V4l10-2.6V16" />
            <ellipse cx="24.8" cy="18.6" rx="4" ry="3.3" />
            <ellipse cx="34.8" cy="16.6" rx="4" ry="3.3" />
          </g>
          <g className="logo__note logo__note--3">
            <path d="M50 22V12l6-1.6v9" />
            <ellipse cx="47.6" cy="22.4" rx="3.1" ry="2.6" />
            <ellipse cx="53.6" cy="19.4" rx="3.1" ry="2.6" />
          </g>
        </svg>
      </span>

      <h1 className="logo__text">
        <span className="logo__ink">오네</span>
        <span className="logo__accent">가이</span>
      </h1>
    </div>
  )
}
