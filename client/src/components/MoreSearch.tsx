import { webSearchUrl } from "../utils/links";
import "./MoreSearch.css";

interface Props {
  query: string;
  onLoadMore: () => void;
  canLoadMore: boolean;
}

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
