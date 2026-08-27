// Per-entity-kind rail field lists, shared by each detail page's rail and the
// list-page preview panel so the two never disagree on what "the summary" is.
import { Label } from '@gravity-ui/uikit'
import type { RailField } from '../components/EntityDetailShell'
import { RelationTargetLink } from '../components/RelationTargetLink'
import type { ApiEntity, ComponentEntity, FlowEntity, GroupEntity, ResourceEntity, SystemEntity } from './types'
import { refName } from './types'

export function systemRailFields(system: SystemEntity): RailField[] {
  return [
    {
      label: 'Owner',
      value: (
        <Label>
          <RelationTargetLink target={system.spec.owner} targetKind="group" targetId={system.spec.ownerId} />
        </Label>
      ),
    },
  ]
}

export function componentRailFields(component: ComponentEntity): RailField[] {
  return [
    { label: 'Type', value: <Label>{component.spec.type}</Label> },
    { label: 'Lifecycle', value: <Label>{component.spec.lifecycle}</Label> },
    {
      label: 'Owner',
      value: (
        <Label>
          <RelationTargetLink target={component.spec.owner} targetKind="group" targetId={component.spec.ownerId} />
        </Label>
      ),
    },
    {
      label: 'System',
      value: (
        <Label>
          <RelationTargetLink target={component.spec.system} targetKind="system" targetId={component.spec.systemId!} />
        </Label>
      ),
    },
  ]
}

export function resourceRailFields(resource: ResourceEntity): RailField[] {
  return [
    { label: 'Type', value: <Label>{resource.spec.type}</Label> },
    {
      label: 'Owner',
      value: (
        <Label>
          <RelationTargetLink target={resource.spec.owner} targetKind="group" targetId={resource.spec.ownerId} />
        </Label>
      ),
    },
    {
      label: 'System',
      value: (
        <Label>
          {resource.spec.system && resource.spec.systemId != null ? (
            <RelationTargetLink target={resource.spec.system} targetKind="system" targetId={resource.spec.systemId} />
          ) : (
            '—'
          )}
        </Label>
      ),
    },
  ]
}

export function apiRailFields(api: ApiEntity): RailField[] {
  return [
    { label: 'Type', value: <Label>{api.spec.type}</Label> },
    {
      label: 'Owner',
      value: (
        <Label>
          <RelationTargetLink target={api.spec.owner} targetKind="group" targetId={api.spec.ownerId} />
        </Label>
      ),
    },
    {
      label: 'System',
      value: (
        <Label>
          <RelationTargetLink target={api.spec.system} targetKind="system" targetId={api.spec.systemId!} />
        </Label>
      ),
    },
  ]
}

export function flowRailFields(flow: FlowEntity): RailField[] {
  return [
    { label: 'System', value: <Label>{refName(flow.system)}</Label> },
    { label: 'Steps', value: String(flow.steps.length) },
  ]
}

export function teamRailFields(group: GroupEntity): RailField[] {
  return [
    { label: 'Type', value: <Label>{group.spec.type}</Label> },
    { label: 'Members', value: String(group.spec.members.length) },
  ]
}
