// Import-boundary check, generalized to every first-party frontend plugin, plus a plugin -> plugin check.
//
// Structural enforcement already comes from `frontend/package.json`'s `exports` map —
// anything outside its declared subpaths (like `frontend/plugins/core/*`) simply fails to
// resolve for a plugin package — this test covers the directions that map can't:
// core code reaching into a plugin package, and one plugin package reaching into another's
// implementation (`@atlas/plugin-api` and its own package are the only allowed cross-package
// imports for a plugin).
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const THIS_FILE = join(import.meta.dirname, 'importBoundary.test.ts')
const FRONTEND_SRC = join(import.meta.dirname, '..')
const COMPOSITION_FILE = join(FRONTEND_SRC, 'plugins', 'composition.ts')
const PLUGINS_ROOT = join(FRONTEND_SRC, '..', '..', '..', 'plugins')

// Matches an actual import/re-export specifier, not prose in a comment mentioning the
// package name (several core files' comments explain what moved where).
const CORE_INTERNALS_IMPORT_PATTERN = /from\s+['"]frontend\/plugins\/core/

// Every first-party plugin with a frontend package, keyed by its `@atlas/plugin-*` name.
// c4/database-schema/apis/standard-catalog all publish `@atlas/plugin-<name>`; `ingestion`
// has no frontend package (backend-only), so it's absent here.
const FRONTEND_PLUGINS = readdirSync(PLUGINS_ROOT)
  .filter((name) => existsSync(join(PLUGINS_ROOT, name, 'frontend', 'src')))
  .map((name) => ({
    packageName: `@atlas/plugin-${name}`,
    src: join(PLUGINS_ROOT, name, 'frontend', 'src'),
  }))

function collectFiles(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    if (statSync(fullPath).isDirectory()) {
      collectFiles(fullPath, files)
    } else if (/\.(ts|tsx)$/.test(entry)) {
      files.push(fullPath)
    }
  }
  return files
}

function importPattern(packageName: string): RegExp {
  return new RegExp(`from\\s+['"]${packageName.replace('/', '\\/')}['"]`)
}

describe.each(FRONTEND_PLUGINS)('frontend/core -> $packageName import boundary', ({ packageName }) => {
  const pattern = importPattern(packageName)

  it('is only imported from plugins/composition.ts, the single composition point', () => {
    const offenders = collectFiles(FRONTEND_SRC)
      .filter((file) => file !== COMPOSITION_FILE && file !== THIS_FILE)
      .filter((file) => pattern.test(readFileSync(file, 'utf-8')))
      .map((file) => relative(FRONTEND_SRC, file))

    expect(offenders).toEqual([])
  })
})

describe.each(FRONTEND_PLUGINS)('$packageName -> frontend/plugins/core import boundary', ({ src }) => {
  it('never reaches into the "core" plugin module\'s internals', () => {
    const offenders = collectFiles(src)
      .filter((file) => CORE_INTERNALS_IMPORT_PATTERN.test(readFileSync(file, 'utf-8')))
      .map((file) => relative(src, file))

    expect(offenders).toEqual([])
  })
})

describe.each(FRONTEND_PLUGINS)('$packageName -> another plugin import boundary', ({ packageName, src }) => {
  const otherPlugins = FRONTEND_PLUGINS.filter((other) => other.packageName !== packageName)

  it('never imports another plugin\'s package directly (only @atlas/plugin-api is a shared cross-plugin dependency)', () => {
    const files = collectFiles(src)
    const offenders = otherPlugins.flatMap(({ packageName: otherPackageName }) => {
      const pattern = importPattern(otherPackageName)
      return files
        .filter((file) => pattern.test(readFileSync(file, 'utf-8')))
        .map((file) => `${relative(src, file)} -> ${otherPackageName}`)
    })

    expect(offenders).toEqual([])
  })
})
