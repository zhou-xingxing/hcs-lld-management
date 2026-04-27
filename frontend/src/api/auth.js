import request from './request'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function fetchCurrentUser() {
  return request.get('/auth/me')
}
