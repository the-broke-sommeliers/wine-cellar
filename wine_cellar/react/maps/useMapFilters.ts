import { useEffect, useState } from 'react'

const setFormValues = (form: HTMLFormElement, params: URLSearchParams) => {
  for (const element of form.elements) {
    if (
      !(element instanceof HTMLInputElement) &&
      !(element instanceof HTMLSelectElement) &&
      !(element instanceof HTMLTextAreaElement)
    ) {
      continue
    }
    if (!element.name) {
      continue
    }
    if (
      element instanceof HTMLInputElement &&
      (element.type === 'checkbox' || element.type === 'radio')
    ) {
      element.checked = params.get(element.name) === element.value
      continue
    }
    const value = params.get(element.name) ?? ''
    if (element instanceof HTMLSelectElement && element.tomselect) {
      if (value) {
        element.tomselect.setValue(value, true)
      } else {
        element.tomselect.clear(true)
      }
    } else {
      element.value = value
    }
  }
}

export function useMapFilters(): string {
  const [search, setSearch] = useState(() => window.location.search)

  useEffect(() => {
    const form = document.querySelector<HTMLFormElement>('.filter-form')
    const clearLink = form?.querySelector<HTMLAnchorElement>('a[href="?"]')

    const applySearch = (nextSearch: string) => {
      const url = nextSearch
        ? `${window.location.pathname}${nextSearch}`
        : window.location.pathname
      window.history.pushState(null, '', url)
      setSearch(nextSearch)
    }

    const handleSubmit = (event: SubmitEvent) => {
      event.preventDefault()
      if (!form) {
        return
      }
      const params = new URLSearchParams()
      for (const [key, value] of new FormData(form).entries()) {
        if (typeof value === 'string') {
          params.append(key, value)
        }
      }
      const nextSearch = params.toString() ? `?${params.toString()}` : ''
      applySearch(nextSearch)
    }

    const handleClear = (event: MouseEvent) => {
      event.preventDefault()
      if (form) {
        setFormValues(form, new URLSearchParams())
      }
      applySearch('')
    }

    const handlePopState = () => {
      const nextSearch = window.location.search
      if (form) {
        setFormValues(form, new URLSearchParams(nextSearch))
      }
      setSearch(nextSearch)
    }

    form?.addEventListener('submit', handleSubmit)
    clearLink?.addEventListener('click', handleClear)
    window.addEventListener('popstate', handlePopState)

    return () => {
      form?.removeEventListener('submit', handleSubmit)
      clearLink?.removeEventListener('click', handleClear)
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  return search
}
