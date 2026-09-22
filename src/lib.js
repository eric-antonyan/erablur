export function cleanText(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim()
}

export function heroName(hero) {
  const first = cleanText(hero?.name?.first || hero?.first_name)
  const last = cleanText(hero?.name?.last || hero?.last_name)
  return [first, last].filter(Boolean).join(' ').trim() || 'Անանուն հերոս'
}

export function heroBirth(hero) {
  return cleanText(hero?.date?.birth || hero?.birth_date)
}

export function heroDeath(hero) {
  return cleanText(hero?.date?.dead || hero?.death_date)
}

export function initials(hero) {
  const name = heroName(hero).split(/\s+/).filter(Boolean)
  return name.slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'Հ'
}

export function formatLife(hero) {
  const birth = heroBirth(hero)
  const death = heroDeath(hero)
  if (birth && death) return `${birth} — ${death}`
  return birth || death || 'Տարեթիվը նշված չէ'
}

export function biographyParagraphs(value) {
  const html = String(value || '').trim()
  if (!html) return []

  // Mongo stores the biography as HTML. Parse it into plain, safe paragraphs
  // rather than printing raw <p>/<br> tags or injecting unsanitized HTML.
  if (typeof DOMParser !== 'undefined') {
    try {
      const doc = new DOMParser().parseFromString(html, 'text/html')
      const blocks = [...doc.body.querySelectorAll('p')]
        .map((node) => cleanText(node.textContent))
        .filter(Boolean)
      const deduped = []
      for (const block of blocks) {
        if (!deduped.includes(block)) deduped.push(block)
      }
      if (deduped.length) return deduped
      const text = cleanText(doc.body.textContent)
      return text ? [text] : []
    } catch {}
  }

  const fallback = cleanText(
    html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n')
      .replace(/<[^>]+>/g, ' '),
  )
  return fallback ? [fallback] : []
}
