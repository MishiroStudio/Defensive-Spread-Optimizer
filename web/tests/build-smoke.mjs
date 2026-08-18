import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const dist = resolve(import.meta.dirname, '..', 'dist')

const [
  optimizerHtml,
  pokedexHtml,
  optimizerManifest,
  pokedexManifest,
  serviceWorker,
] = await Promise.all([
  readFile(resolve(dist, 'index.html'), 'utf8'),
  readFile(resolve(dist, 'pokedex', 'index.html'), 'utf8'),
  readFile(resolve(dist, 'manifest.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'pokedex.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'sw.js'), 'utf8'),
])

assert.match(optimizerHtml, /Defensive Spread Optimizer/)
assert.match(pokedexHtml, /Cordy's Lab Pokédex/)
assert.match(optimizerHtml, /manifest\.webmanifest/)
assert.match(pokedexHtml, /pokedex\.webmanifest/)

assert.equal(optimizerManifest.id, '/Defensive-Spread-Optimizer/')
assert.equal(pokedexManifest.id, '/Defensive-Spread-Optimizer/pokedex/')
assert.notEqual(optimizerManifest.id, pokedexManifest.id)

const listSprites = await readdir(
  resolve(dist, 'assets', 'sprites', 'list', 'normal'),
)
assert.equal(listSprites.filter((name) => name.endsWith('.png')).length, 1271)

const precachedListSprites = new Set(
  serviceWorker.match(/assets\/sprites\/list\/normal\/[^"']+?\.png/g) ?? [],
)
assert.equal(precachedListSprites.size, 1271)

for (const fileName of [
  'pokemon_v2.json',
  'moves.json',
  'learnsets.json',
  'abilities.json',
  'regulations.json',
]) {
  await readFile(resolve(dist, 'data', fileName))
}

for (const fileName of [
  'PhysicalIC_CP.png',
  'SpecialIC_CP.png',
  'StatusIC_CP.png',
]) {
  await readFile(resolve(dist, 'assets', 'move-categories', fileName))
}

console.log('Two-PWA production build verified.')
