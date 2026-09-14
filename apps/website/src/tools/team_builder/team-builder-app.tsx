import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

import {
  STAT_NAMES,
  STAT_ORDER,
  localizedName,
  type MoveCategory,
  type MoveRubric,
  type PokemonForm,
} from "../pokedex/pokedex-data";
import { publicPath } from "../pokedex/public-path";
import {
  Dropdown,
  ItemPicker,
  MoveFilters,
  MovePicker,
  PokemonSearch,
  StatsEditor,
  TypeChip,
  TypeIcon,
  Chevron,
  type SelectOption,
} from "./team-builder-controls";
import {
  TeamBuilderData,
  loadTeamBuilderBundle,
  normalizeMember,
  persistedMember,
  type Language,
  type TeamLibraryDocument,
  type TeamMember,
  type TeamSnapshot,
} from "./team-builder-data";
import {
  exportPokepaste,
  fetchPokepaste,
  parsePasteId,
  parsePokepaste,
  submitPokepaste,
} from "./team-builder-pokepaste";
import {
  createFolder,
  deleteFolder,
  deleteTeam,
  loadTeamLibrary,
  renameFolder,
  saveTeamLibrary,
  upsertTeam,
} from "./team-builder-storage";
import { moveRosterMember, type RosterPosition } from "./team-builder-roster";

const LANGUAGE_KEY = "mishiro-team-builder-language";
const EMPTY_TEAM = (): Array<TeamMember | null> => Array.from({ length: 6 }, () => null);

const COPY = {
  de: {
    subtitle: "The Team Builder for VGC Players",
    switchPrompt: "Switch to",
    switchLanguage: "English",
    teamName: "Teamname",
    regulation: "Regulation",
    manage: "Team verwalten",
    folder: "Ordner",
    savedTeam: "Gespeichertes Team",
    createFolder: "Ordner erstellen",
    renameFolder: "Ordner umbenennen",
    deleteFolder: "Ordner löschen",
    saveTeam: "Team speichern",
    loadTeam: "Team laden",
    deleteTeam: "Team löschen",
    team: "Team",
    bench: "Ersatzbank",
    resetTeam: "Team zurücksetzen",
    resetBench: "Ersatzbank zurücksetzen",
    addPokemon: "Pokémon hinzufügen",
    changePokemon: "Pokémon ändern",
    removePokemon: "Pokémon löschen",
    savePokemon: "Sichern",
    abilities: "Fähigkeit",
    item: "Item",
    moves: "Attacken",
    stats: "Statuswerte",
    upload: "Zu PokéPaste hochladen",
    import: "Von PokéPaste importieren",
    loading: "Team Builder wird geladen …",
    loadError: "Der Team Builder konnte nicht geladen werden.",
    previousRegulations: "Frühere Regulationen",
    defaultFolder: "Meine Teams",
  },
  en: {
    subtitle: "The Team Builder for VGC Players",
    switchPrompt: "Wechsel zu",
    switchLanguage: "Deutsch",
    teamName: "Team name",
    regulation: "Regulation",
    manage: "Manage teams",
    folder: "Folder",
    savedTeam: "Saved team",
    createFolder: "Create folder",
    renameFolder: "Rename folder",
    deleteFolder: "Delete folder",
    saveTeam: "Save team",
    loadTeam: "Load team",
    deleteTeam: "Delete team",
    team: "Team",
    bench: "Bench",
    resetTeam: "Reset team",
    resetBench: "Reset bench",
    addPokemon: "Add Pokémon",
    changePokemon: "Change Pokémon",
    removePokemon: "Remove Pokémon",
    savePokemon: "Save",
    abilities: "Ability",
    item: "Item",
    moves: "Moves",
    stats: "Stats",
    upload: "Upload to PokéPaste",
    import: "Import from PokéPaste",
    loading: "Loading Team Builder …",
    loadError: "The Team Builder could not be loaded.",
    previousRegulations: "Previous regulations",
    defaultFolder: "My teams",
  },
} as const;

type RosterLocation = RosterPosition;

function sameLocation(left: RosterLocation | null, right: RosterLocation): boolean {
  return left?.area === right.area && left.index === right.index;
}

function copyMember(member: TeamMember): TeamMember {
  return normalizeMember(member)!;
}

function AppHeader({ language, onToggle }: { language: Language; onToggle: () => void }) {
  const text = COPY[language];
  return (
    <header className="app-header team-builder-header">
      <div className="brand-block">
        <p className="eyebrow">MISHIRO</p>
        <h1>Team Builder</h1>
        <p className="description">{text.subtitle}</p>
      </div>
      <div className="language-control">
        <span>{text.switchPrompt}</span>
        <button type="button" onClick={onToggle}>{text.switchLanguage}</button>
      </div>
    </header>
  );
}

function SectionHeader({ title, action }: { title: string; action: ReactNode }) {
  return <div className="roster-heading"><h2>{title}</h2>{action}</div>;
}

function CompactStatBars({
  member,
  data,
  regulationId,
  language,
}: {
  member: TeamMember;
  data: TeamBuilderData;
  regulationId: string;
  language: Language;
}) {
  const current = data.calculatedStats(member);
  const uninvested = data.calculatedStats(member, false);
  const maximum = data.maximumStats(regulationId);
  return (
    <div className="compact-stat-bars">
      {STAT_ORDER.map((stat) => {
        const ratio = current[stat] / Math.max(1, maximum[stat]);
        const baseRatio = uninvested[stat] / Math.max(1, maximum[stat]);
        const tone = ratio < 0.25 ? "low" : ratio <= 0.75 ? "middle" : "high";
        return (
          <div className="compact-stat-row" key={stat} title={`${STAT_NAMES[language][stat]}: ${current[stat]} / ${maximum[stat]}`}>
            <span>{STAT_NAMES[language][stat]}</span>
            <span className="stat-bar-track">
              <span className={`stat-bar-base ${tone}`} style={{ width: `${Math.min(100, baseRatio * 100)}%` }} />
              <span
                className={`stat-bar-invested ${tone}`}
                style={{ left: `${Math.min(100, baseRatio * 100)}%`, width: `${Math.max(0, Math.min(1, ratio) - baseRatio) * 100}%` }}
              />
            </span>
            <strong>{current[stat]}</strong>
          </div>
        );
      })}
    </div>
  );
}

function CompactMemberCard({
  member,
  location,
  data,
  regulationId,
  language,
  dragging,
  dropTarget,
  onEdit,
  onRemove,
  onDragStart,
  onDragEnd,
  onDrop,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
}: {
  member: TeamMember;
  location: RosterLocation;
  data: TeamBuilderData;
  regulationId: string;
  language: Language;
  dragging: boolean;
  dropTarget: boolean;
  onEdit: () => void;
  onRemove: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDrop: () => void;
  onTouchStart: (event: ReactPointerEvent<HTMLElement>) => void;
  onTouchMove: (event: ReactPointerEvent<HTMLElement>) => void;
  onTouchEnd: (event: ReactPointerEvent<HTMLElement>) => void;
}) {
  const form = data.form(member);
  const displayForm = data.compactDisplayForm(member);
  const ability = form.abilities.find((entry) => entry.api_name === member.ability_id);
  const item = member.item_id ? data.itemsByName.get(member.item_id) : undefined;
  const moves = [...member.move_ids.slice(0, 4)];
  while (moves.length < 4) moves.push("");
  return (
    <article
      className={`compact-member-card${dragging ? " dragging" : ""}${dropTarget ? " drop-target" : ""}`}
      draggable
      data-drop-area={location.area}
      data-drop-index={location.index}
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", `${location.area}:${location.index}`);
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }}
      onDrop={(event) => { event.preventDefault(); onDrop(); }}
      onPointerDown={onTouchStart}
      onPointerMove={onTouchMove}
      onPointerUp={onTouchEnd}
      onPointerCancel={onTouchEnd}
      onClick={onEdit}
    >
      <button
        type="button"
        className="member-delete-button"
        aria-label={COPY[language].removePokemon}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => { event.stopPropagation(); onRemove(); }}
      >×</button>
      <div className="compact-identity">
        <div className="compact-sprite-wrap">
          <img
            className="compact-pokemon-sprite"
            src={publicPath(displayForm.sprites.home ?? `assets/sprites/list/normal/${displayForm.api_name}.png`)}
            alt=""
            width="62"
            height="62"
            onError={(event) => {
              event.currentTarget.src = publicPath("assets/sprites/missingno.png");
            }}
          />

          {item && (
            <span className="compact-item-overlay" aria-hidden="true">
              <img
                className="compact-item-sprite"
                src={publicPath(`assets/items/${item.api_name}.png`)}
                alt=""
                width="24"
                height="24"
                onLoad={(event) => {
                  event.currentTarget.hidden = false;

                  const fallback =
                    event.currentTarget.nextElementSibling as HTMLElement | null;

                  if (fallback) fallback.hidden = true;
                }}
                onError={(event) => {
                  event.currentTarget.hidden = true;

                  const fallback =
                    event.currentTarget.nextElementSibling as HTMLElement | null;

                  if (fallback) fallback.hidden = false;
                }}
              />

              <span className="item-dot compact-item-fallback" hidden />
            </span>
          )}
        </div>

        <div className="compact-type-icons">
          {displayForm.types.map((type) => (
            <TypeIcon type={type} size={20} key={type} />
          ))}
        </div>
      </div>
      <div className="compact-set">
        <h3>{localizedName(displayForm, language)}</h3>
        <div className="compact-meta-grid">
          <span>{ability ? localizedName(ability, language) : "—"}</span>
          <span>{item ? localizedName(item, language) : "—"}</span>
          <small>{data.natureSummary(member, language, STAT_NAMES[language])}</small>
        </div>
        <div className="compact-moves">
          {moves.map((moveId, index) => <span key={`${moveId}-${index}`}>{moveId ? localizedName(data.movesByName.get(moveId) ?? { api_name: moveId }, language) : "—"}</span>)}
        </div>
      </div>
      <CompactStatBars member={member} data={data} regulationId={regulationId} language={language} />
    </article>
  );
}

function EmptySlot({
  location,
  language,
  dropTarget,
  onClick,
  onDrop,
}: {
  location: RosterLocation;
  language: Language;
  dropTarget: boolean;
  onClick: () => void;
  onDrop: () => void;
}) {
  return (
    <button
      type="button"
      className={`empty-team-slot${dropTarget ? " drop-target" : ""}`}
      data-drop-area={location.area}
      data-drop-index={location.index}
      onClick={onClick}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); onDrop(); }}
    >
      <span>＋</span>{COPY[language].addPokemon}
    </button>
  );
}

function MemberEditor({
  member,
  data,
  regulationId,
  language,
  onChange,
  onSave,
  onRemove,
}: {
  member: TeamMember;
  data: TeamBuilderData;
  regulationId: string;
  language: Language;
  onChange: (member: TeamMember) => void;
  onSave: () => void;
  onRemove: () => void;
}) {
  const text = COPY[language];
  const form = data.form(member);
  const forms = data.relatedForms(member, regulationId);
  const [moveCategory, setMoveCategory] = useState<MoveCategory | "">("");
  const [moveRubric, setMoveRubric] = useState<MoveRubric | "">("");
  const selectAbility = (abilityId: string) => onChange({
    ...member,
    ability_id: abilityId,
    ability_ids_by_form: { ...(member.ability_ids_by_form ?? {}), [member.pokemon_id]: abilityId },
  });
  const changeMove = (index: number, moveId: string | null) => {
    const slots: Array<string | null> = [...member.move_ids.slice(0, 4)];
    while (slots.length < 4) slots.push(null);
    slots[index] = moveId;
    onChange({ ...member, move_ids: slots.map((value) => value ?? "") });
  };
  return (
    <article className="member-editor-card">
      <button
          type="button"
          className="editor-delete-button"
          aria-label={text.removePokemon}
          onClick={onRemove}
        >
          ×
        </button>
        <div className="editor-identity">
        <img
          className="editor-pokemon-sprite"
          src={publicPath(form.sprites.home ?? `assets/sprites/home/normal/${form.api_name}.png`)}
          alt=""
          width="118"
          height="118"
          onError={(event) => { event.currentTarget.src = publicPath("assets/sprites/missingno.png"); }}
        />
        <div className="editor-name-block">
          <h2>{localizedName(form, language)}</h2>
          <p>{localizedName(form, language === "de" ? "en" : "de")}</p>
          {forms.length > 1 && (
            <div className="form-links" aria-label={language === "de" ? "Formen" : "Forms"}>
              {forms.map((option) => (
                <button
                  type="button"
                  className={option.pokemon_id === form.pokemon_id ? "active" : ""}
                  key={option.pokemon_id}
                  onClick={() => onChange(data.switchForm(member, option.pokemon_id, regulationId))}
                >
                  {localizedName(option, language)}
                </button>
              ))}
            </div>
          )}
          <div className="editor-type-chips">{form.types.map((type) => <TypeChip type={type} language={language} key={type} />)}</div>
        </div>
      </div>

      <section className="editor-section ability-section">
        <h3>{text.abilities}</h3>
        <div className="ability-options">
          {form.abilities.map((ability) => (
            <button
              type="button"
              className={member.ability_id === ability.api_name ? "selected" : ""}
              key={ability.api_name}
              onClick={() => selectAbility(ability.api_name)}
            >
              {localizedName(ability, language)}
            </button>
          ))}
        </div>
        {member.ability_id && <p className="effect-description">{data.abilityDescription(member.ability_id, language)}</p>}
      </section>

      <section className="editor-section">
        <h3>{text.item}</h3>
        <ItemPicker
          key={`${form.pokemon_id}-${language}`}
          data={data}
          member={member}
          regulationId={regulationId}
          language={language}
          itemId={member.item_id}
          onChange={(itemId) => onChange({ ...member, item_id: itemId })}
        />
      </section>

      <section className="editor-section move-editor-section">
        <h3>{text.moves}</h3>
        <MoveFilters
          language={language}
          category={moveCategory}
          rubric={moveRubric}
          onCategory={setMoveCategory}
          onRubric={setMoveRubric}
        />
        <div className="selected-move-header">
          <span />
          <span>{language === "de" ? "Attacke" : "Move"}</span>
          <span>{language === "de" ? "Kat." : "Cat."}</span>
          <span>{language === "de" ? "Stärke" : "Power"}</span>
          <span>{language === "de" ? "Gen." : "Acc."}</span>
          <span>AP</span>
          <span />
        </div>
        {Array.from({ length: 4 }, (_, index) => (
          <MovePicker
            key={`${form.pokemon_id}-${language}-${index}`}
            data={data}
            member={member}
            language={language}
            category={moveCategory}
            rubric={moveRubric}
            moveId={member.move_ids[index] ?? null}
            excludedMoveIds={member.move_ids.filter((moveId, moveIndex) => moveIndex !== index && Boolean(moveId))}
            onChange={(moveId) => changeMove(index, moveId)}
            number={index + 1}
          />
        ))}
      </section>

      <section className="editor-section">
        <h3>{text.stats}</h3>
        <StatsEditor data={data} member={member} language={language} onChange={onChange} />
      </section>

      <div className="editor-actions">
        <button
          type="button"
          className="primary-button"
          onClick={onSave}
        >
          {text.savePokemon}
        </button>
      </div>
    </article>

  );
}

function TeamLibrary({
  language,
  library,
  selectedFolderId,
  selectedTeamId,
  onFolder,
  onTeam,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onSaveTeam,
  onLoadTeam,
  onDeleteTeam,
}: {
  language: Language;
  library: TeamLibraryDocument;
  selectedFolderId: string;
  selectedTeamId: string;
  onFolder: (id: string) => void;
  onTeam: (id: string) => void;
  onCreateFolder: () => void;
  onRenameFolder: () => void;
  onDeleteFolder: () => void;
  onSaveTeam: () => void;
  onLoadTeam: () => void;
  onDeleteTeam: () => void;
}) {
  const text = COPY[language];
  const [expanded, setExpanded] = useState(false);
  const folder = library.folders.find((entry) => entry.id === selectedFolderId) ?? library.folders[0];
  const folderOptions = library.folders.map((entry) => ({ value: entry.id, label: entry.name }));
  const teamOptions: SelectOption<string>[] = [
    { value: "", label: language === "de" ? "Team auswählen" : "Choose team" },
    ...(folder?.teams ?? []).map((team) => ({ value: team.id ?? "", label: team.name })),
  ];
  return (
    <section className={`team-library-panel${expanded ? " expanded" : ""}`}>
      <button type="button" className="team-library-toggle" aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>
        <span>{text.manage}</span><Chevron open={expanded} />
      </button>
      {expanded && (
        <div className="team-library-content">
          <div className="team-library-field">
            <span>{text.folder}</span>
            <Dropdown
              value={folder?.id ?? ""}
              options={folderOptions}
              onChange={onFolder}
              label={text.folder}
            />
          </div>
          <div className="library-actions triple">
            <button type="button" onClick={onCreateFolder}>{text.createFolder}</button>
            <button type="button" onClick={onRenameFolder}>{text.renameFolder}</button>
            <button type="button" className="danger-button" onClick={onDeleteFolder}>{text.deleteFolder}</button>
          </div>
          <div className="team-library-field">
            <span>{text.savedTeam}</span>
            <Dropdown
              value={selectedTeamId}
              options={teamOptions}
              onChange={onTeam}
              label={text.savedTeam}
              disabled={!folder?.teams.length}
            />
          </div>
          <div className="library-actions triple">
            <button type="button" className="primary-button" onClick={onSaveTeam}>{text.saveTeam}</button>
            <button type="button" onClick={onLoadTeam} disabled={!selectedTeamId}>{text.loadTeam}</button>
            <button type="button" className="danger-button" onClick={onDeleteTeam} disabled={!selectedTeamId}>{text.deleteTeam}</button>
          </div>
        </div>
      )}
    </section>
  );
}

function PasteImportDialog({
  language,
  busy,
  onClose,
  onImport,
}: {
  language: Language;
  busy: boolean;
  onClose: () => void;
  onImport: (value: string) => void;
}) {
  const [value, setValue] = useState("");
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="paste-dialog" role="dialog" aria-modal="true" aria-labelledby="paste-title">
        <button type="button" className="modal-close" onClick={onClose} aria-label={language === "de" ? "Schließen" : "Close"}>×</button>
        <h2 id="paste-title">{COPY[language].import}</h2>
        <p>{language === "de" ? "PokéPaste-Link, Paste-ID oder vollständigen Teamtext einfügen." : "Paste a PokéPaste link, paste ID, or complete team text."}</p>
        <textarea autoFocus value={value} onChange={(event) => setValue(event.target.value)} placeholder="https://pokepast.es/…" rows={10} />
        <div className="modal-actions"><button type="button" onClick={onClose}>{language === "de" ? "Abbrechen" : "Cancel"}</button><button type="button" className="primary-button" disabled={busy || !value.trim()} onClick={() => onImport(value)}>{busy ? (language === "de" ? "Wird importiert …" : "Importing …") : COPY[language].import}</button></div>
      </section>
    </div>
  );
}

export default function TeamBuilderApp() {
  const [data, setData] = useState<TeamBuilderData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [language, setLanguage] = useState<Language>(() => window.localStorage.getItem(LANGUAGE_KEY) === "en" ? "en" : "de");
  const [regulationId, setRegulationId] = useState("");
  const [teamName, setTeamName] = useState("");
  const [team, setTeam] = useState<Array<TeamMember | null>>(EMPTY_TEAM);
  const [bench, setBench] = useState<TeamMember[]>([]);
  const [editor, setEditor] = useState<RosterLocation | null>(null);
  const [draft, setDraft] = useState<TeamMember | null>(null);
  const [dragSource, setDragSource] = useState<RosterLocation | null>(null);
  const [dropTarget, setDropTarget] = useState<RosterLocation | null>(null);
  const [feedback, setFeedback] = useState("");
  const [pasteDialog, setPasteDialog] = useState(false);
  const [pasteBusy, setPasteBusy] = useState(false);
  const [library, setLibrary] = useState<TeamLibraryDocument>(() => loadTeamLibrary(window.localStorage, COPY[language].defaultFolder));
  const [selectedFolderId, setSelectedFolderId] = useState(() => library.folders[0].id);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [loadedTeamId, setLoadedTeamId] = useState<string | undefined>();
  const feedbackTimer = useRef<number | null>(null);
  const suppressCardClick = useRef(false);
  const dragSourceRef = useRef<RosterLocation | null>(null);
  const touchDrag = useRef<{
    source: RosterLocation;
    target: RosterLocation | null;
    timer: number;
    active: boolean;
    startX: number;
    startY: number;
  } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void loadTeamBuilderBundle(controller.signal)
      .then((bundle) => {
        const next = new TeamBuilderData(bundle);
        setData(next);
        setRegulationId(next.currentRegulationId);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLoadError(error instanceof Error ? error.message : COPY.de.loadError);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem(LANGUAGE_KEY, language);
  }, [language]);

  useEffect(() => saveTeamLibrary(window.localStorage, library), [library]);

  useEffect(() => () => {
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current);
    if (touchDrag.current) window.clearTimeout(touchDrag.current.timer);
  }, []);

  const notify = (message: string) => {
    setFeedback(message);
    if (feedbackTimer.current !== null) window.clearTimeout(feedbackTimer.current);
    feedbackTimer.current = window.setTimeout(() => setFeedback(""), 6000);
  };

  const selectedFolder = library.folders.find((folder) => folder.id === selectedFolderId) ?? library.folders[0];
  const selectedSavedTeam = selectedFolder?.teams.find((saved) => saved.id === selectedTeamId);

  const openEditor = (location: RosterLocation) => {
    if (suppressCardClick.current) return;
    const member = location.area === "team" ? team[location.index] : bench[location.index];
    setEditor(location);
    setDraft(member ? copyMember(member) : null);
  };

  const choosePokemon = (form: PokemonForm) => {
    if (!data) return;
    const member = data.newMember(form);
    const megaStone = data.megaStoneForSelectedForm(member, regulationId);
    if (megaStone) member.item_id = megaStone.api_name;
    setDraft(member);
  };

  const saveDraft = () => {
    if (!editor || !draft) return;
    const saved = copyMember(draft);
    if (editor.area === "team") {
      setTeam((current) => current.map((member, index) => index === editor.index ? saved : member));
    } else {
      setBench((current) => editor.index === current.length
        ? [...current, saved]
        : current.map((member, index) => index === editor.index ? saved : member));
    }
    setEditor(null);
    setDraft(null);
  };

  const removeAt = (location: RosterLocation, confirmRemoval = true) => {
    if (confirmRemoval) {
      const member = location.area === "team" ? team[location.index] : bench[location.index];
      if (member && data && !window.confirm(`${COPY[language].removePokemon}: ${localizedName(data.compactDisplayForm(member), language)}?`)) return;
    }
    if (location.area === "team") setTeam((current) => current.map((member, index) => index === location.index ? null : member));
    else setBench((current) => current.filter((_, index) => index !== location.index));
    setEditor(null);
    setDraft(null);
  };

  const moveMember = (source: RosterLocation, target: RosterLocation) => {
    const next = moveRosterMember(team, bench, source, target);
    setTeam(next.team);
    setBench(next.bench);
  };

  const drop = (target: RosterLocation) => {
    const source = dragSourceRef.current ?? dragSource;

    if (source) {
      moveMember(source, target);
    }

    dragSourceRef.current = null;
    setDragSource(null);
    setDropTarget(null);
  };

  const beginTouchDrag = (source: RosterLocation, event: ReactPointerEvent<HTMLElement>) => {
    if (event.pointerType !== "touch" || editor !== null) return;
    const element = event.currentTarget;
    element.setPointerCapture(event.pointerId);
    const state = {
      source,
      target: null,
      active: false,
      startX: event.clientX,
      startY: event.clientY,
      timer: 0,
    };
    state.timer = window.setTimeout(() => {
      state.active = true;
      setDragSource(source);
      navigator.vibrate?.(20);
    }, 360);
    touchDrag.current = state;
  };

  const moveTouchDrag = (event: ReactPointerEvent<HTMLElement>) => {
    const state = touchDrag.current;
    if (!state || event.pointerType !== "touch") return;
    if (!state.active) {
      if (Math.hypot(event.clientX - state.startX, event.clientY - state.startY) > 9) {
        window.clearTimeout(state.timer);
        touchDrag.current = null;
      }
      return;
    }
    event.preventDefault();
    const targetElement = document.elementsFromPoint(event.clientX, event.clientY)
      .map((element) => element.closest<HTMLElement>("[data-drop-area]"))
      .find((element): element is HTMLElement => Boolean(element));
    const target = targetElement ? {
      area: targetElement.dataset.dropArea as RosterLocation["area"],
      index: Number(targetElement.dataset.dropIndex),
    } : null;
    state.target = target;
    setDropTarget(target);
  };

  const endTouchDrag = (event: ReactPointerEvent<HTMLElement>) => {
    const state = touchDrag.current;
    if (!state || event.pointerType !== "touch") return;
    window.clearTimeout(state.timer);
    if (state.active && state.target) {
      event.preventDefault();
      moveMember(state.source, state.target);
    }
    if (state.active) {
      suppressCardClick.current = true;
      window.setTimeout(() => { suppressCardClick.current = false; }, 0);
    }
    touchDrag.current = null;
    setDragSource(null);
    setDropTarget(null);
  };

  const regulationOptions = useMemo<SelectOption<string>[]>(() => {
    if (!data) return [];
    return data.regulationChoices().map((regulation, index) => ({
      value: regulation.id,
      label: regulation.name,
      separatorBefore: index === 2,
    }));
  }, [data]);

  const snapshot = (name: string): TeamSnapshot => ({
    name,
    regulation_id: regulationId,
    active_slots: team.map(persistedMember),
    bench: bench.map((member) => persistedMember(member)!),
  });

  const saveCurrentTeam = () => {
    const requestedName = teamName.trim() || window.prompt(language === "de" ? "Wie soll das Team heißen?" : "What should the team be called?", "")?.trim();
    if (!requestedName || !selectedFolder) return;
    const [next, teamId] = upsertTeam(library, selectedFolder.id, snapshot(requestedName), loadedTeamId);
    setLibrary(next);
    setTeamName(requestedName);
    setSelectedTeamId(teamId);
    setLoadedTeamId(teamId);
    notify(language === "de" ? `„${requestedName}“ wurde gespeichert.` : `“${requestedName}” was saved.`);
  };

  const loadSavedTeam = () => {
    if (!selectedSavedTeam || !data) return;
    if ((team.some(Boolean) || bench.length) && !window.confirm(language === "de" ? "Das aktuelle Team wird ersetzt. Fortfahren?" : "The current team will be replaced. Continue?")) return;
    const active = selectedSavedTeam.active_slots.slice(0, 6).map(normalizeMember);
    while (active.length < 6) active.push(null);
    const loadedBench = selectedSavedTeam.bench.map(normalizeMember).filter((member) => member !== null);
    try {
      [...active, ...loadedBench].forEach((member) => { if (member) data.form(member); });
    } catch {
      notify(language === "de" ? "Das gespeicherte Team enthält eine unbekannte Pokémon-Form." : "The saved team contains an unknown Pokémon form.");
      return;
    }
    setTeam(active);
    setBench(loadedBench);
    setTeamName(selectedSavedTeam.name);
    const knownRegulation = data.regulationChoices().some((regulation) => regulation.id === selectedSavedTeam.regulation_id);
    setRegulationId(knownRegulation ? selectedSavedTeam.regulation_id : data.currentRegulationId);
    setLoadedTeamId(selectedSavedTeam.id);
    setEditor(null);
    setDraft(null);
    notify(language === "de" ? `„${selectedSavedTeam.name}“ wurde geladen.` : `“${selectedSavedTeam.name}” was loaded.`);
  };

  const resetTeam = () => {
    if (!team.some(Boolean) && !bench.length) return;
    if (!window.confirm(language === "de" ? "Aktives Team und Ersatzbank zurücksetzen? Gespeicherte Teams bleiben erhalten." : "Reset the active team and bench? Saved teams remain unchanged.")) return;
    setTeam(EMPTY_TEAM());
    setBench([]);
    setTeamName("");
    setLoadedTeamId(undefined);
    setEditor(null);
    setDraft(null);
  };

  const resetBench = () => {
    if (!bench.length || !window.confirm(language === "de" ? "Ersatzbank zurücksetzen?" : "Reset the bench?")) return;
    setBench([]);
    setEditor(null);
    setDraft(null);
  };

  const uploadPaste = () => {
    if (!data) return;
    const paste = exportPokepaste(team, regulationId, data.pokedex.regulationsById.get(regulationId)?.name ?? "National Dex", data);
    if (!paste) {
      notify(language === "de" ? "Füge dem aktiven Team zuerst ein Pokémon hinzu." : "Add a Pokémon to the active team first.");
      return;
    }
    submitPokepaste(paste, teamName, data.regulationFormatName(regulationId));
    notify(language === "de" ? "PokéPaste wurde in einem neuen Tab geöffnet." : "PokéPaste opened in a new tab.");
  };

  const importPaste = async (value: string) => {
    if (!data) return;
    setPasteBusy(true);
    try {
      const remote = parsePasteId(value) ? await fetchPokepaste(value) : { title: "", paste: value };
      const result = parsePokepaste(remote.paste, regulationId, data);
      if (!result.members.length) throw new Error(language === "de" ? "Es wurde kein Pokémon erkannt." : "No Pokémon was recognized.");
      if ((team.some(Boolean) || bench.length) && !window.confirm(language === "de" ? "Das aktuelle Team wird ersetzt. Fortfahren?" : "The current team will be replaced. Continue?")) return;
      const active: Array<TeamMember | null> = result.members.slice(0, 6);
      while (active.length < 6) active.push(null);
      setTeam(active);
      setBench(result.members.slice(6));
      setTeamName(remote.title || (language === "de" ? "Importiertes Team" : "Imported team"));
      setLoadedTeamId(undefined);
      setPasteDialog(false);
      notify(`${result.members.length} Pokémon ${language === "de" ? "wurden importiert" : "were imported"}${result.issues.length ? ` · ${language === "de" ? "nicht erkannt" : "not recognized"}: ${result.issues.slice(0, 4).join(", ")}` : ""}.`);
    } catch (error) {
      notify(error instanceof Error ? error.message : COPY[language].loadError);
    } finally {
      setPasteBusy(false);
    }
  };

  if (!data || loadError) {
    return (
      <main className="app-shell"><section className="pokedex-card loading-card team-builder-card"><AppHeader language={language} onToggle={() => setLanguage((current) => current === "de" ? "en" : "de")} /><p className={loadError ? "load-error" : "loading-message"}>{loadError || COPY[language].loading}</p></section></main>
    );
  }

  const renderLocation = (location: RosterLocation, member: TeamMember | null) => {
    if (sameLocation(editor, location)) {
      if (!draft) return <PokemonSearch data={data} regulationId={regulationId} language={language} onSelect={choosePokemon} onCancel={() => setEditor(null)} />;
      return <MemberEditor member={draft} data={data} regulationId={regulationId} language={language} onChange={setDraft} onSave={saveDraft} onRemove={() => removeAt(location, false)} />;
    }
    if (!member) return <EmptySlot location={location} language={language} dropTarget={sameLocation(dropTarget, location)} onClick={() => openEditor(location)} onDrop={() => drop(location)} />;
    return (
      <CompactMemberCard
        member={member}
        location={location}
        data={data}
        regulationId={regulationId}
        language={language}
        dragging={sameLocation(dragSource, location)}
        dropTarget={sameLocation(dropTarget, location)}
        onEdit={() => openEditor(location)}
        onRemove={() => removeAt(location)}
        onDragStart={() => {
          dragSourceRef.current = location;
          setDragSource(location);
        }}
        onDragEnd={() => {
          dragSourceRef.current = null;
          setDragSource(null);
          setDropTarget(null);
        }}
        onDrop={() => drop(location)}
        onTouchStart={(event) => beginTouchDrag(location, event)}
        onTouchMove={moveTouchDrag}
        onTouchEnd={endTouchDrag}
      />
    );
  };

  return (
    <main className="app-shell team-builder-shell">
      <section className="pokedex-card team-builder-card">
        <AppHeader language={language} onToggle={() => setLanguage((current) => current === "de" ? "en" : "de")} />
        <div className="team-meta-row">
          <label className="team-name-field"><span className="sr-only">{COPY[language].teamName}</span><input value={teamName} onChange={(event) => setTeamName(event.target.value)} placeholder={COPY[language].teamName} /></label>
          <label className="regulation-field"><span>{COPY[language].regulation}</span><Dropdown value={regulationId} options={regulationOptions} onChange={setRegulationId} label={COPY[language].regulation} /></label>
        </div>

        <TeamLibrary
          language={language}
          library={library}
          selectedFolderId={selectedFolderId}
          selectedTeamId={selectedTeamId}
          onFolder={(id) => { setSelectedFolderId(id); setSelectedTeamId(""); }}
          onTeam={setSelectedTeamId}
          onCreateFolder={() => {
            const name = window.prompt(language === "de" ? "Name des neuen Ordners:" : "Name of the new folder:")?.trim();
            if (!name) return;
            const [next, id] = createFolder(library, name);
            setLibrary(next); setSelectedFolderId(id); setSelectedTeamId("");
          }}
          onRenameFolder={() => {
            if (!selectedFolder) return;
            const name = window.prompt(language === "de" ? "Neuer Ordnername:" : "New folder name:", selectedFolder.name)?.trim();
            if (name) setLibrary(renameFolder(library, selectedFolder.id, name));
          }}
          onDeleteFolder={() => {
            if (!selectedFolder || !window.confirm(`${COPY[language].deleteFolder}: ${selectedFolder.name}?`)) return;
            const next = deleteFolder(library, selectedFolder.id, COPY[language].defaultFolder);
            setLibrary(next); setSelectedFolderId(next.folders[0].id); setSelectedTeamId("");
          }}
          onSaveTeam={saveCurrentTeam}
          onLoadTeam={loadSavedTeam}
          onDeleteTeam={() => {
            if (!selectedFolder || !selectedSavedTeam || !window.confirm(`${COPY[language].deleteTeam}: ${selectedSavedTeam.name}?`)) return;
            setLibrary(deleteTeam(library, selectedFolder.id, selectedSavedTeam.id ?? ""));
            if (loadedTeamId === selectedSavedTeam.id) { setTeam(EMPTY_TEAM()); setBench([]); setTeamName(""); setLoadedTeamId(undefined); }
            setSelectedTeamId("");
          }}
        />

        {feedback && <div className="app-feedback" role="status">{feedback}</div>}

        <div className="roster" onDragOver={(event: DragEvent) => {
          const target = (event.target as HTMLElement).closest<HTMLElement>("[data-drop-area]");
          if (target) setDropTarget({ area: target.dataset.dropArea as RosterLocation["area"], index: Number(target.dataset.dropIndex) });
        }}>
          <SectionHeader title={COPY[language].team} action={<button type="button" className="section-danger-button" disabled={!team.some(Boolean) && !bench.length} onClick={resetTeam}>{COPY[language].resetTeam}</button>} />
          {team.map((member, index) => <div className="roster-card-host" key={`team-${index}`}>{renderLocation({ area: "team", index }, member)}</div>)}

          <div className="pokepaste-actions">
            <button type="button" disabled={!team.some(Boolean) || editor !== null} onClick={uploadPaste}>{COPY[language].upload}</button>
            <button type="button" disabled={editor !== null} onClick={() => setPasteDialog(true)}>{COPY[language].import}</button>
          </div>

          <SectionHeader title={COPY[language].bench} action={<button type="button" className="section-danger-button" disabled={!bench.length} onClick={resetBench}>{COPY[language].resetBench}</button>} />
          {bench.map((member, index) => <div className="roster-card-host" key={`bench-${index}-${member.pokemon_id}`}>{renderLocation({ area: "bench", index }, member)}</div>)}
          <div className="roster-card-host">{renderLocation({ area: "bench", index: bench.length }, null)}</div>
        </div>
      </section>
      {pasteDialog && <PasteImportDialog language={language} busy={pasteBusy} onClose={() => setPasteDialog(false)} onImport={(value) => void importPaste(value)} />}
    </main>
  );
}
