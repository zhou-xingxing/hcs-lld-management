import request from './request'

export function downloadTemplate() {
  return request.get('/excel/template', { responseType: 'blob' })
}

export function previewImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/excel/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export function confirmImport(previewId, operator) {
  return request.post('/excel/import/confirm', { preview_id: previewId, operator })
}

export function exportExcel(params) {
  return request.get('/excel/export', { params, responseType: 'blob' })
}

export function fetchStats() {
  return request.get('/stats')
}

export function fetchChangeLogs(params) {
  return request.get('/change-logs', { params })
}
