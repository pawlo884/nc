import { isAxiosError } from 'axios'

export default function ApiError({ error }: { error: unknown }) {
  if (isAxiosError(error)) {
    const status = error.response?.status
    if (status === 401 || status === 403) {
      return (
        <div className="alert alert-warning">
          <strong>Wymagane logowanie.</strong> API MPD wymaga uwierzytelnienia
          sesją Django.{' '}
          <a href="/admin/login/?next=/" target="_blank" rel="noreferrer">
            Zaloguj się przez panel admina
          </a>{' '}
          i odśwież stronę.
        </div>
      )
    }
    return (
      <div className="alert alert-error">
        Błąd API ({status ?? 'brak odpowiedzi'}): {error.message}
      </div>
    )
  }
  return <div className="alert alert-error">Nieoczekiwany błąd: {String(error)}</div>
}
