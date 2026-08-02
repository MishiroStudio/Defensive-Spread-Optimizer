import {
  copyFile,
  mkdir,
  readdir,
  stat,
} from 'node:fs/promises'

import {
  dirname,
  join,
  resolve,
} from 'node:path'

import {
  fileURLToPath,
} from 'node:url'

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

const sourceDirectory = resolve(
  projectDirectory,
  'assets',
  'sprites',
)

const destinationDirectory = resolve(
  webDirectory,
  'public',
  'assets',
  'sprites',
)

async function fileNeedsCopy(
  sourceFile,
  destinationFile,
) {
  try {
    const [
      sourceStats,
      destinationStats,
    ] = await Promise.all([
      stat(sourceFile),
      stat(destinationFile),
    ])

    return (
      sourceStats.size !== destinationStats.size
      || sourceStats.mtimeMs
        > destinationStats.mtimeMs
    )
  } catch {
    return true
  }
}

async function synchronizeDirectory(
  source,
  destination,
) {
  await mkdir(destination, {
    recursive: true,
  })

  const entries = await readdir(source, {
    withFileTypes: true,
  })

  let copiedFiles = 0

  for (const entry of entries) {
    const sourcePath = join(
      source,
      entry.name,
    )

    const destinationPath = join(
      destination,
      entry.name,
    )

    if (entry.isDirectory()) {
      copiedFiles +=
        await synchronizeDirectory(
          sourcePath,
          destinationPath,
        )

      continue
    }

    if (!entry.isFile()) {
      continue
    }

    if (
      await fileNeedsCopy(
        sourcePath,
        destinationPath,
      )
    ) {
      await copyFile(
        sourcePath,
        destinationPath,
      )

      copiedFiles += 1
    }
  }

  return copiedFiles
}

const copiedFiles =
  await synchronizeDirectory(
    sourceDirectory,
    destinationDirectory,
  )

console.log(
  `${copiedFiles} Pokémon sprites synchronized.`,
)