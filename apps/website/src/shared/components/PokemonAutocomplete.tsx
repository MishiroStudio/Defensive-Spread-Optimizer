import {
  useMemo,
  useState,
  type KeyboardEvent,
} from 'react'

import type { Pokemon } from '../types/pokemon'
import {
  findPokemonSuggestions,
  type PokemonDisplayLanguage,
  type PokemonNameOption,
} from './pokemonAutocompleteData'

interface PokemonAutocompleteProps {
  pokemonList: Pokemon[]
  value: string
  language: PokemonDisplayLanguage
  placeholder: string
  onChange: (value: string) => void
  onSelect: (pokemon: Pokemon) => void
  ariaLabelledBy: string
}

export function PokemonAutocomplete({
  pokemonList,
  value,
  language,
  placeholder,
  onChange,
  onSelect,
  ariaLabelledBy,
}: PokemonAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const suggestions = useMemo(
    () => findPokemonSuggestions(
      pokemonList,
      value,
      language,
    ),
    [language, pokemonList, value],
  )

  function selectOption(
    option: PokemonNameOption,
  ): void {
    onSelect(option.pokemon)
    setIsOpen(false)
    setActiveIndex(-1)
  }

  function handleInputChange(
    newValue: string,
  ): void {
    onChange(newValue)
    setIsOpen(true)
    setActiveIndex(-1)
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
  ): void {
    if (event.key === 'Escape') {
      setIsOpen(false)
      setActiveIndex(-1)
      return
    }

    if (suggestions.length === 0) {
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setIsOpen(true)

      setActiveIndex((currentIndex) =>
        Math.min(
          currentIndex + 1,
          suggestions.length - 1,
        ),
      )
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      setIsOpen(true)

      setActiveIndex((currentIndex) =>
        Math.max(currentIndex - 1, 0),
      )
    }

    if (event.key === 'Enter') {
      event.preventDefault()
      selectOption(
        suggestions[activeIndex >= 0 ? activeIndex : 0],
      )
    }
  }

  return (
    <div className="autocomplete">
      <input
        id="pokemon-search"
        aria-labelledby={ariaLabelledBy}
        className="pokemon-search"
        type="text"
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls="pokemon-suggestions"
        onFocus={() => {
          if (value.trim().length > 0) {
            setIsOpen(true)
          }
        }}
        onBlur={() => {
          setIsOpen(false)
          setActiveIndex(-1)
        }}
        onChange={(event) =>
          handleInputChange(event.target.value)
        }
        onKeyDown={handleKeyDown}
      />

      {isOpen && suggestions.length > 0 && (
        <ul
          id="pokemon-suggestions"
          className="autocomplete-list"
          role="listbox"
        >
          {suggestions.map((option, index) => (
            <li
              key={option.pokemon.pokemon_id}
              role="option"
              aria-selected={index === activeIndex}
            >
              <button
                className={
                  index === activeIndex
                    ? 'autocomplete-option active'
                    : 'autocomplete-option'
                }
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault()
                  selectOption(option)
                }}
                onMouseEnter={() =>
                  setActiveIndex(index)
                }
              >
                <span>{option.label}</span>

                <small>
                  #{String(option.pokemon.dex).padStart(4, '0')}
                </small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
