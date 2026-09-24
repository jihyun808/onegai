import { useEffect, useState } from 'react'

import { fetchLyrics, type LyricsResponse } from '../utils/api'
import { Modal } from './Modal'
import { Spinner } from './Spinner'
import './LyricsModal.css'

interface Props {
  title: string
  singer: string
  onClose: () => void
}

export function LyricsModal({ title, singer, onClose }: Props) {
  const [data, setData] = useState<LyricsResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    fetchLyrics(title, singer, controller.signal)
      .then(setData)
      .catch((error) => {
        if (error.name !== 'AbortError') setFailed(true)
      })

    return () => controller.abort()
  }, [title, singer])

  return (
    <Modal title={title} onClose={onClose}>
      <p className="lyrics__singer">{singer || '가수 정보 없음'}</p>

      <div className="lyrics__body">
        {!data && !failed && (
          <div className="lyrics__loading">
            <Spinner />
            <p className="lyrics__note">가사를 찾는 중이에요</p>
          </div>
        )}

        {data?.available && (
          <ol className="lyrics__lines">
            {data.lines?.map((line, index) => (
              <li key={index} className="lyrics__line">
                <span className="lyrics__ko">{line.ko}</span>
                <span className="lyrics__ja">{line.ja}</span>
              </li>
            ))}
          </ol>
        )}

        {(failed || (data && !data.available)) && (
          <p className="lyrics__reason">
            {data?.reason ?? '가사를 가져오지 못했어요.'}
          </p>
        )}
      </div>

      <div className="lyrics__foot">
        <a
          className="lyrics__search"
          href={data?.search_url ?? searchFallback(title, singer)}
          target="_blank"
          rel="noopener noreferrer"
        >
          인터넷에서 찾아보기
        </a>
        {data?.available && <span className="lyrics__source">가사 · {data.provider}</span>}
      </div>
    </Modal>
  )
}

function searchFallback(title: string, singer: string) {
  const query = `"${title}" ${singer} 가사`.trim()
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`
}
