import "./SearchTips.css";

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
