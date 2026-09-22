import { ArrowRight, Search, X } from 'lucide-react'

export default function SearchField({ value, onChange, onSubmit = null, onClear = null, placeholder = 'Փնտրել հերոսի անունով…', autoFocus = false }) {
  return (
    <form className="search-field liquid-pill" onSubmit={(e) => { e.preventDefault(); onSubmit?.() }}>
      <Search className="search-field__leading" size={18} strokeWidth={2.1} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        autoComplete="off"
        autoCorrect="off"
        spellCheck="false"
        enterKeyHint="search"
        aria-label="Փնտրել հերոս"
      />
      {value ? <button type="button" className="icon-button icon-button--small search-field__clear" onClick={() => { onChange(''); onClear?.() }} aria-label="Մաքրել"><X size={15} /></button> : null}
      <button type="submit" className="search-field__submit" aria-label="Որոնել"><ArrowRight size={16} /></button>
    </form>
  )
}
