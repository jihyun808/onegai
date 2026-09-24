import './StateMessage.css'

interface Props {
  title: string
  description?: string
}

export function StateMessage({ title, description }: Props) {
  return (
    <div className="state">
      <p className="state__title">{title}</p>
      {description && <p className="state__desc">{description}</p>}
    </div>
  )
}
