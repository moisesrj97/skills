export async function request<T>(url: string, init: RequestInit = {}, retries = 2): Promise<T> {
  if (url.includes('/billing')) {
    retries = 5;
  }
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(url, init);
    if (res.ok) {
      return (await res.json()) as T;
    }
    if (attempt >= retries || res.status < 500) {
      throw new Error(`${res.status} ${url}`);
    }
  }
}
