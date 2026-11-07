// build-smoke.mjs — Cordy's Lab PWAs V11
import assert from 'node:assert/strict'
import { readFile, readdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const dist = resolve(import.meta.dirname, '..', 'dist')

const [
  optimizerHtml,
  pokedexHtml,
  teamBuilderHtml,
  speedTrainerHtml,
  optimizerManifest,
  pokedexManifest,
  teamBuilderManifest,
  speedTrainerManifest,
  serviceWorker,
] = await Promise.all([
  readFile(resolve(dist, 'index.html'), 'utf8'),
  readFile(resolve(dist, 'pokedex', 'index.html'), 'utf8'),
  readFile(resolve(dist, 'team-builder', 'index.html'), 'utf8'),
  readFile(resolve(dist, 'speed-trainer', 'index.html'), 'utf8'),
  readFile(resolve(dist, 'manifest.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'pokedex.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'team-builder.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'speed-trainer.webmanifest'), 'utf8').then(JSON.parse),
  readFile(resolve(dist, 'sw.js'), 'utf8'),
])

assert.match(optimizerHtml, /Defensive Spread Optimizer/)
assert.match(pokedexHtml, /Cordy's Lab Pokédex/)
assert.match(teamBuilderHtml, /MISHIRO Team Builder/)
assert.match(speedTrainerHtml, /MISHIRO – Speed Tier Trainer/)
assert.match(optimizerHtml, /manifest\.webmanifest/)
assert.match(pokedexHtml, /pokedex\.webmanifest/)
assert.match(teamBuilderHtml, /team-builder\.webmanifest/)
assert.match(speedTrainerHtml, /speed-trainer\.webmanifest/)
assert.match(optimizerHtml, /optimizer-apple-touch-icon\.png/)
assert.match(pokedexHtml, /pokedex-apple-touch-icon\.png/)
assert.match(teamBuilderHtml, /tb-apple-touch-icon\.png/)
assert.match(speedTrainerHtml, /speed-trainer-apple-touch-icon\.png/)

assert.equal(optimizerManifest.id, '/Defensive-Spread-Optimizer/')
assert.equal(pokedexManifest.id, '/Defensive-Spread-Optimizer/pokedex/')
assert.equal(teamBuilderManifest.id, '/Defensive-Spread-Optimizer/team-builder/')
assert.equal(speedTrainerManifest.id, '/Defensive-Spread-Optimizer/speed-trainer/')
assert.equal(new Set([
  optimizerManifest.id,
  pokedexManifest.id,
  teamBuilderManifest.id,
  speedTrainerManifest.id,
]).size, 4)
assert.equal(optimizerManifest.icons[0].src, 'icons/optimizer-192x192.png')
assert.equal(pokedexManifest.icons[0].src, 'icons/pokedex-192x192.png')
assert.equal(teamBuilderManifest.icons[0].src, 'icons/tb-192x192.png')
assert.equal(speedTrainerManifest.icons[0].src, 'icons/speed-trainer-192x192.png')

for (const icon of [
  'optimizer-apple-touch-icon.png',
  'optimizer-192x192.png',
  'optimizer-512x512.png',
  'pokedex-apple-touch-icon.png',
  'pokedex-192x192.png',
  'pokedex-512x512.png',
  'tb-apple-touch-icon.png',
  'tb-192x192.png',
  'tb-512x512.png',
  'speed-trainer-apple-touch-icon.png',
  'speed-trainer-192x192.png',
  'speed-trainer-512x512.png',
]) {
  await readFile(resolve(dist, 'icons', icon))
}

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
  'usage_stats.json',
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

console.log('Four-PWA production build verified.')
