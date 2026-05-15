declare module 'django' {
  export function gettext(message: string): string
  export function pgettext(context: string, message: string): string
  export function ngettext(
    singular: string,
    plural: string,
    count: number
  ): string
  export function interpolate(fmt: string, obj: any, named?: boolean): string
}
