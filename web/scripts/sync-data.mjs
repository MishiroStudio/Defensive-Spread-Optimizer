import { copyFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = dirname(
  fileURLToPath(import.meta.url),
)

const webDirectory = resolve(
  scriptDirectory,
  '..',
)

const projectDirectory = resolve(
  webDirectory,
  '..',
)

const sourceFile = resolve(
  projectDirectory,
  'data',
  'pokemon.json',
)

const destinationDirectory = resolve(
  webDirectory,
  'public',
  'data',
)

const destinationFile = resolve(
  destinationDirectory,
  'pokemon.json',
)

await mkdir(destinationDirectory, {
  recursive: true,
})

await copyFile(
  sourceFile,
  destinationFile,
)

console.log(
  'Pokémon data synchronized.',
)