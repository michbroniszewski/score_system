// Reads API v1. The Pages build (VITE_STATIC_DATA=true) reads the static snapshot that
// `make export` writes, where every response is a file at the same path plus ".json";
// otherwise the live API is used (proxied by the Vite dev server, see vite.config.ts).
export const staticData = import.meta.env.VITE_STATIC_DATA === 'true'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly url: string,
    readonly detail: string | null = null,
  ) {
    super(detail ?? `${url} answered ${status}`)
  }
}

export function apiUrl(path: string, isStatic = staticData): string {
  return isStatic ? `${import.meta.env.BASE_URL}api/v1/${path}.json` : `/api/v1/${path}`
}

export async function getJson<T>(path: string): Promise<T> {
  const url = apiUrl(path)
  const response = await fetch(url)
  if (!response.ok) {
    throw new ApiError(response.status, url)
  }
  return (await response.json()) as T
}

// Changes data through the live API (the local admin panel only).
export async function send<T>(
  method: 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<T> {
  const url = apiUrl(path, false)
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    throw new ApiError(response.status, url, await errorDetail(response))
  }
  return (response.status === 204 ? null : await response.json()) as T
}

// The API answers errors with {"detail": "..."}, or a list of field errors for invalid input.
async function errorDetail(response: Response): Promise<string | null> {
  try {
    const { detail } = (await response.json()) as {
      detail?: string | { loc?: (string | number)[]; msg: string }[]
    }
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // loc is e.g. ["body", "sets", 0, "home"]; an error on the whole body has no field.
      return detail
        .map((e) => {
          const field = (e.loc ?? []).slice(1).join('.')
          return field ? `${field}: ${e.msg}` : e.msg
        })
        .join('; ')
    }
  } catch {
    // not JSON
  }
  return null
}
