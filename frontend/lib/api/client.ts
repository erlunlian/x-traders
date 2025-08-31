const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    let authHeader: Record<string, string> = {};
    if (typeof window !== "undefined") {
      try {
        const token = window.localStorage.getItem("admin_token");
        if (token) authHeader = { Authorization: `Bearer ${token}` };
      } catch {}
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeader,
        ...options.headers,
      },
    });

    if (response.status === 401) {
      // On 401, clear token and notify listeners; do not redirect here
      if (typeof window !== "undefined") {
        try {
          window.localStorage.removeItem("admin_token");
        } catch {}
        try {
          window.dispatchEvent(new CustomEvent("adminUnauthorized"));
        } catch {}
      }
      let msg = `API Error: 401 Unauthorized`;
      try {
        const body = await response.json();
        if (body && (body.message || body.detail)) {
          msg = String(body.message || body.detail);
        }
      } catch {}
      throw new Error(msg);
    }

    if (!response.ok) {
      let msg = `API Error: ${response.status} ${response.statusText}`;
      try {
        const body = await response.json();
        if (body && (body.message || body.detail)) {
          msg = String(body.message || body.detail);
        }
      } catch {}
      throw new Error(msg);
    }

    return response.json();
  }

  // GET request
  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  // POST request
  async post<T, D = unknown>(endpoint: string, data?: D): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T, D = unknown>(endpoint: string, data?: D): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }
}

export const apiClient = new ApiClient();
