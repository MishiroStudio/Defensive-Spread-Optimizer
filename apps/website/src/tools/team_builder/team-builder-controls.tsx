import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  CATEGORY_NAMES,
  MAX_STAT_POINTS,
  MAX_TOTAL_STAT_POINTS,
  RUBRIC_NAMES,
  RUBRIC_ORDER,
  STAT_NAMES,
  STAT_ORDER,
  TYPE_NAMES,
  localizedName,
  type Move,
  type MoveCategory,
  type MoveRubric,
  type PokemonForm,
  type StatKey,
} from "../pokedex/pokedex-data";
import { publicPath } from "../pokedex/public-path";
import {
  ITEM_CATEGORIES,
  ITEM_CATEGORY_NAMES,
  type ItemCategory,
  type Language,
  type TeamBuilderData,
  type TeamMember,
} from "./team-builder-data";

export interface SelectOption<T extends string> {
  value: T;
  label: string;
  separatorBefore?: boolean;
}

export function Chevron({ open = false }: { open?: boolean }) {
  return <span aria-hidden="true" className={`select-chevron${open ? " open" : ""}`} />;
}

export function Dropdown<T extends string>({
  value,
  options,
  onChange,
  label,
  className = "",
  disabled = false,
}: {
  value: T;
  options: SelectOption<T>[];
  onChange: (value: T) => void;
  label: string;
  className?: string;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value) ?? options[0];
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  return (
    <div className={`pretty-select ${className}`} ref={root}>
      <button
        type="button"
        className="pretty-select-trigger"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selected?.label ?? "–"}</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="pretty-select-menu" role="listbox" aria-label={label}>
          {options.map((option) => (
            <button
              type="button"
              role="option"
              aria-selected={option.value === value}
              className={`${option.value === value ? "selected" : ""}${option.separatorBefore ? " separator" : ""}`}
              key={option.value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function TypeIcon({ type, size = 22 }: { type: string; size?: number }) {
  return (
    <img
      className="tb-type-icon"
      src={publicPath(`assets/types/${type}.png`)}
      alt={TYPE_NAMES.en[type] ?? type}
      title={TYPE_NAMES.en[type] ?? type}
      width={size}
      height={size}
    />
  );
}

export function TypeChip({ type, language }: { type: string; language: Language }) {
  return (
    <span className={`tb-type-chip type-${type}`}>
      <TypeIcon type={type} size={16} />
      {TYPE_NAMES[language][type] ?? type}
    </span>
  );
}

export function CategoryIcon({ move, data, size = 18 }: { move: Move; data: TeamBuilderData; size?: number }) {
  return (
    <img
      className={`move-category-icon category-${move.category}`}
      src={data.categoryIcon(move)}
      alt={move.category}
      title={move.category}
      width={size}
      height={size}
    />
  );
}

export function PokemonSearch({
  data,
  regulationId,
  language,
  onSelect,
  onCancel,
}: {
  data: TeamBuilderData;
  regulationId: string;
  language: Language;
  onSelect: (form: PokemonForm) => void;
  onCancel: () => void;
}) {
  const [query, setQuery] = useState("");
  const results = useMemo(
    () => data.searchForms(query, regulationId),
    [data, query, regulationId],
  );
  return (
    <section className="pokemon-search-card">
      <div className="search-field pokemon-search-field">
        <span className="search-symbol" aria-hidden="true">⌕</span>
        <input
          autoFocus
          value={query}
          placeholder={language === "de" ? "Pokémon, Typ, Fähigkeit, Attacke …" : "Pokémon, type, ability, move …"}
          aria-label={language === "de" ? "Pokémon suchen" : "Search Pokémon"}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") onCancel();
            if (event.key === "Enter" && results[0]) onSelect(results[0]);
          }}
        />
        <button type="button" className="field-close" onClick={onCancel} aria-label={language === "de" ? "Abbrechen" : "Cancel"}>×</button>
      </div>
      {query && (
        <div className="pokemon-search-results">
          {results.length ? results.map((form) => (
            <button type="button" key={form.pokemon_id} onClick={() => onSelect(form)}>
              <img
                src={publicPath(`assets/sprites/list/normal/${form.api_name}.png`)}
                alt=""
                width="38"
                height="38"
                onError={(event) => { event.currentTarget.src = publicPath("assets/sprites/missingno.png"); }}
              />
              <span className="pokemon-result-names">
                <strong>{localizedName(form, language)}</strong>
                <small>{localizedName(form, language === "de" ? "en" : "de")}</small>
              </span>
              <span className="pokemon-result-types">
                {form.types.map((type) => <TypeIcon type={type} size={22} key={type} />)}
              </span>
              <small>#{String(form.national_dex).padStart(4, "0")}</small>
            </button>
          )) : <p className="empty-menu-message">{language === "de" ? "Kein Pokémon gefunden." : "No Pokémon found."}</p>}
        </div>
      )}
    </section>
  );
}

function SearchPopup({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`search-popup ${className}`}>{children}</div>;
}

export function ItemPicker({
  data,
  member,
  regulationId,
  language,
  itemId,
  onChange,
}: {
  data: TeamBuilderData;
  member: TeamMember;
  regulationId: string;
  language: Language;
  itemId: string | null;
  onChange: (itemId: string | null) => void;
}) {
  const selected = itemId ? data.itemsByName.get(itemId) : undefined;
  const [category, setCategory] = useState<ItemCategory>("all");
  const [query, setQuery] = useState(selected ? localizedName(selected, language) : "");
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const categories = ITEM_CATEGORIES.filter((value) => (
    value !== "mega-stones"
    || data.availableItems(member, regulationId, language, "mega-stones").length > 0
  ));
  const options = data.availableItems(member, regulationId, language, category, query === (selected ? localizedName(selected, language) : "") ? "" : query);
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  const selectCategory = (value: ItemCategory) => {
    setCategory(value);
    if (value === "mega-stones") {
      const megaStones = data.availableItems(member, regulationId, language, "mega-stones");
      if (megaStones.length === 1) {
        onChange(megaStones[0].api_name);
        setQuery(localizedName(megaStones[0], language));
      }
    }
  };
  return (
    <div className="item-picker" ref={root}>
      <Dropdown
        value={category}
        options={categories.map((value) => ({ value, label: ITEM_CATEGORY_NAMES[language][value] }))}
        onChange={selectCategory}
        label={language === "de" ? "Item-Kategorie" : "Item category"}
        className="item-category-select"
      />
      <div className="search-combobox">
        <div className="item-combobox-control">
          {selected && <img src={publicPath(`assets/items/${selected.api_name}.png`)} alt="" width="24" height="24" onLoad={(event) => { event.currentTarget.hidden = false; }} onError={(event) => { event.currentTarget.hidden = true; }} />}
          <input
            value={query}
            placeholder="Item"
            aria-label={language === "de" ? "Item suchen" : "Search item"}
            onFocus={(event) => { setOpen(true); if (selected) event.currentTarget.select(); }}
            onChange={(event) => {
              if (selected) onChange(null);
              setQuery(event.target.value);
              setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpen(false);
              if (event.key === "Enter" && options[0]) {
                onChange(options[0].api_name);
                setQuery(localizedName(options[0], language));
                setOpen(false);
              }
            }}
          />
          {selected && <button type="button" className="clear-selection" aria-label={language === "de" ? "Item entfernen" : "Remove item"} onClick={() => { onChange(null); setQuery(""); }}>×</button>}
          <button type="button" className="combobox-arrow" aria-label={language === "de" ? "Items öffnen" : "Open items"} onClick={() => { setOpen((current) => !current); setQuery(selected ? localizedName(selected, language) : ""); }}><Chevron open={open} /></button>
        </div>
        {open && (
          <SearchPopup className="item-popup">
            <button type="button" className={!selected ? "selected" : ""} onClick={() => { onChange(null); setQuery(""); setOpen(false); }}>
              {language === "de" ? "Kein Item" : "No item"}
            </button>
            {options.map((item) => (
              <button type="button" className={item.api_name === itemId ? "selected" : ""} key={item.api_name} onClick={() => { onChange(item.api_name); setQuery(localizedName(item, language)); setOpen(false); }}>
                <img src={publicPath(`assets/items/${item.api_name}.png`)} alt="" width="26" height="26" onError={(event) => { event.currentTarget.hidden = true; }} />
                <span>{localizedName(item, language)}</span>
              </button>
            ))}
            {!options.length && <p className="empty-menu-message">{language === "de" ? "Keine passenden Items." : "No matching items."}</p>}
          </SearchPopup>
        )}
      </div>
      {selected && <p className="effect-description">{data.itemDescription(selected.api_name, language)}</p>}
    </div>
  );
}

function MoveTableHeader({ language }: { language: Language }) {
  return (
    <div className="move-table-row move-table-header">
      <span aria-hidden="true" />
      <span>{language === "de" ? "Attacke" : "Move"}</span>
      <span>{language === "de" ? "Kat." : "Cat."}</span>
      <span>{language === "de" ? "Stärke" : "Power"}</span>
      <span>{language === "de" ? "Gen." : "Acc."}</span>
      <span>AP</span>
    </div>
  );
}

function MoveRow({
  move,
  data,
  member,
  language,
}: {
  move: Move;
  data: TeamBuilderData;
  member: TeamMember;
  language: Language;
}) {
  return (
    <div className="move-table-row">
      <TypeIcon type={move.type} size={22} />
      <span className="move-name-cell">{localizedName(move, language)}</span>
      <span className="move-category-cell"><CategoryIcon move={move} data={data} /></span>
      <span>{move.power ?? "—"}</span>
      <span>{move.always_hits ? "—" : move.accuracy === null ? "—" : `${move.accuracy}%`}</span>
      <span>{data.movePp(member, move)}</span>
    </div>
  );
}

export function MoveFilters({
  language,
  category,
  rubric,
  onCategory,
  onRubric,
}: {
  language: Language;
  category: MoveCategory | "";
  rubric: MoveRubric | "";
  onCategory: (value: MoveCategory | "") => void;
  onRubric: (value: MoveRubric | "") => void;
}) {
  const categoryOptions: Array<SelectOption<MoveCategory | "">> = [
    { value: "", label: language === "de" ? "Alle Kategorien" : "All categories" },
    ...(["physical", "special", "status"] as MoveCategory[]).map((value) => ({ value, label: CATEGORY_NAMES[language][value] })),
  ];
  const rubricOptions: Array<SelectOption<MoveRubric | "">> = [
    { value: "", label: language === "de" ? "Alle Rubriken" : "All rubrics" },
    ...[...new Set(RUBRIC_ORDER)].map((value) => ({ value, label: RUBRIC_NAMES[language][value] })),
  ];
  return (
    <div className="move-filters">
      <Dropdown value={category} options={categoryOptions} onChange={onCategory} label={language === "de" ? "Attackenkategorie" : "Move category"} />
      <Dropdown value={rubric} options={rubricOptions} onChange={onRubric} label={language === "de" ? "Attackenrubrik" : "Move rubric"} />
    </div>
  );
}

export function MovePicker({
  data,
  member,
  language,
  category,
  rubric,
  moveId,
  excludedMoveIds,
  onChange,
  number,
}: {
  data: TeamBuilderData;
  member: TeamMember;
  language: Language;
  category: MoveCategory | "";
  rubric: MoveRubric | "";
  moveId: string | null;
  excludedMoveIds: string[];
  onChange: (moveId: string | null) => void;
  number: number;
}) {
  const selected = moveId ? data.movesByName.get(moveId) : undefined;
  const [query, setQuery] = useState(selected ? localizedName(selected, language) : "");
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const selectedName = selected ? localizedName(selected, language) : "";
  const excluded = new Set(excludedMoveIds);
  const options = data.filteredMoves(member, language, category, rubric, query === selectedName ? "" : query)
    .filter((move) => !excluded.has(move.api_name));
  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  return (
    <div className="move-picker" ref={root}>
      <span className="move-number">{number}</span>
      <div className="move-combobox">
        <div className="move-combobox-control move-table-row">
          {selected ? <TypeIcon type={selected.type} size={22} /> : <span className="empty-type-icon" />}
          <input
            value={query}
            placeholder={language === "de" ? "Attacke auswählen" : "Choose move"}
            aria-label={`${language === "de" ? "Attacke" : "Move"} ${number}`}
            onFocus={(event) => { setOpen(true); if (selected) event.currentTarget.select(); }}
            onChange={(event) => {
              if (selected) onChange(null);
              setQuery(event.target.value);
              setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpen(false);
              if (event.key === "Enter" && options[0]) {
                onChange(options[0].api_name);
                setQuery(localizedName(options[0], language));
                setOpen(false);
              }
            }}
          />
          <span className="move-category-cell">{selected && <CategoryIcon move={selected} data={data} />}</span>
          <span>{selected?.power ?? (selected ? "—" : "")}</span>
          <span>{selected ? (selected.always_hits || selected.accuracy === null ? "—" : `${selected.accuracy}%`) : ""}</span>
          <span>{selected ? data.movePp(member, selected) : ""}</span>
          <button type="button" className="move-arrow" aria-label={language === "de" ? "Attacken öffnen" : "Open moves"} onClick={() => { setOpen((current) => !current); setQuery(selectedName); }}><Chevron open={open} /></button>
        </div>
        {open && (
          <SearchPopup className="move-popup">
            <MoveTableHeader language={language} />
            <button type="button" className={`move-option${!selected ? " selected" : ""}`} onClick={() => { onChange(null); setQuery(""); setOpen(false); }}>
              <div className="move-table-row"><span /><span>{language === "de" ? "Keine Attacke" : "No move"}</span><span /><span /><span /><span /></div>
            </button>
            {options.map((move) => (
              <button type="button" className={`move-option${move.api_name === moveId ? " selected" : ""}`} key={move.api_name} onClick={() => { onChange(move.api_name); setQuery(localizedName(move, language)); setOpen(false); }}>
                <MoveRow move={move} data={data} member={member} language={language} />
              </button>
            ))}
            {!options.length && <p className="empty-menu-message">{language === "de" ? "Keine passenden Attacken." : "No matching moves."}</p>}
          </SearchPopup>
        )}
      </div>
        {selected && (
          <p className="effect-description tb-move-description">
            {data.moveDescription(selected.api_name, language)}
          </p>
        )}
    </div>
  );
}

export function StatsEditor({
  data,
  member,
  language,
  onChange,
}: {
  data: TeamBuilderData;
  member: TeamMember;
  language: Language;
  onChange: (member: TeamMember) => void;
}) {
  const stats = data.calculatedStats(member);
  const baseStats = data.form(member).base_stats;
  const total = STAT_ORDER.reduce((sum, stat) => sum + member.stat_points[stat], 0);
  const baseStatTotal = STAT_ORDER.reduce((sum, stat) => sum + baseStats[stat], 0);
  const finalStatTotal = STAT_ORDER.reduce((sum, stat) => sum + stats[stat], 0);
  const natureStats = STAT_ORDER.filter((stat): stat is Exclude<StatKey, "hp"> => stat !== "hp");
  const setPoints = (stat: StatKey, requested: number) => {
    const current = member.stat_points[stat];
    const available = MAX_TOTAL_STAT_POINTS - (total - current);
    const value = Math.max(0, Math.min(MAX_STAT_POINTS, available, Math.trunc(requested || 0)));
    onChange({ ...member, stat_points: { ...member.stat_points, [stat]: value } });
  };
  const toggleNature = (stat: Exclude<StatKey, "hp">, direction: "up" | "down") => {
    if (direction === "up") {
      onChange({
        ...member,
        nature_increased: member.nature_increased === stat ? null : stat,
        nature_decreased: member.nature_decreased === stat ? null : member.nature_decreased,
      });
    } else {
      onChange({
        ...member,
        nature_decreased: member.nature_decreased === stat ? null : stat,
        nature_increased: member.nature_increased === stat ? null : member.nature_increased,
      });
    }
  };
  return (
    <div className="stats-editor">
      {STAT_ORDER.map((stat) => (
        <div className="stat-editor-row" key={stat}>
          <strong>{STAT_NAMES[language][stat]}</strong>

          <span>{baseStats[stat]}</span>

          <strong className="final-stat-value">
            {stats[stat]}
          </strong>

          <input
            type="range"
            min="0"
            max={MAX_STAT_POINTS}
            value={member.stat_points[stat]}
            onChange={(event) => setPoints(stat, Number(event.target.value))}
            aria-label={`${STAT_NAMES[language][stat]} Stat Points`}
          />

          <input
            type="number"
            inputMode="numeric"
            min="0"
            max={MAX_STAT_POINTS}
            value={member.stat_points[stat]}
            onFocus={(event) => event.currentTarget.select()}
            onChange={(event) => setPoints(stat, Number(event.target.value))}
          />
          {stat === "hp" ? <span className="nature-empty" /> : (
            <div className="nature-buttons">
              <button type="button" className={member.nature_increased === stat ? "active positive" : ""} onClick={() => toggleNature(stat, "up")}>+</button>
              <button type="button" className={member.nature_decreased === stat ? "active negative" : ""} onClick={() => toggleNature(stat, "down")}>−</button>
            </div>
          )}
        </div>
      ))}
      <div className="stats-footer">
        <strong className="bst-label">BST</strong>
        <strong className="bst-base">{baseStatTotal}</strong>
        <strong className="points-total">{total}/{MAX_TOTAL_STAT_POINTS}</strong>
        <strong className="bst-final">{finalStatTotal}</strong>
        <span className="nature-name">{data.natureName(member, language)}</span>
      </div>
      <div className="nature-mobile-grid">
        {natureStats.map((stat) => (
          <div key={stat}><span>{STAT_NAMES[language][stat]}</span><div className="nature-buttons"><button type="button" className={member.nature_increased === stat ? "active positive" : ""} onClick={() => toggleNature(stat, "up")}>+</button><button type="button" className={member.nature_decreased === stat ? "active negative" : ""} onClick={() => toggleNature(stat, "down")}>−</button></div></div>
        ))}
        <strong>{data.natureName(member, language)}</strong>
      </div>
    </div>
  );
}
