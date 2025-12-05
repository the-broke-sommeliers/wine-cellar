declare function gettext(msgid: string): string;
declare function ngettext(singular: string, plural: string, count: number): string;
declare function gettext_noop(msgid: string): string;
declare function pgettext(context: string, msgid: string): string;
declare function npgettext(
    context: string,
    singular: string,
    plural: string,
    count: number
): string;
