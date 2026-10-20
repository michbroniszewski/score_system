// Reads API v1. The Pages build (VITE_STATIC_DATA=true) reads the static snapshot that
// `make export` writes, where every response is a file at the same path plus ".json";
// otherwise the live API is used (proxied by the Vite dev server, see vite.config.ts).
const staticData = import.meta.env.VITE_STATIC_DATA === 'true'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly url: string,
  ) {
    super(`${url} answered ${status}`)
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
