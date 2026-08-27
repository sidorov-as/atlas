import { Link } from '@gravity-ui/uikit'
import { useNavigate } from 'react-router-dom'
import { kindToPath } from '../lib/entities'
import { refName, type Relation } from '../lib/types'

/**
 * Renders a relation's target as a link to its detail page when `targetKind` has a routable
 * kind, falling back to plain text otherwise (e.g. `user`, which has no
 * detail route). Shared by RelationsTab and Component's Provides/Consumes API sections.
 */
export function RelationTargetLink({ target, targetKind, targetId }: Pick<Relation, 'target' | 'targetKind' | 'targetId'>) {
  const navigate = useNavigate()
  const label = refName(target)
  const pathPrefix = kindToPath[targetKind]
  if (!pathPrefix) return <>{label}</>

  const to = `${pathPrefix}/${targetId}`
  return (
    <Link href={to} onClick={(event) => { event.preventDefault(); navigate(to) }}>
      {label}
    </Link>
  )
}
