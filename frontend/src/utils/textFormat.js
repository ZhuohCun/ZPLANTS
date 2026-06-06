export function formatEnglishDays(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue) || numberValue <= 0) return ''
  const dayCount = Math.trunc(numberValue)
  return dayCount === 1 ? '1 day' : `${dayCount} days`
}
