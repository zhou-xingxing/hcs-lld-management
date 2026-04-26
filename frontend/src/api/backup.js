import request from './request'

export function fetchBackupConfig() {
  return request.get('/backup/config')
}

export function updateBackupConfig(data) {
  return request.put('/backup/config', data)
}

export function runBackup() {
  return request.post('/backup/run')
}

export function fetchBackupRecords(params) {
  return request.get('/backup/records', { params })
}
