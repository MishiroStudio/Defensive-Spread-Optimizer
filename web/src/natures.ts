export type NatureStat =
  | 'attack'
  | 'defense'
  | 'special_attack'
  | 'special_defense'
  | 'speed'

export type IncreasedNatureStat =
  | NatureStat
  | 'bulk'

export interface Nature {
  id: string
  name_en: string
  name_de: string
  positive: NatureStat | null
  negative: NatureStat | null
  attack: number
  defense: number
  special_attack: number
  special_defense: number
  speed: number
}

export const NATURES = {
  hardy: {
    id: 'hardy',
    name_en: 'Hardy',
    name_de: 'Robust',
    positive: null,
    negative: null,
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  adamant: {
    id: 'adamant',
    name_en: 'Adamant',
    name_de: 'Hart',
    positive: 'attack',
    negative: 'special_attack',
    attack: 1.1,
    defense: 1.0,
    special_attack: 0.9,
    special_defense: 1.0,
    speed: 1.0,
  },

  brave: {
    id: 'brave',
    name_en: 'Brave',
    name_de: 'Mutig',
    positive: 'attack',
    negative: 'speed',
    attack: 1.1,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 0.9,
  },

  modest: {
    id: 'modest',
    name_en: 'Modest',
    name_de: 'Mäßig',
    positive: 'special_attack',
    negative: 'attack',
    attack: 0.9,
    defense: 1.0,
    special_attack: 1.1,
    special_defense: 1.0,
    speed: 1.0,
  },

  quiet: {
    id: 'quiet',
    name_en: 'Quiet',
    name_de: 'Ruhig',
    positive: 'special_attack',
    negative: 'speed',
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.1,
    special_defense: 1.0,
    speed: 0.9,
  },

  jolly: {
    id: 'jolly',
    name_en: 'Jolly',
    name_de: 'Froh',
    positive: 'speed',
    negative: 'special_attack',
    attack: 1.0,
    defense: 1.0,
    special_attack: 0.9,
    special_defense: 1.0,
    speed: 1.1,
  },

  timid: {
    id: 'timid',
    name_en: 'Timid',
    name_de: 'Scheu',
    positive: 'speed',
    negative: 'attack',
    attack: 0.9,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.1,
  },

  bold: {
    id: 'bold',
    name_en: 'Bold',
    name_de: 'Kühn',
    positive: 'defense',
    negative: 'attack',
    attack: 0.9,
    defense: 1.1,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  calm: {
    id: 'calm',
    name_en: 'Calm',
    name_de: 'Still',
    positive: 'special_defense',
    negative: 'attack',
    attack: 0.9,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.1,
    speed: 1.0,
  },

  relaxed: {
    id: 'relaxed',
    name_en: 'Relaxed',
    name_de: 'Locker',
    positive: 'defense',
    negative: 'speed',
    attack: 1.0,
    defense: 1.1,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 0.9,
  },

  sassy: {
    id: 'sassy',
    name_en: 'Sassy',
    name_de: 'Forsch',
    positive: 'special_defense',
    negative: 'speed',
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.1,
    speed: 0.9,
  },

  impish: {
    id: 'impish',
    name_en: 'Impish',
    name_de: 'Pfiffig',
    positive: 'defense',
    negative: 'special_attack',
    attack: 1.0,
    defense: 1.1,
    special_attack: 0.9,
    special_defense: 1.0,
    speed: 1.0,
  },

  careful: {
    id: 'careful',
    name_en: 'Careful',
    name_de: 'Sacht',
    positive: 'special_defense',
    negative: 'special_attack',
    attack: 1.0,
    defense: 1.0,
    special_attack: 0.9,
    special_defense: 1.1,
    speed: 1.0,
  },

      lonely: {
    id: 'lonely',
    name_en: 'Lonely',
    name_de: 'Solo',
    positive: 'attack',
    negative: 'defense',
    attack: 1.1,
    defense: 0.9,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  naughty: {
    id: 'naughty',
    name_en: 'Naughty',
    name_de: 'Frech',
    positive: 'attack',
    negative: 'special_defense',
    attack: 1.1,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 0.9,
    speed: 1.0,
  },

  docile: {
    id: 'docile',
    name_en: 'Docile',
    name_de: 'Sanft',
    positive: null,
    negative: null,
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  lax: {
    id: 'lax',
    name_en: 'Lax',
    name_de: 'Lasch',
    positive: 'defense',
    negative: 'special_defense',
    attack: 1.0,
    defense: 1.1,
    special_attack: 1.0,
    special_defense: 0.9,
    speed: 1.0,
  },

  hasty: {
    id: 'hasty',
    name_en: 'Hasty',
    name_de: 'Hastig',
    positive: 'speed',
    negative: 'defense',
    attack: 1.0,
    defense: 0.9,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.1,
  },

  serious: {
    id: 'serious',
    name_en: 'Serious',
    name_de: 'Ernst',
    positive: null,
    negative: null,
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  naive: {
    id: 'naive',
    name_en: 'Naive',
    name_de: 'Naiv',
    positive: 'speed',
    negative: 'special_defense',
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 0.9,
    speed: 1.1,
  },

  mild: {
    id: 'mild',
    name_en: 'Mild',
    name_de: 'Mild',
    positive: 'special_attack',
    negative: 'defense',
    attack: 1.0,
    defense: 0.9,
    special_attack: 1.1,
    special_defense: 1.0,
    speed: 1.0,
  },

  bashful: {
    id: 'bashful',
    name_en: 'Bashful',
    name_de: 'Zaghaft',
    positive: null,
    negative: null,
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },

  rash: {
    id: 'rash',
    name_en: 'Rash',
    name_de: 'Hitzig',
    positive: 'special_attack',
    negative: 'special_defense',
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.1,
    special_defense: 0.9,
    speed: 1.0,
  },

  gentle: {
    id: 'gentle',
    name_en: 'Gentle',
    name_de: 'Zart',
    positive: 'special_defense',
    negative: 'defense',
    attack: 1.0,
    defense: 0.9,
    special_attack: 1.0,
    special_defense: 1.1,
    speed: 1.0,
  },

  quirky: {
    id: 'quirky',
    name_en: 'Quirky',
    name_de: 'Kauzig',
    positive: null,
    negative: null,
    attack: 1.0,
    defense: 1.0,
    special_attack: 1.0,
    special_defense: 1.0,
    speed: 1.0,
  },
} satisfies Record<string, Nature>

export type NatureId = keyof typeof NATURES

export function getNaturesByStatChanges(
  increasedStat: string,
  decreasedStat: string,
): Partial<Record<NatureId, Nature>> {
  const normalizedIncreasedStat =
    increasedStat.toLowerCase().trim()

  const normalizedDecreasedStat =
    decreasedStat.toLowerCase().trim()

  const possibleNatures:
    Partial<Record<NatureId, Nature>> = {}

  const entries = Object.entries(NATURES) as [
    NatureId,
    Nature,
  ][]

  for (const [natureId, nature] of entries) {
    const positiveStat = nature.positive
    const negativeStat = nature.negative

    const positiveMatches =
      normalizedIncreasedStat === 'bulk'
        ? positiveStat === 'defense'
          || positiveStat === 'special_defense'
        : positiveStat === normalizedIncreasedStat

    const negativeMatches =
      negativeStat === normalizedDecreasedStat

    if (positiveMatches && negativeMatches) {
      possibleNatures[natureId] = nature
    }
  }

  return possibleNatures
}