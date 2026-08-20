import { useEffect, useMemo, useState } from 'react'

import { PokemonAutocomplete } from './components/PokemonAutocomplete'
import type { NatureStat } from './natures'
import {
  findBestDefensiveSpread,
  type BestDefensiveSpread,
  type HeldItem,
} from './optimizer'
import { loadPokemonData } from './pokemonData'
import type { Pokemon } from './types/pokemon'

import './App.css'

const TOTAL_INVESTMENT_POINTS = 66
const SHINY_ODDS = 2048
const MISSINGNO_SPRITE =
  `${import.meta.env.BASE_URL}assets/sprites/missingno.png`

const increasedNatureOptions = [
  { value: 'bulk', label: 'Bulk' },
  { value: 'attack', label: 'Attack' },
  { value: 'special_attack', label: 'Sp. Attack' },
  { value: 'speed', label: 'Speed' },
]

const decreasedNatureOptions = [
  { value: 'attack', label: 'Attack' },
  { value: 'special_attack', label: 'Sp. Attack' },
  { value: 'speed', label: 'Speed' },
]

const finalStatLabels = [
  'HP',
  'Attack',
  'Defense',
  'Sp. Attack',
  'Sp. Defense',
  'Speed',
] as const

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

function formatNatureName(
  nameEnglish: string,
  nameGerman: string,
): string {
  return nameEnglish === nameGerman
    ? nameEnglish
    : `${nameEnglish} / ${nameGerman}`
}

function formatDefensiveModifiers(
  item: HeldItem,
  stage: number,
  stat: DefensiveStat,
): string {
  const modifiers: string[] = []

  if (item === 'eviolite') {
    modifiers.push('Eviolite')
  }

  if (item === 'assault_vest' && stat === 'special_defense') {
    modifiers.push('Assault Vest')
  }

  if (stage !== 0) {
    const statName = stat === 'defense' ? 'Def' : 'SpD'
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
              : 'Pokémon data could not be loaded.',
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

  const isShiny = useMemo(() => (
    selectedPokemon !== null
    && Math.floor(Math.random() * SHINY_ODDS) === 0
  ), [selectedPokemon])

  const selectedPokemonSprite = useMemo(() => {
    if (selectedPokemon === null) {
      return null
    }

    const spritePath = isShiny
      ? selectedPokemon.sprite_home_shiny
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
      && Math.floor(Math.random() * SHINY_ODDS) === 0

    setSelectedPokemonName(value)
    setIsShiny(shouldUseShinySprite)
    invalidateResult()
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
        <header>
          <p className="eyebrow">
            MISHIRO
          </p>

          <h1>
            Defensive Spread Optimizer
          </h1>

          <p className="description">
            Find the bulkiest defensive spread for your Pokémon.
          </p>
        </header>

        {isLoading && (
          <p className="status-message">
            Loading Pokémon data…
          </p>
        )}

        {errorMessage !== null && (
          <p className="status-message error-message">
            {errorMessage}
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
                  onChange={handlePokemonChange}
                  ariaLabelledBy="pokemon-search-heading"
                />
              </div>
            </section>

            <div className="pokemon-selection-layout">
              <section className="settings-card nature-card">
                <div className="nature-select-fields">
                  <div className="form-field nature-select-field">
                    <h2
                      id="increased-nature-heading"
                      className="settings-heading"
                    >
                      Increased Nature Stat
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
                      {increasedNatureOptions.map((option) => (
                        <option
                          key={option.value}
                          value={option.value}
                        >
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-field nature-select-field">
                    <h2
                      id="decreased-nature-heading"
                      className="settings-heading"
                    >
                      Decreased Nature Stat
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
                      {decreasedNatureOptions.map((option) => (
                        <option
                          key={option.value}
                          value={option.value}
                        >
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </section>

              <section
                className="sprite-card"
                aria-label="Selected Pokémon"
              >
                <img
                  className={
                    selectedPokemonSprite === null
                      ? 'pokemon-sprite missingno-sprite'
                      : 'pokemon-sprite'
                  }
                  src={selectedPokemonSprite ?? MISSINGNO_SPRITE}
                  alt={
                    selectedPokemon !== null
                      ? selectedPokemon.name_en
                      : 'MissingNo placeholder'
                  }
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
              </section>
            </div>

            <section className="settings-card combined-controls-card">
              <div className="combined-controls-grid">
                <div className="control-column">
                  <div className="control-column-heading">
                    <h2 className="settings-heading">
                      Fixed Investments
                    </h2>
                  </div>

                  <div className="control-rows">
                    <div className="control-row">
                      <label htmlFor="fixed-attack">
                        Attack
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
                        Sp. Attack
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
                        Speed
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
                        {remainingDefensivePoints} remaining
                      </span>
                    </div>
                  </div>

                  {hasInvalidFixedInvestments && (
                    <p className="validation-message">
                      Fixed investments cannot exceed 66 points in total.
                    </p>
                  )}
                </div>

                <div className="control-column">
                  <div className="control-column-heading">
                    <h2 className="settings-heading">
                      Battle Modifiers
                    </h2>
                  </div>

                  <div className="control-rows">
                    <div className="control-row">
                      <label htmlFor="held-item">
                        Held Item
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
                          None
                        </option>

                        <option value="eviolite">
                          Eviolite
                        </option>

                        <option value="assault_vest">
                          Assault Vest
                        </option>
                      </select>
                    </div>

                    <div className="control-row">
                      <label htmlFor="defense-stage">
                        Def Stage
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
                        SpD Stage
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
              Optimize
            </button>
          </>
        )}

        {!isLoading && errorMessage === null && (
          <section className="result-card final-result-card">
            <div className="final-result-section">
              <h2 className="settings-heading">
                Nature
              </h2>

              <p className="result-nature-name">
                {result === null
                  ? '-'
                  : formatNatureName(
                      result.nature.name_en,
                      result.nature.name_de,
                    )}
              </p>
            </div>

            <div className="result-divider" />

            <div className="final-result-section">
              <h2 className="settings-heading">
                Final Stats
              </h2>

              <div className="final-stats-list">
                {result === null || selectedPokemon === null ? (
                  finalStatLabels.map((label) => (
                    <PlaceholderStatRow
                      key={label}
                      label={label}
                    />
                  ))
                ) : (
                  <>
                    <FinalStatRow
                      label="HP"
                      baseValue={selectedPokemon.base_hp}
                      finalValue={result.hp}
                      investmentPoints={result.hp_points}
                    />

                    <FinalStatRow
                      label="Attack"
                      baseValue={selectedPokemon.base_atk}
                      finalValue={result.attack}
                      investmentPoints={result.atk_points}
                      natureDirection={getNatureDirection(
                        result,
                        'attack',
                      )}
                    />

                    <FinalStatRow
                      label="Defense"
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
                      )}
                    />

                    <FinalStatRow
                      label="Sp. Attack"
                      baseValue={selectedPokemon.base_spa}
                      finalValue={result.special_attack}
                      investmentPoints={result.spa_points}
                      natureDirection={getNatureDirection(
                        result,
                        'special_attack',
                      )}
                    />

                    <FinalStatRow
                      label="Sp. Defense"
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
                      )}
                    />

                    <FinalStatRow
                      label="Speed"
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