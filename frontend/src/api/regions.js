import request from './request'

export function fetchRegions(params) {
  return request.get('/regions', { params })
}

export function getRegion(id) {
  return request.get(`/regions/${id}`)
}

export function createRegion(data) {
  return request.post('/regions', data)
}

export function updateRegion(id, data) {
  return request.put(`/regions/${id}`, data)
}

export function deleteRegion(id) {
  return request.delete(`/regions/${id}`)
}

export function fetchRegionPlanes(regionId) {
  return request.get(`/regions/${regionId}/planes`)
}

export function enableRegionPlane(regionId, planeTypeId, cidr) {
  return request.post(`/regions/${regionId}/planes`, { plane_type_id: planeTypeId, cidr })
}

export function disableRegionPlane(regionId, planeId) {
  return request.delete(`/regions/${regionId}/planes/${planeId}`)
}

export function fetchRegionAllocations(regionId, params) {
  return request.get(`/regions/${regionId}/allocations`, { params })
}

export function createAllocation(regionId, data) {
  return request.post(`/regions/${regionId}/allocations`, data)
}

export function updateAllocation(id, data) {
  return request.put(`/allocations/${id}`, data)
}

export function deleteAllocation(id) {
  return request.delete(`/allocations/${id}`)
}
