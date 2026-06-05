import { httpPost, type ApiResult } from './http'

export type LoginResponse = {
  access_token: string
}

export async function apiLogin(body: { email: string; password: string }): Promise<ApiResult<LoginResponse>> {
  return httpPost<LoginResponse, typeof body>('/api/v1/auth/login', body)
}
