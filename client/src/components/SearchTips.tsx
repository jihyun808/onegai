import "./SearchTips.css";

/**
 * 검색어를 아직 안 넣었을 때 띄우는 안내.
 *
 * 세 줄만 남겼다. 실제로 결과가 갈리는 것만 골랐다 (2026-08-19 실측).
 *
 * | 검색 | 태진 | 금영 |
 * | --- | --- | --- |
 * | `요루니카케루`   | 1건 | 1건 |
 * | `요루니 카케루`  | **0건** | 1건 |
 * | `yoru ni kakeru` | 0건 | 0건 |
 * | `요아소비`(가수) | 31건 | 27건 |
 *
 * 띄어쓰기 하나로 결과가 사라지는 것이 가장 크고, 그다음이 '곡명 대신
 * 가수명'이다. 노래방 기기 검색이 원래 그렇게 동작한다.
 *
 * 3번은 외래어 제목 때문이다. 노래방에 실린 발음 표기가 일본어 읽기를
 * 그대로 옮긴 것이 아니라 **한국에서 쓰는 말**이다 —
 * `シルエット`는 `시루엣토`가 아니라 `실루엣`으로 찾아야 나온다.
 */
export function SearchTips() {
  return (
    <div className="tips">
      <p className="tips__title">이렇게 검색해 보세요</p>

      <ol className="tips__list">
        <li>
          <span className="tips__no">1</span>
          <span>
            <b>띄어쓰기 없이</b> 붙여서
            <em className="tips__eg">요루니카케루 ⭘ / 요루니 카케루 ✕</em>
          </span>
        </li>
        <li>
          <span className="tips__no">2</span>
          <span>
            곡명이 안 나오면 <b>가수명으로</b>
            <em className="tips__eg">긴 일본어 제목은 잘 안 걸려요</em>
          </span>
        </li>
        <li>
          <span className="tips__no">3</span>
          <span>
            <b>한국에서 쓰는 표기</b>로. 안 되면 일본어로
            <em className="tips__eg">실루엣 ⭘ / 시루엣토 ✕ · シルエット ⭘</em>
          </span>
        </li>
      </ol>
    </div>
  );
}
