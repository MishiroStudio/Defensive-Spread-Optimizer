import { useEffect, useMemo, useState } from 'react'

import {
  PokemonAutocomplete,
} from '../../shared/components/PokemonAutocomplete'
import {
  localizedPokemonName,
  type PokemonDisplayLanguage,
} from '../../shared/components/pokemonAutocompleteData'
import type { NatureStat } from '../../shared/calculations/natures'
import {
  findBestDefensiveSpread,
  type BestDefensiveSpread,
  type HeldItem,
} from './optimizer'
import { loadPokemonData } from './pokemonData'
import type { Pokemon } from '../../shared/types/pokemon'

import './optimizer.css'

const TOTAL_INVESTMENT_POINTS = 66
const SHINY_ODDS = 2048
const LANGUAGE_KEY = 'mishiro-defensive-spread-optimizer-language'
const MISSINGNO_SPRITE =
  `${import.meta.env.BASE_URL}assets/sprites/missingno.png`

type Language = PokemonDisplayLanguage

const TYPE_COLORS: Record<string, string> = {
  normal: '#9FA19F',
  grass: '#3FA129',
  fire: '#E62829',
  water: '#2980EF',
  electric: '#FAC000',
  bug: '#91A119',
  flying: '#81B9EF',
  rock: '#AFA981',
  poison: '#9141CB',
  ground: '#915121',
  ice: '#3FD8FF',
  fighting: '#FF8000',
  psychic: '#EF4179',
  ghost: '#704170',
  dragon: '#5060E1',
  dark: '#50413F',
  steel: '#60A1B8',
  fairy: '#EF70EF',
}

const TYPE_NAMES: Record<Language, Record<string, string>> = {
  de: {
    normal: 'Normal',
    fire: 'Feuer',
    water: 'Wasser',
    electric: 'Elektro',
    grass: 'Pflanze',
    ice: 'Eis',
    fighting: 'Kampf',
    poison: 'Gift',
    ground: 'Boden',
    flying: 'Flug',
    psychic: 'Psycho',
    bug: 'Käfer',
    rock: 'Gestein',
    ghost: 'Geist',
    dragon: 'Drache',
    dark: 'Unlicht',
    steel: 'Stahl',
    fairy: 'Fee',
  },
  en: {
    normal: 'Normal',
    fire: 'Fire',
    water: 'Water',
    electric: 'Electric',
    grass: 'Grass',
    ice: 'Ice',
    fighting: 'Fighting',
    poison: 'Poison',
    ground: 'Ground',
    flying: 'Flying',
    psychic: 'Psychic',
    bug: 'Bug',
    rock: 'Rock',
    ghost: 'Ghost',
    dragon: 'Dragon',
    dark: 'Dark',
    steel: 'Steel',
    fairy: 'Fairy',
  },
}

const COPY = {
  de: {
    subtitle: 'Finde den defensiv stärksten Stat-Spread für dein Pokémon.',
    switchPrompt: 'Switch to',
    switchLanguage: 'English',
    loading: 'Pokémon-Daten werden geladen …',
    loadError: 'Die Pokémon-Daten konnten nicht geladen werden.',
    searchPlaceholder: 'Nach einem Pokémon suchen',
    shiny: 'Shiny',
    dex: 'Nationaldex',
    abilities: 'Fähigkeiten',
    increasedNatureStat: 'Erhöhter Statuswert',
    decreasedNatureStat: 'Verringerter Statuswert',
    bulk: 'Bulk',
    attack: 'Angriff',
    defense: 'Verteidigung',
    specialAttack: 'Sp. Angriff',
    specialDefense: 'Sp. Verteidigung',
    speed: 'Initiative',
    fixedInvestments: 'Fixe Investitionen',
    remaining: 'verbleibend',
    invalidInvestments: 'Fixe Investitionen dürfen zusammen höchstens 66 Punkte betragen.',
    battleModifiers: 'Kampfmodifikatoren',
    heldItem: 'Item',
    none: 'Keines',
    eviolite: 'Evolith',
    assaultVest: 'Offensivweste',
    defenseStage: 'Vert.-Stufe',
    specialDefenseStage: 'SpV-Stufe',
    optimize: 'Optimieren',
    statAlignment: 'Stat Alignment',
    finalStats: 'Finale Statuswerte',
  },
  en: {
    subtitle: 'Find the bulkiest defensive spread for your Pokémon.',
    switchPrompt: 'Wechsel zu',
    switchLanguage: 'Deutsch',
    loading: 'Loading Pokémon data…',
    loadError: 'Pokémon data could not be loaded.',
    searchPlaceholder: 'Search for a Pokémon',
    shiny: 'Shiny',
    dex: 'National Dex',
    abilities: 'Abilities',
    increasedNatureStat: 'Increased Nature Stat',
    decreasedNatureStat: 'Decreased Nature Stat',
    bulk: 'Bulk',
    attack: 'Attack',
    defense: 'Defense',
    specialAttack: 'Sp. Attack',
    specialDefense: 'Sp. Defense',
    speed: 'Speed',
    fixedInvestments: 'Fixed Investments',
    remaining: 'remaining',
    invalidInvestments: 'Fixed investments cannot exceed 66 points in total.',
    battleModifiers: 'Battle Modifiers',
    heldItem: 'Held Item',
    none: 'None',
    eviolite: 'Eviolite',
    assaultVest: 'Assault Vest',
    defenseStage: 'Def Stage',
    specialDefenseStage: 'SpD Stage',
    optimize: 'Optimize',
    statAlignment: 'Stat Alignment',
    finalStats: 'Final Stats',
  },
} as const

const RESULT_STAT_LABELS: Record<Language, {
  hp: string
  attack: string
  defense: string
  specialAttack: string
  specialDefense: string
  speed: string
}> = {
  de: {
    hp: 'KP',
    attack: 'Angr',
    defense: 'Vert',
    specialAttack: 'SpA',
    specialDefense: 'SpV',
    speed: 'Init',
  },
  en: {
    hp: 'HP',
    attack: 'Attack',
    defense: 'Defense',
    specialAttack: 'Sp. Attack',
    specialDefense: 'Sp. Defense',
    speed: 'Speed',
  },
}

const statStageOptions = Array.from(
  { length: 13 },
  (_, index) => 6 - index,
)

type DefensiveStat = 'defense' | 'special_defense'
type NatureDirection = 'increased' | 'decreased' | null

interface FinalStatRowProps {
  label: string
  baseValue: number
  finalValue: number
  investmentPoints: number
  natureDirection?: NatureDirection
  modifiedValue?: number
  modifierText?: string
}

function formatStatStage(stage: number): string {
  return stage > 0 ? `+${stage}` : stage.toString()
}

function formatInvestment(points: number): string {
  return points > 0 ? `(+${points})` : ''
}

function localizedNatureName(
  nameEnglish: string,
  nameGerman: string,
  language: Language,
): string {
  return language === 'de'
    ? nameGerman || nameEnglish
    : nameEnglish || nameGerman
}

function formatDefensiveModifiers(
  item: HeldItem,
  stage: number,
  stat: DefensiveStat,
  language: Language,
): string {
  const modifiers: string[] = []
  const text = COPY[language]

  if (item === 'eviolite') {
    modifiers.push(text.eviolite)
  }

  if (item === 'assault_vest' && stat === 'special_defense') {
    modifiers.push(text.assaultVest)
  }

  if (stage !== 0) {
    const statName = stat === 'defense'
      ? language === 'de' ? 'Vert' : 'Def'
      : language === 'de' ? 'SpV' : 'SpD'
    modifiers.push(`${formatStatStage(stage)} ${statName}`)
  }

  return modifiers.length > 0
    ? `(${modifiers.join(', ')})`
    : ''
}

function normalizePokemonName(name: string): string {
  return name.trim().toLocaleLowerCase()
}

function findPokemonByName(
  pokemonList: Pokemon[],
  name: string,
): Pokemon | null {
  const normalizedName = normalizePokemonName(name)

  if (normalizedName === '') {
    return null
  }

  return pokemonList.find((pokemon) => (
    normalizePokemonName(pokemon.name_en) === normalizedName
    || normalizePokemonName(pokemon.name_de) === normalizedName
  )) ?? null
}

function getNatureDirection(
  result: BestDefensiveSpread,
  stat: NatureStat,
): NatureDirection {
  if (result.nature.positive === stat) {
    return 'increased'
  }

  if (result.nature.negative === stat) {
    return 'decreased'
  }

  return null
}

function FinalStatRow({
  label,
  baseValue,
  finalValue,
  investmentPoints,
  natureDirection = null,
  modifiedValue,
  modifierText = '',
}: FinalStatRowProps) {
  const natureArrow =
    natureDirection === 'increased'
      ? '↑'
      : natureDirection === 'decreased'
        ? '↓'
        : ''

  const labelClassName = natureDirection === null
    ? 'final-stat-label'
    : `final-stat-label ${natureDirection}`

  const hasModifiedValue =
    modifiedValue !== undefined
    && modifiedValue !== finalValue

  return (
    <div className="final-stat-row">
      <span className={labelClassName}>
        {label}

        {natureArrow !== '' && (
          <span className="nature-arrow">
            {natureArrow}
          </span>
        )}
      </span>

      <div className="final-stat-values">
        <span className="base-stat-value">
          {baseValue}
        </span>

        <span className="stat-arrow primary-stat-arrow">
          →
        </span>

        <strong className="final-stat-value">
          {finalValue}
        </strong>

        {investmentPoints > 0 && (
          <span className="stat-note">
            {formatInvestment(investmentPoints)}
          </span>
        )}

        {hasModifiedValue && (
          <>
            <span className="stat-arrow modifier-arrow">
              →
            </span>

            <strong className="modified-stat">
              {modifiedValue}
            </strong>

            {modifierText !== '' && (
              <span className="modifier-note">
                {modifierText}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function PlaceholderStatRow({
  label,
}: {
  label: string
}) {
  return (
    <div className="final-stat-row">
      <span className="final-stat-label">
        {label}
      </span>

      <div className="final-stat-values">
        <span className="base-stat-value">
          -
        </span>
      </div>
    </div>
  )
}

type InvestmentInput = number | ''

function parseInvestmentInput(
  value: string,
): InvestmentInput {
  return value === ''
    ? ''
    : Number(value)
}

function investmentValue(
  value: InvestmentInput,
): number {
  return value === ''
    ? 0
    : value
}

function App() {
  const [language, setLanguage] = useState<Language>(() => {
    if (typeof window === 'undefined') {
      return 'de'
    }

    const storedLanguage = window.localStorage.getItem(LANGUAGE_KEY)

    return storedLanguage === 'de' || storedLanguage === 'en'
      ? storedLanguage
      : 'de'
  })
  const [pokemonList, setPokemonList] = useState<Pokemon[]>([])
  const [selectedPokemonName, setSelectedPokemonName] = useState('')
  const [increasedNatureStat, setIncreasedNatureStat] = useState('bulk')
  const [decreasedNatureStat, setDecreasedNatureStat] = useState('attack')
  const [fixedAttackPoints, setFixedAttackPoints] = useState<InvestmentInput>(0)
  const [fixedSpecialAttackPoints, setFixedSpecialAttackPoints,] = useState<InvestmentInput>(0)
  const [fixedSpeedPoints, setFixedSpeedPoints,] = useState<InvestmentInput>(0)
  const [heldItem, setHeldItem] = useState<HeldItem>('none')
  const [defenseStage, setDefenseStage] = useState(0)
  const [specialDefenseStage, setSpecialDefenseStage] = useState(0)
  const [result, setResult] = useState<BestDefensiveSpread | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isShiny, setIsShiny] = useState(false)

  const text = COPY[language]
  const resultStatLabels = RESULT_STAT_LABELS[language]

  useEffect(() => {
    document.documentElement.lang = language
    window.localStorage.setItem(LANGUAGE_KEY, language)
  }, [language])

  useEffect(() => {
    let isCancelled = false

    async function loadData(): Promise<void> {
      try {
        const pokemonData = await loadPokemonData()

        if (!isCancelled) {
          setPokemonList(pokemonData)
        }
      } catch (error: unknown) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : COPY.de.loadError,
          )
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadData()

    return () => {
      isCancelled = true
    }
  }, [])

  const selectedPokemon = useMemo(
    () => findPokemonByName(
      pokemonList,
      selectedPokemonName,
    ),
    [pokemonList, selectedPokemonName],
  )

  const selectedPokemonSprite = useMemo(() => {
    if (selectedPokemon === null) {
      return null
    }

    const spritePath = isShiny
      ? selectedPokemon.sprite_home_shiny
        ?? selectedPokemon.sprite_home
      : selectedPokemon.sprite_home

    return spritePath === null
      ? null
      : `${import.meta.env.BASE_URL}${spritePath}`
  }, [isShiny, selectedPokemon])

  const attackPoints =
  investmentValue(fixedAttackPoints)

  const specialAttackPoints =
    investmentValue(fixedSpecialAttackPoints)

  const speedPoints =
    investmentValue(fixedSpeedPoints)

  const fixedInvestmentTotal =
    attackPoints
    + specialAttackPoints
    + speedPoints

  const remainingDefensivePoints =
    TOTAL_INVESTMENT_POINTS
    - fixedInvestmentTotal

  const hasInvalidFixedInvestments =
    remainingDefensivePoints < 0

  function invalidateResult(): void {
    setResult(null)
  }

  function handlePokemonChange(
    value: string,
  ): void {
    const nextPokemon = findPokemonByName(
      pokemonList,
      value,
    )

    const shouldUseShinySprite =
      nextPokemon !== null
      && nextPokemon.sprite_home_shiny !== null
      && Math.floor(Math.random() * SHINY_ODDS) === 0

    setSelectedPokemonName(value)
    setIsShiny(shouldUseShinySprite)
    invalidateResult()
  }

  function handlePokemonSelect(
    pokemon: Pokemon,
  ): void {
    const shouldUseShinySprite =
      pokemon.sprite_home_shiny !== null
      && Math.floor(Math.random() * SHINY_ODDS) === 0

    setSelectedPokemonName(
      localizedPokemonName(pokemon, language),
    )
    setIsShiny(shouldUseShinySprite)
    invalidateResult()
  }

  function toggleLanguage(): void {
    const nextLanguage = language === 'de' ? 'en' : 'de'

    setLanguage(nextLanguage)

    if (selectedPokemon !== null) {
      setSelectedPokemonName(
        localizedPokemonName(selectedPokemon, nextLanguage),
      )
    }
  }

  function optimize(): void {
    if (
      selectedPokemon === null
      || hasInvalidFixedInvestments
    ) {
      return
    }

    const spread = findBestDefensiveSpread(
      selectedPokemon,
      increasedNatureStat,
      decreasedNatureStat,
      attackPoints,
      specialAttackPoints,
      speedPoints,
      defenseStage,
      specialDefenseStage,
      heldItem,
    )

    setResult(spread)
  }

  return (
    <main className="app">
      <section className="optimizer-card">
        <header className="app-header">
          <div className="brand-block">
            <p className="eyebrow">
              MISHIRO
            </p>

            <h1>
              Defensive Spread Optimizer
            </h1>

            <p className="description">
              {text.subtitle}
            </p>
          </div>

          <div className="language-control">
            <span>{text.switchPrompt}</span>
            <button type="button" onClick={toggleLanguage}>
              {text.switchLanguage}
            </button>
          </div>
        </header>

        {isLoading && (
          <p className="status-message">
            {text.loading}
          </p>
        )}

        {errorMessage !== null && (
          <p className="status-message error-message">
            {text.loadError}
          </p>
        )}

        {!isLoading && errorMessage === null && (
          <>
            <section className="search-card">
              <div className="form-field">
                <h2
                  id="pokemon-search-heading"
                  className="settings-heading"
                >
                  Pokémon
                </h2>

                <PokemonAutocomplete
                  pokemonList={pokemonList}
                  value={selectedPokemonName}
                  language={language}
                  placeholder={text.searchPlaceholder}
                  onChange={handlePokemonChange}
                  onSelect={handlePokemonSelect}
                  ariaLabelledBy="pokemon-search-heading"
                />
              </div>
            </section>

            {selectedPokemon !== null && (
              <section className="identity-card">
                <div className="sprite-column">
                  <div className="sprite-stage">
                    <img
                      className={
                        selectedPokemonSprite === null
                          ? 'pokemon-sprite missingno-sprite'
                          : 'pokemon-sprite'
                      }
                      src={selectedPokemonSprite ?? MISSINGNO_SPRITE}
                      alt={localizedPokemonName(
                        selectedPokemon,
                        language,
                      )}
                      onError={(event) => {
                        const image = event.currentTarget

                        if (image.dataset.fallbackApplied === 'true') {
                          return
                        }

                        image.dataset.fallbackApplied = 'true'
                        image.src = MISSINGNO_SPRITE
                        image.classList.add('missingno-sprite')
                      }}
                    />
                  </div>

                  <label className="shiny-control">
                    <input
                      type="checkbox"
                      checked={isShiny}
                      disabled={selectedPokemon.sprite_home_shiny === null}
                      onChange={(event) => {
                        setIsShiny(event.target.checked)
                      }}
                    />
                    <span>{text.shiny}</span>
                  </label>
                </div>

                <div className="identity-details">
                  <p className="dex-label">
                    {text.dex}
                    {' '}
                    #{String(selectedPokemon.dex).padStart(4, '0')}
                  </p>

                  <h2>
                    {localizedPokemonName(selectedPokemon, language)}
                  </h2>

                  {selectedPokemon.name_de !== selectedPokemon.name_en && (
                    <p className="other-name">
                      {localizedPokemonName(
                        selectedPokemon,
                        language === 'de' ? 'en' : 'de',
                      )}
                    </p>
                  )}

                  <div className="type-chips">
                    {selectedPokemon.types.map((type) => (
                      <span
                        className="type-chip"
                        key={type}
                        style={{
                          backgroundColor:
                            TYPE_COLORS[type] ?? '#94a3b8',
                        }}
                      >
                        {TYPE_NAMES[language][type] ?? type}
                      </span>
                    ))}
                  </div>

                  <h3>{text.abilities}</h3>

                  <div className="ability-buttons">
                    {selectedPokemon.abilities.map((ability) => (
                      <span key={ability.api_name}>
                        {language === 'de'
                          ? ability.name_de || ability.name_en
                          : ability.name_en || ability.name_de}
                      </span>
                    ))}
                  </div>
                </div>
              </section>
            )}

            <section className="settings-card nature-card">
              <div className="nature-select-fields">
                <div className="form-field nature-select-field">
                  <h2
                    id="increased-nature-heading"
                    className="settings-heading"
                  >
                    {text.increasedNatureStat}
                  </h2>

                  <select
                    id="increased-nature-stat"
                    aria-labelledby="increased-nature-heading"
                    value={increasedNatureStat}
                    onChange={(event) => {
                      setIncreasedNatureStat(event.target.value)
                      invalidateResult()
                    }}
                  >
                    <option value="bulk">{text.bulk}</option>
                    <option value="attack">{text.attack}</option>
                    <option value="special_attack">
                      {text.specialAttack}
                    </option>
                    <option value="speed">{text.speed}</option>
                  </select>
                </div>

                <div className="form-field nature-select-field">
                  <h2
                    id="decreased-nature-heading"
                    className="settings-heading"
                  >
                    {text.decreasedNatureStat}
                  </h2>

                  <select
                    id="decreased-nature-stat"
                    aria-labelledby="decreased-nature-heading"
                    value={decreasedNatureStat}
                    onChange={(event) => {
                      setDecreasedNatureStat(event.target.value)
                      invalidateResult()
                    }}
                  >
                    <option value="attack">{text.attack}</option>
                    <option value="special_attack">
                      {text.specialAttack}
                    </option>
                    <option value="speed">{text.speed}</option>
                  </select>
                </div>
              </div>
            </section>

            <section className="settings-card combined-controls-card">
              <div className="combined-controls-grid">
                <div className="control-column">
                  <div className="control-column-heading">
                    <h2 className="settings-heading">
                      {text.fixedInvestments}
                    </h2>
                  </div>

                  <div className="control-rows">
                    <div className="control-row">
                      <label htmlFor="fixed-attack">
                        {text.attack}
                      </label>

                      <input
                        id="fixed-attack"
                        type="number"
                        min="0"
                        max="32"
                        value={fixedAttackPoints}
                        onChange={(event) => {
                          setFixedAttackPoints(
                            parseInvestmentInput(event.target.value),
                          )
                          setResult(null)
                        }}
                        onBlur={() => {
                          if (fixedAttackPoints === '') {
                            setFixedAttackPoints(0)
                          }
                        }}
                      />
                    </div>

                    <div className="control-row">
                      <label htmlFor="fixed-special-attack">
                        {text.specialAttack}
                      </label>

                      <input
                        id="fixed-special-attack"
                        type="number"
                        min="0"
                        max="32"
                        value={fixedSpecialAttackPoints}
                        onChange={(event) => {
                          setFixedSpecialAttackPoints(
                            parseInvestmentInput(event.target.value),
                          )
                          setResult(null)
                        }}
                        onBlur={() => {
                          if (fixedSpecialAttackPoints === '') {
                            setFixedSpecialAttackPoints(0)
                          }
                        }}
                      />
                    </div>

                    <div className="control-row">
                      <label htmlFor="fixed-speed">
                        {text.speed}
                      </label>

                      <input
                        id="fixed-speed"
                        type="number"
                        min="0"
                        max="32"
                        value={fixedSpeedPoints}
                        onChange={(event) => {
                          setFixedSpeedPoints(
                            parseInvestmentInput(event.target.value),
                          )
                          setResult(null)
                        }}
                        onBlur={() => {
                          if (fixedSpeedPoints === '') {
                            setFixedSpeedPoints(0)
                          }
                        }}
                      />
                    </div>

                    <div className="control-row remaining-points-row">
                      <span aria-hidden="true" />

                      <span
                        className={
                          hasInvalidFixedInvestments
                            ? 'remaining-points-note invalid'
                            : 'remaining-points-note'
                        }
                      >
                        {remainingDefensivePoints} {text.remaining}
                      </span>
                    </div>
                  </div>

                  {hasInvalidFixedInvestments && (
                    <p className="validation-message">
                      {text.invalidInvestments}
                    </p>
                  )}
                </div>

                <div className="control-column">
                  <div className="control-column-heading">
                    <h2 className="settings-heading">
                      {text.battleModifiers}
                    </h2>
                  </div>

                  <div className="control-rows">
                    <div className="control-row">
                      <label htmlFor="held-item">
                        {text.heldItem}
                      </label>

                      <select
                        id="held-item"
                        value={heldItem}
                        onChange={(event) => {
                          setHeldItem(event.target.value as HeldItem)
                          invalidateResult()
                        }}
                      >
                        <option value="none">
                          {text.none}
                        </option>

                        <option value="eviolite">
                          {text.eviolite}
                        </option>

                        <option value="assault_vest">
                          {text.assaultVest}
                        </option>
                      </select>
                    </div>

                    <div className="control-row">
                      <label htmlFor="defense-stage">
                        {text.defenseStage}
                      </label>

                      <select
                        id="defense-stage"
                        value={defenseStage}
                        onChange={(event) => {
                          setDefenseStage(Number(event.target.value))
                          invalidateResult()
                        }}
                      >
                        {statStageOptions.map((stage) => (
                          <option key={stage} value={stage}>
                            {formatStatStage(stage)}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="control-row">
                      <label htmlFor="special-defense-stage">
                        {text.specialDefenseStage}
                      </label>

                      <select
                        id="special-defense-stage"
                        value={specialDefenseStage}
                        onChange={(event) => {
                          setSpecialDefenseStage(Number(event.target.value))
                          invalidateResult()
                        }}
                      >
                        {statStageOptions.map((stage) => (
                          <option key={stage} value={stage}>
                            {formatStatStage(stage)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <button
              className="optimize-button"
              type="button"
              disabled={
                selectedPokemon === null
                || hasInvalidFixedInvestments
              }
              onClick={optimize}
            >
              {text.optimize}
            </button>
          </>
        )}

        {!isLoading && errorMessage === null && (
          <section className="result-card final-result-card">
            <div className="final-result-section">
              <h2 className="settings-heading">
                {text.statAlignment}
              </h2>

              <p className="result-nature-name">
                {result === null
                  ? '-'
                  : localizedNatureName(
                      result.nature.name_en,
                      result.nature.name_de,
                      language,
                    )}
              </p>
            </div>

            <div className="result-divider" />

            <div className="final-result-section">
              <h2 className="settings-heading">
                {text.finalStats}
              </h2>

              <div className="final-stats-list">
                {result === null || selectedPokemon === null ? (
                  [
                    resultStatLabels.hp,
                    resultStatLabels.attack,
                    resultStatLabels.defense,
                    resultStatLabels.specialAttack,
                    resultStatLabels.specialDefense,
                    resultStatLabels.speed,
                  ].map((label) => (
                    <PlaceholderStatRow
                      key={label}
                      label={label}
                    />
                  ))
                ) : (
                  <>
                    <FinalStatRow
                      label={resultStatLabels.hp}
                      baseValue={selectedPokemon.base_hp}
                      finalValue={result.hp}
                      investmentPoints={result.hp_points}
                    />

                    <FinalStatRow
                      label={resultStatLabels.attack}
                      baseValue={selectedPokemon.base_atk}
                      finalValue={result.attack}
                      investmentPoints={result.atk_points}
                      natureDirection={getNatureDirection(
                        result,
                        'attack',
                      )}
                    />

                    <FinalStatRow
                      label={resultStatLabels.defense}
                      baseValue={selectedPokemon.base_def}
                      finalValue={result.raw_defense}
                      investmentPoints={result.def_points}
                      natureDirection={getNatureDirection(
                        result,
                        'defense',
                      )}
                      modifiedValue={result.defense}
                      modifierText={formatDefensiveModifiers(
                        result.held_item,
                        result.defense_stage,
                        'defense',
                        language,
                      )}
                    />

                    <FinalStatRow
                      label={resultStatLabels.specialAttack}
                      baseValue={selectedPokemon.base_spa}
                      finalValue={result.special_attack}
                      investmentPoints={result.spa_points}
                      natureDirection={getNatureDirection(
                        result,
                        'special_attack',
                      )}
                    />

                    <FinalStatRow
                      label={resultStatLabels.specialDefense}
                      baseValue={selectedPokemon.base_spd}
                      finalValue={result.raw_special_defense}
                      investmentPoints={result.spd_points}
                      natureDirection={getNatureDirection(
                        result,
                        'special_defense',
                      )}
                      modifiedValue={result.special_defense}
                      modifierText={formatDefensiveModifiers(
                        result.held_item,
                        result.special_defense_stage,
                        'special_defense',
                        language,
                      )}
                    />

                    <FinalStatRow
                      label={resultStatLabels.speed}
                      baseValue={selectedPokemon.base_spe}
                      finalValue={result.speed}
                      investmentPoints={result.spe_points}
                      natureDirection={getNatureDirection(
                        result,
                        'speed',
                      )}
                    />
                  </>
                )}
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  )
}

export default App
