import { describe, expect, it } from 'vitest'
import { detectSpecLanguage, parseSpecContent } from './specFormat'

describe('detectSpecLanguage', () => {
  it('detects JSON content starting with {', () => {
    expect(detectSpecLanguage('{"openapi": "3.0.0"}')).toBe('json')
  })

  it('detects JSON content starting with [', () => {
    expect(detectSpecLanguage('[1, 2, 3]')).toBe('json')
  })

  it('detects leading whitespace before a JSON opener', () => {
    expect(detectSpecLanguage('  \n{"openapi": "3.0.0"}')).toBe('json')
  })

  it('defaults to YAML for non-JSON-looking content', () => {
    expect(detectSpecLanguage('openapi: 3.0.0')).toBe('yaml')
  })

  it('defaults to YAML for empty content', () => {
    expect(detectSpecLanguage('')).toBe('yaml')
  })
})

describe('parseSpecContent', () => {
  it('returns null for valid YAML', () => {
    expect(parseSpecContent('openapi: 3.0.0')).toBeNull()
  })

  it('returns null for valid JSON', () => {
    expect(parseSpecContent('{"openapi": "3.0.0"}')).toBeNull()
  })

  it('returns an error message for invalid content', () => {
    expect(parseSpecContent('{ broken')).toMatch(/unexpected end of the stream/)
  })

  it('parses deeply-aliased/merge-key YAML without exhausting CPU (GHSA-2883-xcg3-v3hh)', () => {
    // PoC shape from the js-yaml advisory: merging a large anchored sequence
    // of empty mappings into many targets is O(N*K) work that a vulnerable
    // js-yaml's maxTotalMergeKeys guard failed to bound (~13s at N=K=20000
    // pre-fix; the fixed loader handles this in well under a second).
    const n = 20000
    const arr = `arr: &arr\n${Array.from({ length: n }, () => '  - {}').join('\n')}\n`
    const targets = `targets:\n${Array.from({ length: n }, () => '  - <<: *arr').join('\n')}\n`
    const content = arr + targets

    const start = performance.now()
    const error = parseSpecContent(content)
    const elapsed = performance.now() - start

    expect(error).toBeNull()
    expect(elapsed).toBeLessThan(2000)
  })
})
