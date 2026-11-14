import { useReactFlow } from '@xyflow/react'
import { MagnifierMinus, MagnifierPlus, SquareDashed } from '@gravity-ui/icons'
import { Button, Icon, Tooltip } from '@gravity-ui/uikit'

/** Zoom / fit buttons in the same Gravity style as the Flows, ER and C4 canvases (`.flow-graph__zoom`, core `index.css`). */
export function GraphZoomToolbar() {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  return (
    <div className="flow-graph__zoom">
      <Tooltip content="Zoom in" placement="right">
        <Button view="raised" aria-label="Zoom in" onClick={() => void zoomIn()}>
          <Icon data={MagnifierPlus} />
        </Button>
      </Tooltip>
      <Tooltip content="Fit to viewport" placement="right">
        <Button view="raised" aria-label="Fit to viewport" onClick={() => void fitView({ duration: 200, padding: 0.2 })}>
          <Icon data={SquareDashed} />
        </Button>
      </Tooltip>
      <Tooltip content="Zoom out" placement="right">
        <Button view="raised" aria-label="Zoom out" onClick={() => void zoomOut()}>
          <Icon data={MagnifierMinus} />
        </Button>
      </Tooltip>
    </div>
  )
}
