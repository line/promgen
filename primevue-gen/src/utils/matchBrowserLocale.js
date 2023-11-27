/**
 * Find the first matching browser locale.
 *
 * Given a list of locales, it returns the one that best fits with the browser's preferred languages
 * for displaying pages.
 *
 * @param {Array<string>} locales - List of locales
 * @returns {string|undefined} Matching locale, otherwise undefined
 */
export function matchBrowserLocale(locales) {
  for (const language of navigator.languages) {
    for (const locale of locales) {
      if (RegExp(`^${locale}(-..)?$`).test(language)) {
        return locale;
      }
    }
  }

  return undefined;
}
