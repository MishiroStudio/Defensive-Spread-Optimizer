import {
  useMemo,
  useState,
  type KeyboardEvent,
} from 'react'

import type { Pokemon } from '../types/pokemon'

interface PokemonAutocompleteProps {
  pokemonList: Pokemon[]
  value: string
  onChange: (value: string) => void
  ariaLabelledBy: string
}

interface PokemonNameOption {
  label: string
  pokemon: Pokemon
  language: 'EN' | 'DE'
}

export function PokemonAutocomplete({
  pokemonList,
  value,
  onChange,
  ariaLabelledBy,
}: PokemonAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  const pokemonNameOptions = useMemo(() => {
    const uniqueNames =
      new Map<string, PokemonNameOption>()

    for (const pokemon of pokemonList) {
      const names: PokemonNameOption[] = [
        {
          label: pokemon.name_en.trim(),
          pokemon,
          language: 'EN',
        },
        {
          label: pokemon.name_de.trim(),
          pokemon,
          language: 'DE',
        },
      ]

      for (const nameOption of names) {
        if (nameOption.label.length === 0) {
          continue
        }

        const normalizedName =
          nameOption.label.toLocaleLowerCase()

        if (!uniqueNames.has(normalizedName)) {
          uniqueNames.set(
            normalizedName,
            nameOption,
          )
        }
      }
    }

    return Array.from(uniqueNames.values())
  }, [pokemonList])

  const suggestions = useMemo(() => {
    const query = value
      .trim()
      .toLocaleLowerCase()

    if (query.length === 0) {
      return []
    }

    return pokemonNameOptions
      .filter((option) =>
        option.label
          .toLocaleLowerCase()
          .includes(query),
      )
      .slice(0, 12)
  }, [
    pokemonNameOptions,
    value,
  ])

  function selectOption(
    option: PokemonNameOption,
  ): void {
    onChange(option.label)
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

    if (
      event.key === 'Enter'
      && activeIndex >= 0
    ) {
      event.preventDefault()
      selectOption(suggestions[activeIndex])
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
        placeholder="Search for a Pokémon"
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
              key={option.label.toLocaleLowerCase()}
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
                  {option.language}
                  {' · '}
                  #{option.pokemon.dex}
                </small>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}