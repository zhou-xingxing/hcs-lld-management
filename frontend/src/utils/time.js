export const APP_TIME_ZONE = 'Asia/Shanghai'

export function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    timeZone: APP_TIME_ZONE,
    hour12: false,
  })
}
