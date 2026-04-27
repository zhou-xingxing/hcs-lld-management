import request from './request'

export function fetchUsers(params) {
  return request.get('/users', { params })
}

export function createUser(data) {
  return request.post('/users', data)
}

export function updateUser(id, data) {
  return request.put(`/users/${id}`, data)
}

export function resetUserPassword(id, password) {
  return request.post(`/users/${id}/reset-password`, { password })
}

export function deleteUser(id) {
  return request.delete(`/users/${id}`)
}
