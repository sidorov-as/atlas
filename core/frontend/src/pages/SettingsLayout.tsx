import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Menu, Text } from '@gravity-ui/uikit'
import { SettingsHomePage } from './SettingsHomePage'
import { SettingsTagsPage } from './SettingsTagsPage'

const SETTINGS_SECTIONS = [
  { to: '/settings/home', label: 'Home' },
  { to: '/settings/tags', label: 'Tag colors' },
]

/**
 * Nested Settings area (admin-settings-area spec): a persistent left
 * sub-navigation plus an internal `<Routes>` for each section, so
 * `/settings/tags` (say) renders the Tag colors section directly rather than
 * through a different Settings page first. `/settings` redirects to
 * `/settings/home`. Reached only once `AdminProtected` (`App.tsx`) has
 * already confirmed the current user is a superuser.
 */
export function SettingsLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <div style={{ display: 'flex', gap: 32 }}>
      <div style={{ minWidth: 200 }}>
        <Text variant="header-1">Settings</Text>
        <Menu size="l" style={{ marginTop: 16 }}>
          {SETTINGS_SECTIONS.map((section) => (
            <Menu.Item
              key={section.to}
              active={location.pathname === section.to}
              onClick={() => navigate(section.to)}
            >
              {section.label}
            </Menu.Item>
          ))}
        </Menu>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Routes>
          <Route index element={<Navigate to="home" replace />} />
          <Route path="home" element={<SettingsHomePage />} />
          <Route path="tags" element={<SettingsTagsPage />} />
        </Routes>
      </div>
    </div>
  )
}
