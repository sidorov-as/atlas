import { Alert } from '@gravity-ui/uikit'

import type { ConflictReason } from '../lib/types'

/**
 * Shown on an entity's detail page when it's currently blocking a rival YAML
 * or manual claim. Warning-styled and
 * message-distinct from `ReadOnlyBanner`: that one is informational ("this
 * entity is YAML-managed"), this one names an action the viewer can take.
 *
 * `removed_entity` gets its own message: adopting doesn't apply to a
 * `removed` entity the way it does to an active one — the actual unblocking
 * action is Revive (to reclaim the name) or Purge (to free it for the rival).
 */
export function ConflictBanner({
  blockedBy,
  reason,
}: {
  blockedBy: string
  reason?: ConflictReason | null
}) {
  const message =
    reason === 'removed_entity'
      ? `blocking a claim from \`${blockedBy}\` — this entity is removed; an owner must revive or purge it before that claim can succeed`
      : `blocking a claim from \`${blockedBy}\` — a member of this entity's owner Group can adopt it to resolve the conflict`
  return <Alert theme="warning" message={message} />
}
