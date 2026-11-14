import { FooterItem } from '@gravity-ui/navigation'
import { Display, Moon, Sun } from '@gravity-ui/icons'
import { Icon, SegmentedRadioGroup, type IconData } from '@gravity-ui/uikit'
import { useTheme, type ThemeMode } from '../lib/ThemeContext'

const MODES: readonly { value: ThemeMode; title: string; icon: IconData }[] = [
  { value: 'light', title: 'Light', icon: Sun },
  { value: 'dark', title: 'Dark', icon: Moon },
  { value: 'system', title: 'System', icon: Display },
]

const CYCLE: readonly ThemeMode[] = ['system', 'light', 'dark']

/** Footer theme control: all three modes when the shell is expanded, one cycling icon when compact. */
export function ThemeSwitcher({ compact }: { compact: boolean }) {
  const { mode, setMode } = useTheme()

  if (compact) {
    const active = MODES.find((item) => item.value === mode) ?? MODES[2]
    const next = CYCLE[(CYCLE.indexOf(mode) + 1) % CYCLE.length]
    return (
      <FooterItem
        id="theme"
        title={`Theme: ${active.title}`}
        icon={active.icon}
        onItemClick={() => setMode(next)}
      />
    )
  }

  return (
    <div style={{ padding: '6px 12px' }}>
      <SegmentedRadioGroup<ThemeMode>
        className="theme-switcher"
        size="m"
        width="max"
        value={mode}
        onUpdate={setMode}
        aria-label="Theme"
      >
        {MODES.map((item) => (
          // A lone <Icon> as `content` gets the option's icon layout (vertically centered); the
          // accessible name goes on the radio input.
          <SegmentedRadioGroup.Option
            key={item.value}
            value={item.value}
            title={item.title}
            controlProps={{ 'aria-label': item.title }}
            content={<Icon data={item.icon} size={16} />}
          />
        ))}
      </SegmentedRadioGroup>
    </div>
  )
}
