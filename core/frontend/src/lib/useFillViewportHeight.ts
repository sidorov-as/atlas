import { useEffect, useRef, useState } from 'react'

/** Sizes a container to reach the bottom of the viewport instead of a fixed height — for a tab whose content is the page's only body, so it should fill the screen rather than sit in a small boxed area. Re-measures on mount, on resize, and whenever the container's own box changes size (including going from zero — e.g. an ancestor `display: none` tab panel that stays mounted while inactive, such as `EntityDetailShell`'s — to its real size), via `ResizeObserver`.
 *
 * Call this from a component that only mounts while its tab is active (not from the page component itself, which mounts once): the page usually renders just one tab's panel at a time, so a hook called from the page would measure once — while some other tab is still showing and this container doesn't exist yet — and never again. Mounting it inside a tab panel that stays mounted-but-hidden instead of unmounting is fine too: the `ResizeObserver` re-measures once that panel is shown and the container gets a real box. */
export function useFillViewportHeight(bottomPadding = 24) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState(600)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    function measure() {
      const top = containerRef.current?.getBoundingClientRect().top ?? 0
      setHeight(Math.max(360, window.innerHeight - top - bottomPadding))
    }
    // `getBoundingClientRect().top` is viewport-relative: if the page was left
    // scrolled down (e.g. a long list on the previously active tab kept the
    // scroll position when switching here), it reads as a too-small — even
    // negative — offset, and the computed height overshoots the viewport
    // enough that the page needs to scroll to reach the container's own
    // bottom edge. Reset to the top first so the measurement always reflects
    // this tab's own layout.
    window.scrollTo(0, 0)
    measure()
    window.addEventListener('resize', measure)

    let frame = 0
    const observer = window.ResizeObserver ? new window.ResizeObserver(() => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(measure)
    }) : null
    observer?.observe(container)

    return () => {
      window.removeEventListener('resize', measure)
      cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [bottomPadding])

  return { containerRef, height }
}
