import { useNavigate } from 'react-router-dom'
import { Button } from '@gravity-ui/uikit'
import { newViewFromRootPath } from '../lib/customView'

/** Opens the view editor with `entityId` as a depth-1 Neighborhood root, rendered immediately. */
export function OpenInViewBuilder({ entityId }: { entityId: string }) {
  const navigate = useNavigate()
  return (
    <Button view="outlined" onClick={() => navigate(newViewFromRootPath(entityId))}>
      Open in view builder
    </Button>
  )
}
