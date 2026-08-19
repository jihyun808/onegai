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

/**
 * 가사 팝업. 열릴 때 한 번만 불러온다.
 *
 * 금영에 있는 곡은 한글 발음까지 나오고, 없는 곡(태진 전용이 특히 많다)은
 * 검색 링크로 넘긴다 — 태진은 어디에도 가사를 두지 않아서 다른 수가 없다.
 *
 * 권리 확인은 아직 진행 중이다 (DECISIONS.md 37번).
 */
export function LyricsModal({ title, singer, onClose }: Props) {
  const [data, setData] = useState<LyricsResponse | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    // 가사를 다 받기 전에 닫으면 setState가 헛돈다
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
            {/* 금영 조회가 2초쯤 걸린다. 멈춘 것처럼 보이지 않게 알려 준다 */}
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

      {/*
        기다리기 싫은 사람은 바로 검색으로 가면 된다.
        그래서 가사를 받기 전부터 띄워 둔다 — 주소는 제목만 있으면 만들 수 있다.
      */}
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

/** 서버 응답조차 못 받았을 때 쓸 링크. 주소만 조립하면 되니 클라이언트에서도 만든다. */
function searchFallback(title: string, singer: string) {
  const query = `"${title}" ${singer} 가사`.trim()
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`
}
