// @vitest-environment jsdom
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import DocumentationPreviewView from './DocumentationPreviewView'

describe('DocumentationPreview hostile-input regressions', () => {
  it('renders a linkify ReDoS payload (mailto: scan-loop) without pathological slowdown', () => {
    // PoC from GHSA-v245-v573-v5vm: contiguous "mailto:" repetitions triggered
    // quadratic-complexity scanning in linkify-it's mailto validator.
    const value = 'mailto:'.repeat(48000)

    const start = performance.now()
    render(<DocumentationPreviewView value={value} />)
    const elapsed = performance.now() - start

    expect(elapsed).toBeLessThan(2000)
  })

  it('renders an email-like ReDoS payload (fuzzy email scan-loop) without pathological slowdown', () => {
    // PoC from GHSA-22p9-wv53-3rq4: repeated email-like substrings triggered
    // O(n^2) behavior in linkify-it's match() re-slicing.
    const value = 'a@b.com '.repeat(20000)

    const start = performance.now()
    render(<DocumentationPreviewView value={value} />)
    const elapsed = performance.now() - start

    expect(elapsed).toBeLessThan(2000)
  })

  it('never turns SVG-embedded script content into live, executable DOM', () => {
    const value = [
      '<svg xmlns="http://www.w3.org/2000/svg"><script>window.__pwned_script=true</script></svg>',
      '',
      // Namespace-prefixed anchor + control-character-obfuscated javascript: URI
      // (GHSA-w27v-7q3p-w38r): svgo's removeScripts missed `<svg:a>` and
      // schemes containing embedded tabs/newlines like `java\tscript:`.
      '<svg xmlns:svg="http://www.w3.org/2000/svg"><svg:a xlink:href="java&#9;script:window.__pwned_ns=true"><text>click</text></svg:a></svg>',
      '',
      // Executable HTML inside foreignObject (GHSA-4vpr-x523-8j87,
      // GHSA-2p49-hgcm-8545): an iframe srcdoc smuggling a script.
      '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><iframe srcdoc="&lt;script&gt;window.__pwned_fo=true&lt;/script&gt;"></iframe></body></foreignObject></svg>',
    ].join('\n')

    const { container } = render(<DocumentationPreviewView value={value} />)

    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('iframe')).toBeNull()
    expect(container.querySelector('svg\\:a, a[xlink\\:href], a[href^="java"]')).toBeNull()
    expect((window as unknown as Record<string, unknown>).__pwned_script).toBeUndefined()
    expect((window as unknown as Record<string, unknown>).__pwned_ns).toBeUndefined()
    expect((window as unknown as Record<string, unknown>).__pwned_fo).toBeUndefined()
  })
})
