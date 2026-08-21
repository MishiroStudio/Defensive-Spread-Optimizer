export function calculateHp(
  baseHp: number,
  statPoints: number,
): number {
  const level50Hp =
    Math.floor((2 * baseHp + 31) / 2) + 60

  return level50Hp + statPoints
}

export function calculateOtherStat(
  baseStat: number,
  statPoints: number,
  nature = 1.0,
): number {
  const level50Stat =
    Math.floor((2 * baseStat + 31) / 2) + 5

  const statWithPoints =
    level50Stat + statPoints

  return Math.floor(
    statWithPoints * nature,
  )
}

export function calculateAttack(
  baseAttack: number,
  statPoints: number,
  nature = 1.0,
): number {
  return calculateOtherStat(
    baseAttack,
    statPoints,
    nature,
  )
}

export function calculateDefense(
  baseDefense: number,
  statPoints: number,
  nature = 1.0,
): number {
  return calculateOtherStat(
    baseDefense,
    statPoints,
    nature,
  )
}

export function calculateSpecialAttack(
  baseSpecialAttack: number,
  statPoints: number,
  nature = 1.0,
): number {
  return calculateOtherStat(
    baseSpecialAttack,
    statPoints,
    nature,
  )
}

export function calculateSpecialDefense(
  baseSpecialDefense: number,
  statPoints: number,
  nature = 1.0,
): number {
  return calculateOtherStat(
    baseSpecialDefense,
    statPoints,
    nature,
  )
}

export function calculateSpeed(
  baseSpeed: number,
  statPoints: number,
  nature = 1.0,
): number {
  return calculateOtherStat(
    baseSpeed,
    statPoints,
    nature,
  )
}