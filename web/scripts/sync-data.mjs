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

const destinationDirectory = resolve(
  webDirectory,
  'public',
  'data',
)

const dataFiles = [
  'pokemon.json',
  'pokemon_v2.json',
  'moves.json',
  'learnsets.json',
  'abilities.json',
  'regulations.json',
]

await mkdir(destinationDirectory, {
  recursive: true,
})

for (const fileName of dataFiles) {
  await copyFile(
    resolve(projectDirectory, 'data', fileName),
    resolve(destinationDirectory, fileName),
  )
}

console.log(
  `${dataFiles.length} data files synchronized.`,
)
