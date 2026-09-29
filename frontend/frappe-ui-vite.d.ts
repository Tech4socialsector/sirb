declare module 'frappe-ui/vite' {
  import type { PluginOption } from 'vite'

  interface FrappeUIViteOptions {
    frontendRoute?: string
    jinjaBootData?: boolean
    lucideIcons?: boolean
    frappeProxy?: boolean | Record<string, unknown>
    buildConfig?: boolean | Record<string, unknown>
    frappeTypes?: Record<string, unknown>
  }

  export default function frappeui(options?: FrappeUIViteOptions): PluginOption[]
}
