import { webSearchUrl } from "../utils/links";
import "./MoreSearch.css";

interface Props {
  /** 지금 검색어. 브라우저 검색 링크를 만드는 데 쓴다 */
  query: string;
  /** 노래방 공식 사이트까지 다시 조회 */
  onLoadMore: () => void;
  /** 공식 조회가 이미 진행 중이면 버튼을 감춘다 */
  canLoadMore: boolean;
}

/**
 * 결과 끝과 '결과 없음' 아래에 함께 두는 마무리 영역.
 *
 * 두 갈래를 준다.
 *   1. 노래방 공식까지 **우리가** 다시 조회 (자체 DB는 크롤 시점까지만 담는다)
 *   2. 그래도 없으면 **브라우저로** 나가기
 *
 * 2번은 가사보기의 '인터넷에서 찾아보기'와 같은 원리다 — 우리가 못 찾는
 * 것을 붙잡고 있지 말고 찾아갈 곳을 알려 준다. 주소는 검색어만 있으면
 * 만들 수 있어서 서버를 기다리지 않는다.
 */
export function MoreSearch({ query, onLoadMore, canLoadMore }: Props) {
  return (
    <div className="more">
      {canLoadMore && (
        <button type="button" className="home__more" onClick={onLoadMore}>
          찾는 곡이 없나요? 공식 사이트에서 결과 더 불러오기
        </button>
      )}

      <a
        className="more__web"
        href={webSearchUrl(query)}
        target="_blank"
        rel="noopener noreferrer"
      >
        브라우저에서 검색하기
      </a>
    </div>
  );
}
