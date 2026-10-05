import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dialog, Label, Tab, TabList, TabProvider, Text, TextInput } from '@gravity-ui/uikit'
import { useDebouncedValue } from 'frontend/lib/useDebouncedValue'
import { HighlightedText } from './HighlightedText'
import { SearchUnavailableError, searchApi, type KindCount, type SearchResult } from '../lib/api'

export const SEARCH_DEBOUNCE_MS = 200
/** Fixed so the dialog keeps one size while results come and go; a centered dialog that resizes visibly jumps. */
const RESULTS_HEIGHT = 360
/** Tab value of the "no kind filter" tab; real kinds are never called this. */
const ALL_KINDS = 'all'
/** Status older than this many seconds of unindexed backlog triggers the stale-index notice. */
const STALE_AFTER_SECONDS = 120

type State =
  | { phase: 'idle' }
  /** `results` keeps the previous answer on screen while the next one loads, so the list does not collapse and regrow. */
  | { phase: 'loading'; results: SearchResult[] }
  | { phase: 'done'; results: SearchResult[] }
  | { phase: 'unavailable' }
  | { phase: 'error' }

export function SearchDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const titleId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [state, setState] = useState<State>({ phase: 'idle' })
  const [active, setActive] = useState(0)
  const [stale, setStale] = useState(false)
  const [kind, setKind] = useState(ALL_KINDS)
  const [kindLabel, setKindLabel] = useState('')
  const [facets, setFacets] = useState<KindCount[]>([])
  const debounced = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    if (!open) return
    const controller = new AbortController()
    searchApi
      .status(controller.signal)
      .then((status) => setStale((status.oldestPendingAgeSeconds ?? 0) > STALE_AFTER_SECONDS))
      .catch(() => setStale(false))
    return () => controller.abort()
  }, [open])

  useEffect(() => {
    if (!open) return
    if (debounced === '') {
      setState({ phase: 'idle' })
      setFacets([])
      return
    }
    const controller = new AbortController()
    setState((previous) => ({
      phase: 'loading',
      results: previous.phase === 'done' || previous.phase === 'loading' ? previous.results : [],
    }))
    searchApi
      .search(debounced, { kind: kind === ALL_KINDS ? null : kind, signal: controller.signal })
      .then((response) => {
        setActive(0)
        setFacets(response.facets ?? [])
        setState({ phase: 'done', results: response.results })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        setState({ phase: err instanceof SearchUnavailableError ? 'unavailable' : 'error' })
      })
    return () => controller.abort()
  }, [debounced, open, kind])

  function close() {
    setQuery('')
    setKind(ALL_KINDS)
    setKindLabel('')
    setFacets([])
    setState({ phase: 'idle' })
    setActive(0)
    onClose()
  }

  function openResult(result: SearchResult) {
    close()
    navigate(result.link)
  }

  const results = state.phase === 'done' || state.phase === 'loading' ? state.results : []
  const loading = state.phase === 'loading'
  const total = facets.reduce((sum, facet) => sum + facet.count, 0)
  // A kind selected earlier stays selectable (as 0) when a new query has no match in it.
  const tabs =
    kind === ALL_KINDS || facets.some((facet) => facet.kind === kind)
      ? facets
      : [...facets, { kind, kindLabel: kindLabel || kind, count: 0 }]
  const optionId = (index: number) => `${titleId}-option-${index}`

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown' && results.length > 0) {
      event.preventDefault()
      setActive((index) => (index + 1) % results.length)
    } else if (event.key === 'ArrowUp' && results.length > 0) {
      event.preventDefault()
      setActive((index) => (index - 1 + results.length) % results.length)
    } else if (event.key === 'Enter' && !loading && results[active]) {
      event.preventDefault()
      openResult(results[active])
    }
    // Escape is handled by the Dialog itself (`onClose`).
  }

  return (
    <Dialog open={open} onClose={close} onTransitionIn={() => inputRef.current?.focus()} aria-labelledby={titleId} maxWidth="m" fullWidth disableHeightTransition>
      <Dialog.Header caption="Search" id={titleId} />
      <Dialog.Body>
        <div onKeyDown={onKeyDown}>
          <TextInput
            controlRef={inputRef}
            autoFocus
            size="l"
            placeholder="Search the catalog…"
            value={query}
            onUpdate={setQuery}
            controlProps={{
              'aria-label': 'Search query',
              role: 'combobox',
              'aria-expanded': results.length > 0,
              'aria-controls': `${titleId}-results`,
              'aria-activedescendant': results[active] ? optionId(active) : undefined,
            }}
          />
          <TabProvider
            value={kind}
            onUpdate={(value) => {
              setKind(value)
              setKindLabel(tabs.find((tab) => tab.kind === value)?.kindLabel ?? '')
              inputRef.current?.focus()
            }}
          >
            <TabList size="m" contentOverflow="scroll" style={{ marginTop: 8 }} aria-label="Filter by type">
              <Tab value={ALL_KINDS} counter={facets.length > 0 ? total : undefined}>
                All
              </Tab>
              {tabs.map((facet) => (
                <Tab key={facet.kind} value={facet.kind} counter={facet.count}>
                  {facet.kindLabel}
                </Tab>
              ))}
            </TabList>
          </TabProvider>
          {stale && (
            <div role="status" style={{ marginTop: 8 }}>
              <Text color="warning">The search index is behind; recent changes may not appear yet.</Text>
            </div>
          )}
          <div id={`${titleId}-results`} role="listbox" style={{ marginTop: 12, height: RESULTS_HEIGHT, overflowY: 'auto' }}>
            {loading && results.length === 0 && <Text color="secondary">Searching…</Text>}
            {state.phase === 'unavailable' && <Text color="danger">Search is currently unavailable. Try again later.</Text>}
            {state.phase === 'error' && <Text color="danger">Search failed. Try again.</Text>}
            {state.phase === 'done' && results.length === 0 && <Text color="secondary">No results found.</Text>}
            {results.map((result, index) => (
              <div
                key={result.id}
                id={optionId(index)}
                role="option"
                aria-selected={index === active}
                onMouseEnter={() => setActive(index)}
                onClick={() => openResult(result)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  borderRadius: 6,
                  opacity: loading ? 0.6 : undefined,
                  background: index === active ? 'var(--g-color-base-simple-hover)' : undefined,
                }}
              >
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Label size="xs">{result.kindLabel}</Label>
                  <Text variant="subheader-2">{result.title}</Text>
                </div>
                {result.snippet && (
                  <div style={{ marginTop: 4 }}>
                    <Text color="secondary" variant="body-1">
                      <HighlightedText snippet={result.snippet} />
                    </Text>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </Dialog.Body>
    </Dialog>
  )
}
