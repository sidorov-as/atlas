import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@gravity-ui/uikit/styles/styles.css'
import './theme.css'
import './tag-palette.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
