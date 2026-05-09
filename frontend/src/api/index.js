import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload/file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function startDiagnosis(params) {
  return api.post('/diagnosis/analyze', params)
}

export function generateSolution(params) {
  return api.post('/solution/generate', params)
}

export default api
