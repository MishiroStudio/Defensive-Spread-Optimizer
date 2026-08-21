import { calculateSimpleDamage } from './damage'
import {
  getNaturesByStatChanges,
  type Nature,
} from './natures'
import {
  calculateAttack,
  calculateDefense,
  calculateHp,
  calculateSpecialAttack,
  calculateSpecialDefense,
  calculateSpeed,
} from './stats'

export type HeldItem =
  | 'none'
  | 'eviolite'
  | 'assault_vest'

export interface PokemonBaseStats {
  base_hp: number
  base_atk: number
  base_def: number
  base_spa: number
  base_spd: number
  base_spe: number
}

export interface DefensiveStats {
  defense: number
  specialDefense: number
}

export interface BestDefensiveSpread {
  nature: Nature

  hp_points: number
  atk_points: number
  def_points: number
  spa_points: number
  spd_points: number
  spe_points: number

  hp: number
  attack: number
  raw_defense: number
  raw_special_defense: number
  defense: number
  special_defense: number
  special_attack: number
  speed: number

  defense_stage: number
  special_defense_stage: number
  held_item: HeldItem

  score: number
}

function validateStatStage(stage: number): void {
  if (
    !Number.isInteger(stage)
    || stage < -6
    || stage > 6
  ) {
    throw new RangeError(
      `Stat stage must be an integer from -6 to +6, received ${stage}`,
    )
  }
}

export function applyStatStage(
  stat: number,
  stage: number,
): number {
  validateStatStage(stage)

  if (stage >= 0) {
    return Math.floor(
      (stat * (2 + stage)) / 2,
    )
  }

  return Math.floor(
    (stat * 2) / (2 - stage),
  )
}

export function applyDefensiveItem(
  defense: number,
  specialDefense: number,
  heldItem: HeldItem,
): DefensiveStats {
  switch (heldItem) {
    case 'eviolite':
      return {
        defense: Math.floor(defense * 1.5),
        specialDefense: Math.floor(
          specialDefense * 1.5,
        ),
      }

    case 'assault_vest':
      return {
        defense,
        specialDefense: Math.floor(
          specialDefense * 1.5,
        ),
      }

    case 'none':
      return {
        defense,
        specialDefense,
      }

    default: {
      const exhaustiveCheck: never = heldItem

      throw new Error(
        `Unsupported held item: ${exhaustiveCheck}`,
      )
    }
  }
}

export function findBestDefensiveSpread(
  pokemon: PokemonBaseStats,
  increasedNatureStat: string,
  decreasedNatureStat: string,
  fixedAttackPoints = 0,
  fixedSpecialAttackPoints = 0,
  fixedSpeedPoints = 0,
  defenseStage = 0,
  specialDefenseStage = 0,
  heldItem: HeldItem = 'none',
): BestDefensiveSpread | null {
  const remainingPoints =
    66
    - fixedAttackPoints
    - fixedSpecialAttackPoints
    - fixedSpeedPoints

  let bestScore: number | null = null
  let bestSpread: BestDefensiveSpread | null = null

  const possibleNatures =
    getNaturesByStatChanges(
      increasedNatureStat,
      decreasedNatureStat,
    )

  const natureEntries = Object.values(
    possibleNatures,
  ).filter(
    (nature): nature is Nature =>
      nature !== undefined,
  )

  if (natureEntries.length === 0) {
    return null
  }

  for (const nature of natureEntries) {
    for (
      let hpPoints = 0;
      hpPoints <= 32;
      hpPoints += 1
    ) {
      for (
        let defensePoints = 0;
        defensePoints <= 32;
        defensePoints += 1
      ) {
        for (
          let specialDefensePoints = 0;
          specialDefensePoints <= 32;
          specialDefensePoints += 1
        ) {
          const defensivePointTotal =
            hpPoints
            + defensePoints
            + specialDefensePoints

          if (
            defensivePointTotal
            !== remainingPoints
          ) {
            continue
          }

          const hp = calculateHp(
            pokemon.base_hp,
            hpPoints,
          )

          const attack = calculateAttack(
            pokemon.base_atk,
            fixedAttackPoints,
            nature.attack,
          )

          const rawDefense = calculateDefense(
            pokemon.base_def,
            defensePoints,
            nature.defense,
          )

          const specialAttack =
            calculateSpecialAttack(
              pokemon.base_spa,
              fixedSpecialAttackPoints,
              nature.special_attack,
            )

          const rawSpecialDefense =
            calculateSpecialDefense(
              pokemon.base_spd,
              specialDefensePoints,
              nature.special_defense,
            )

          const speed = calculateSpeed(
            pokemon.base_spe,
            fixedSpeedPoints,
            nature.speed,
          )

          const stagedDefense = applyStatStage(
            rawDefense,
            defenseStage,
          )

          const stagedSpecialDefense =
            applyStatStage(
              rawSpecialDefense,
              specialDefenseStage,
            )

          const effectiveStats =
            applyDefensiveItem(
              stagedDefense,
              stagedSpecialDefense,
              heldItem,
            )

          const physicalDamage =
            calculateSimpleDamage(
              effectiveStats.defense,
            )

          const specialDamage =
            calculateSimpleDamage(
              effectiveStats.specialDefense,
            )

          const score =
            physicalDamage / hp
            + specialDamage / hp

          if (
            bestScore === null
            || score < bestScore
          ) {
            bestScore = score

            bestSpread = {
              nature,

              hp_points: hpPoints,
              atk_points: fixedAttackPoints,
              def_points: defensePoints,
              spa_points:
                fixedSpecialAttackPoints,
              spd_points:
                specialDefensePoints,
              spe_points: fixedSpeedPoints,

              hp,
              attack,

              raw_defense: rawDefense,
              raw_special_defense:
                rawSpecialDefense,

              defense: effectiveStats.defense,
              special_defense:
                effectiveStats.specialDefense,

              special_attack: specialAttack,
              speed,

              defense_stage: defenseStage,
              special_defense_stage:
                specialDefenseStage,
              held_item: heldItem,

              score,
            }
          }
        }
      }
    }
  }

  return bestSpread
}