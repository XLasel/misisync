export function normalizeGroupSearch(value: string) {
  return value
    .normalize('NFKC')
    .trim()
    .toLocaleUpperCase('ru')
    .replace(/[–—−]/g, '-')
    .replace(/\s+/g, '')
}
