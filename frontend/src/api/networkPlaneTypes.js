import request from './request'

export function fetchPlaneTypes(params) {
  return request.get('/network-plane-types', { params })
}

export function getPlaneType(id) {
  return request.get(`/network-plane-types/${id}`)
}

export function createPlaneType(data) {
  return request.post('/network-plane-types', data)
}

export function updatePlaneType(id, data) {
  return request.put(`/network-plane-types/${id}`, data)
}

export function deletePlaneType(id) {
  return request.delete(`/network-plane-types/${id}`)
}
