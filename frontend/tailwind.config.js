import frappeUIPreset from 'frappe-ui/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // Semantic design-system tokens (see src/style.css for values). Existing
      // literal gray/emerald/amber/red/blue Tailwind classes elsewhere in the
      // app are left as-is — these are additive, for new/restyled shell and
      // status UI, not a replacement of every color in the codebase.
      // NOT named `ink` / `surface` — frappe-ui's own preset already
      // reserves those as nested color families (ink-gray-*, surface-*,
      // ...), and a flat string at the same top-level key collides with
      // that nested object so the bare utility silently drops (see the
      // long comment in src/style.css). `charcoal` / `paper` don't collide.
      colors: {
        canvas: 'rgb(var(--color-canvas) / <alpha-value>)',
        paper: 'rgb(var(--color-paper) / <alpha-value>)',
        line: 'rgb(var(--color-border) / <alpha-value>)',
        charcoal: 'rgb(var(--color-charcoal) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
          hover: 'rgb(var(--color-primary-hover) / <alpha-value>)',
        },
        success: 'rgb(var(--color-success) / <alpha-value>)',
        warning: 'rgb(var(--color-warning) / <alpha-value>)',
        danger: 'rgb(var(--color-danger) / <alpha-value>)',
        info: 'rgb(var(--color-info) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      // frappe-ui's own preset replaces Tailwind's default fontSize scale
      // with noticeably smaller values for its own dense admin-tool style
      // (text-base is 14px there, not 16px; text-sm is 13px; line-height
      // is a tight 1.15 throughout) — that's what was actually making
      // every text-sm/text-base element in this app read as "too small",
      // not a compiled-CSS bug. Overriding back to comfortable sizes for
      // a student-facing production app.
      fontSize: {
        xs: ['13px', { lineHeight: '1.45' }],
        sm: ['14.5px', { lineHeight: '1.5' }],
        base: ['16px', { lineHeight: '1.55' }],
        lg: ['18px', { lineHeight: '1.5' }],
        xl: ['20px', { lineHeight: '1.45' }],
        '2xl': ['24px', { lineHeight: '1.35' }],
        '3xl': ['30px', { lineHeight: '1.3' }],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 1px 0 rgb(15 23 42 / 0.03)',
      },
    },
  },
}
