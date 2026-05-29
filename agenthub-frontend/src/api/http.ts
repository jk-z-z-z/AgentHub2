export type ApiResult<T> = { code: number; message: string; data: T }

function authHeaders() {
  const token = localStorage.getItem('token')
  return token ? ({ Authorization: `Bearer ${token}` } as Record<string, string>) : ({} as Record<string, string>)
}

function handleUnauthorized(status: number) {
  if (status === 401) {
    localStorage.removeItem('token')
  }
}

function buildUrl(path: string, query?: Record<string, string | number | boolean | undefined | null>) {
  const base = path.startsWith('http') ? path : path
  if (!query) return base
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null) continue
    params.set(k, String(v))
  }
  const qs = params.toString()
  return qs ? `${base}${base.includes('?') ? '&' : '?'}${qs}` : base
}

export async function httpGet<T>(
  url: string,
  query?: Record<string, string | number | boolean | undefined | null>,
): Promise<ApiResult<T>> {
  const request = await fetch(buildUrl(url, query), {
    headers: authHeaders(),
  })
  if (!request.ok) {
    handleUnauthorized(request.status)
    let detail = `HTTP ${request.status}`
    try {
      const payload = (await request.json()) as { detail?: string; message?: string }
      detail = payload.detail || payload.message || detail
    } catch {
      detail = `HTTP ${request.status}`
    }
    throw new Error(detail)
  }
  return (await request.json()) as ApiResult<T>
}

export async function httpPost<TResponse, TBody extends object>(
  url: string,
  body: TBody,
): Promise<ApiResult<TResponse>> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    handleUnauthorized(res.status)
    let detail = `HTTP ${res.status}`
    try {
      const payload = (await res.json()) as { detail?: string; message?: string }
      detail = payload.detail || payload.message || detail
    } catch {
      detail = `HTTP ${res.status}`
    }
    throw new Error(detail)
  }
  return (await res.json()) as ApiResult<TResponse>
}

export async function httpPut<TResponse, TBody>(
  url: string,
  body: TBody,
): Promise<ApiResult<TResponse>> {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'content-type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    handleUnauthorized(res.status)
    let detail = `HTTP ${res.status}`
    try {
      const payload = (await res.json()) as { detail?: string; message?: string }
      detail = payload.detail || payload.message || detail
    } catch {
      detail = `HTTP ${res.status}`
    }
    throw new Error(detail)
  }
  return (await res.json()) as ApiResult<TResponse>
}

export async function httpDelete<TResponse>(url: string): Promise<ApiResult<TResponse>> {
  const res = await fetch(url, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    handleUnauthorized(res.status)
    let detail = `HTTP ${res.status}`
    try {
      const payload = (await res.json()) as { detail?: string; message?: string }
      detail = payload.detail || payload.message || detail
    } catch {
      detail = `HTTP ${res.status}`
    }
    throw new Error(detail)
  }
  return (await res.json()) as ApiResult<TResponse>
}
