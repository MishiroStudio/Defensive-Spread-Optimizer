import {
  normalizeMember,
  persistedMember,
  type TeamFolder,
  type TeamLibraryDocument,
  type TeamSnapshot,
} from "./team-builder-data";

export const TEAM_LIBRARY_KEY = "mishiro-team-builder-library-v1";

function identifier(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function emptyTeamLibrary(defaultFolderName: string): TeamLibraryDocument {
  return {
    schema_version: 1,
    folders: [{ id: identifier(), name: defaultFolderName, teams: [] }],
  };
}

export function normalizeSnapshot(value: unknown): TeamSnapshot | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Partial<TeamSnapshot>;
  if (!String(raw.name ?? "").trim()) return null;
  const active = Array.isArray(raw.active_slots)
    ? raw.active_slots.slice(0, 6).map(normalizeMember)
    : [];
  while (active.length < 6) active.push(null);
  const bench = Array.isArray(raw.bench)
    ? raw.bench.map(normalizeMember).filter((member) => member !== null)
    : [];
  return {
    ...(raw.id ? { id: String(raw.id) } : {}),
    name: String(raw.name).trim(),
    regulation_id: String(raw.regulation_id || "national_dex"),
    active_slots: active,
    bench,
  };
}

export function normalizeTeamLibrary(value: unknown, defaultFolderName: string): TeamLibraryDocument {
  if (!value || typeof value !== "object" || Array.isArray(value)) return emptyTeamLibrary(defaultFolderName);
  const rawFolders = (value as { folders?: unknown }).folders;
  if (!Array.isArray(rawFolders)) return emptyTeamLibrary(defaultFolderName);
  const folders: TeamFolder[] = rawFolders.flatMap((entry) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) return [];
    const raw = entry as Partial<TeamFolder>;
    const name = String(raw.name ?? "").trim();
    if (!name) return [];
    return [{
      id: String(raw.id || identifier()),
      name,
      teams: Array.isArray(raw.teams)
        ? raw.teams.map(normalizeSnapshot).filter((team) => team !== null)
        : [],
    }];
  });
  return folders.length ? { schema_version: 1, folders } : emptyTeamLibrary(defaultFolderName);
}

export function loadTeamLibrary(storage: Pick<Storage, "getItem">, defaultFolderName: string): TeamLibraryDocument {
  const serialized = storage.getItem(TEAM_LIBRARY_KEY);
  if (!serialized) return emptyTeamLibrary(defaultFolderName);
  try {
    return normalizeTeamLibrary(JSON.parse(serialized), defaultFolderName);
  } catch {
    return emptyTeamLibrary(defaultFolderName);
  }
}

export function saveTeamLibrary(storage: Pick<Storage, "setItem">, document: TeamLibraryDocument): void {
  storage.setItem(TEAM_LIBRARY_KEY, JSON.stringify(document));
}

export function createFolder(document: TeamLibraryDocument, name: string): [TeamLibraryDocument, string] {
  const id = identifier();
  return [{ ...document, folders: [...document.folders, { id, name: name.trim(), teams: [] }] }, id];
}

export function renameFolder(document: TeamLibraryDocument, folderId: string, name: string): TeamLibraryDocument {
  return {
    ...document,
    folders: document.folders.map((folder) => folder.id === folderId ? { ...folder, name: name.trim() } : folder),
  };
}

export function deleteFolder(document: TeamLibraryDocument, folderId: string, defaultFolderName: string): TeamLibraryDocument {
  const folders = document.folders.filter((folder) => folder.id !== folderId);
  return folders.length ? { ...document, folders } : emptyTeamLibrary(defaultFolderName);
}

export function upsertTeam(
  document: TeamLibraryDocument,
  folderId: string,
  snapshot: TeamSnapshot,
  preferredTeamId?: string,
): [TeamLibraryDocument, string] {
  let teamId = preferredTeamId;
  const folders = document.folders.map((folder) => {
    if (folder.id !== folderId) return folder;
    const normalized = snapshot.name.trim().toLocaleLowerCase();
    const existingIndex = folder.teams.findIndex((team) => (
      (preferredTeamId && team.id === preferredTeamId)
      || team.name.trim().toLocaleLowerCase() === normalized
    ));
    teamId = existingIndex >= 0 ? folder.teams[existingIndex].id : identifier();
    const stored: TeamSnapshot = {
      ...snapshot,
      id: teamId,
      active_slots: snapshot.active_slots.map(persistedMember),
      bench: snapshot.bench.map((member) => persistedMember(member)!),
    };
    const teams = [...folder.teams];
    if (existingIndex >= 0) teams[existingIndex] = stored;
    else teams.push(stored);
    teams.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
    return { ...folder, teams };
  });
  if (!teamId) throw new Error("Der ausgewählte Ordner existiert nicht mehr.");
  return [{ ...document, folders }, teamId];
}

export function deleteTeam(document: TeamLibraryDocument, folderId: string, teamId: string): TeamLibraryDocument {
  return {
    ...document,
    folders: document.folders.map((folder) => folder.id === folderId
      ? { ...folder, teams: folder.teams.filter((team) => team.id !== teamId) }
      : folder),
  };
}

