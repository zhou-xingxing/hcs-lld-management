import request from './request'

export function lookupIP(q, exact = true) {
  return request.get('/lookup', { params: { q, exact } })
}
