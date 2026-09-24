import './StateMessage.css'

interface Props {
  title: string
  description?: string
}

/** 초기 화면, 결과 없음, 오류를 같은 형태로 보여준다. */
export function StateMessage({ title, description }: Props) {
  return (
    <div className="state">
      <p className="state__title">{title}</p>
      {description && <p className="state__desc">{description}</p>}
    </div>
  )
}
