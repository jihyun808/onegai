import { useEffect, useRef } from 'react'

import './Modal.css'

interface Props {
  title: string
  onClose: () => void
  children: React.ReactNode
}

/** 손그림 톤의 둥근 팝업. 배경을 누르거나 Esc로 닫는다. */
export function Modal({ title, onClose, children }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)

    // 팝업 뒤 목록이 같이 스크롤되지 않게 막는다
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'

    // 열리면 팝업 안으로 초점을 옮긴다
    panelRef.current?.focus()

    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
    }
  }, [onClose])

  return (
    <div className="modal" onClick={onClose}>
      <div
        className="modal__panel sketch"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panelRef}
        // 패널 안을 눌렀을 때 배경 클릭으로 취급되지 않게 한다
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal__head">
          <h2 className="modal__title">{title}</h2>
          <button className="modal__close" type="button" onClick={onClose} aria-label="닫기">
            <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
              <path
                d="M2 2l8 8M10 2l-8 8"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
