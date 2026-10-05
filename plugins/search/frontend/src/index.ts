// Search frontend plugin — supplies the single `globalSearch` shell contribution (search
// box + results dialog). Talks only to the search plugin's HTTP endpoints, so it works with
// any engine and imports no other plugin.
import { defineFrontendPlugin, globalSearch } from '@atlas/plugin-api'
import { SearchBox } from './components/SearchBox'

export const searchPlugin = defineFrontendPlugin({
  id: 'atlas.search',
  contributions: [globalSearch({ id: 'atlas.search.global', component: SearchBox })],
})
