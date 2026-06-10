import { httpPost, type ApiResult } from './http'
import type { User } from './models'

export type LoginResponse = {
  access_token: string
  user: User
}

export async function apiLogin(body: { email: string; password: string }): Promise<ApiResult<LoginResponse>> {
  return httpPost<LoginResponse, typeof body>('/api/v1/auth/login', body)
}

export async function apiRegister(body: {
  email: string
  username: string
  display_name?: string | null
  password: string
  bio?: string
}): Promise<ApiResult<LoginResponse>> {
  return httpPost<LoginResponse, typeof body>('/api/v1/auth/register', body)
}
