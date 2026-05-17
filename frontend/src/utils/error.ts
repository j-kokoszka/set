export async function parseBackendError(response: Response, defaultMessage: string): Promise<string> {
  try {
    const errorData = await response.json();
    const detail = errorData?.detail || errorData?.error;
    if (detail) {
      return `${defaultMessage}: ${detail} (Status: ${response.status})`;
    }
    return `${defaultMessage}. Status: ${response.status}`;
  } catch {
    return `${defaultMessage}. Status: ${response.status}`;
  }
}
