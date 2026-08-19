import {
  type CSSProperties,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  type Language,
  type Move,
  type MoveCategory,
  type MoveRubric,
  type PokemonForm,
  type StatKey,
  CATEGORY_COLORS,
  CATEGORY_ICON_FILES,
  CATEGORY_NAMES,
  MAX_STAT_POINTS,
  MAX_TOTAL_STAT_POINTS,
  PokedexIndex,
  RUBRIC_NAMES,
  RUBRIC_ORDER,
  SOURCE_NAMES,
  STAT_NAMES,
  STAT_ORDER,
  TYPE_COLORS,
  TYPE_NAMES,
  calculateAllStats,
  formatMoveEffect,
  groupAndSortMoves,
  localizedName,
  matchRank,
  moveDisplayPp,
  moveMatchesRubric,
  statTotal,
} from "./pokedex-data";
import { publicPath } from "./public-path";

type StatMode = "min" | "max" | "custom";
type SearchState = "learned" | "not-learned" | "not-found" | null;

const COPY = {
  de: {
    back: "← Zurück zu den Ergebnissen",
    dex: "Nationaldex",
    shiny: "Shiny",
    noSprite: "Kein Sprite verfügbar",
    abilities: "Fähigkeiten",
    abilityMissing: "Für diese Fähigkeit ist noch keine Beschreibung hinterlegt.",
    stats: "Stats",
    base: "Base",
    min: "Min",
    minNature: "Min −Wesen",
    max: "Max",
    maxNature: "Max +Wesen",
    custom: "Individuell",
    value: "Wert",
    points: "EVs",
    nature: "Wesen",
    total: "Total",
    moves: "Attacken",
    moveSearch: "Attacke suchen …",
    filters: "Filter:",
    category: "Kategorie",
    group: "Rubrik",
    none: "Keine",
    move: "Attacke",
    power: "Stärke",
    accuracy: "Gen.",
    pp: "AP",
    expandAll: "Alle ausklappen",
    collapseAll: "Alle einklappen",
    learned: (move: string) => `✓ Dieses Pokémon lernt ${move}.`,
    notLearned: (move: string) => `✕ Dieses Pokémon lernt ${move} nicht.`,
    notFound: "Keine Attacke gefunden.",
    fallback: (source: string) => `Nicht in Champions – Movepool aus ${source}`,
  },
  en: {
    back: "← Back to results",
    dex: "National Dex",
    shiny: "Shiny",
    noSprite: "No sprite available",
    abilities: "Abilities",
    abilityMissing: "No description has been stored for this ability yet.",
    stats: "Stats",
    base: "Base",
    min: "Min",
    minNature: "Min −Nature",
    max: "Max",
    maxNature: "Max +Nature",
    custom: "Custom",
    value: "Value",
    points: "EVs",
    nature: "Nature",
    total: "Total",
    moves: "Moves",
    moveSearch: "Search move …",
    filters: "Filter:",
    category: "Category",
    group: "Group",
    none: "None",
    move: "Move",
    power: "Power",
    accuracy: "Acc.",
    pp: "PP",
    expandAll: "Expand all",
    collapseAll: "Collapse all",
    learned: (move: string) => `✓ This Pokémon learns ${move}.`,
    notLearned: (move: string) => `✕ This Pokémon does not learn ${move}.`,
    notFound: "No move found.",
    fallback: (source: string) => `Not in Champions – showing ${source} set`,
  },
} as const;

function emptyNumbers(value: number): Record<StatKey, number> {
  return Object.fromEntries(STAT_ORDER.map((stat) => [stat, value])) as Record<StatKey, number>;
}

function TypeIcon({ type, size = 22 }: { type: string; size?: number }) {
  return (
    <img
      className="type-icon"
      src={publicPath(`assets/types/${type}.png`)}
      alt=""
      title={TYPE_NAMES.en[type] ?? type}
      width={size}
      height={size}
    />
  );
}

function TypeChips({ types, language }: { types: string[]; language: Language }) {
  return (
    <div className="type-chips">
      {types.map((type) => (
        <span
          className="type-chip"
          key={type}
          style={{ backgroundColor: TYPE_COLORS[type] ?? "#94A3B8" }}
        >
          {TYPE_NAMES[language][type] ?? type}
        </span>
      ))}
    </div>
  );
}

function CategoryIcon({ category, language }: { category: MoveCategory; language: Language }) {
  const image = publicPath(`assets/move-categories/${CATEGORY_ICON_FILES[category]}`);
  return (
    <span
      className="category-icon"
      role="img"
      aria-label={CATEGORY_NAMES[language][category]}
      title={CATEGORY_NAMES[language][category]}
      style={{
        "--category-color": CATEGORY_COLORS[category],
        "--category-image": `url(${image})`,
      } as CSSProperties}
    />
  );
}

function DetailSprite({
  form,
  shiny,
  noSpriteText,
}: {
  form: PokemonForm;
  shiny: boolean;
  noSpriteText: string;
}) {
  const relativePath = shiny ? form.sprites.home_shiny : form.sprites.home;
  const localFallback = publicPath(`assets/sprites/list/normal/${form.api_name}.png`);
  const [useFallback, setUseFallback] = useState(false);
  const [failed, setFailed] = useState(false);
  const detailSource = relativePath ? publicPath(relativePath) : localFallback;
  const source = useFallback ? localFallback : detailSource;

  if (failed) return <p className="sprite-missing">{noSpriteText}</p>;
  return (
    <img
      className="detail-sprite"
      src={source}
      alt={localizedName(form, "en")}
      onError={() => {
        if (!useFallback && source !== localFallback) setUseFallback(true);
        else setFailed(true);
      }}
    />
  );
}

function StatsPanel({ form, language }: { form: PokemonForm; language: Language }) {
  const text = COPY[language];
  const [mode, setMode] = useState<StatMode>("custom");
  const [points, setPoints] = useState<Record<StatKey, number>>(() => emptyNumbers(0));
  const [natures, setNatures] = useState<Record<StatKey, number>>(() => emptyNumbers(1));

  const neutralPoints = useMemo(() => emptyNumbers(mode === "max" ? MAX_STAT_POINTS : 0), [mode]);
  const neutralNatures = useMemo(() => emptyNumbers(1), []);
  const fixedNature = useMemo(() => Object.fromEntries(STAT_ORDER.map((stat) => [
    stat,
    stat === "hp" ? 1 : mode === "max" ? 1.1 : 0.9,
  ])) as Record<StatKey, number>, [mode]);
  const neutralValues = calculateAllStats(form.base_stats, neutralPoints, neutralNatures);
  const natureValues = calculateAllStats(form.base_stats, neutralPoints, fixedNature);
  const customValues = calculateAllStats(form.base_stats, points, natures);
  const baseTotal = statTotal(form.base_stats);
  const neutralTotal = statTotal(neutralValues);
  const natureTotal = statTotal(natureValues);
  const customTotal = statTotal(customValues);
  const pointsTotal = statTotal(points);

  function updatePoints(stat: StatKey, value: number) {
    const nextValue = Number.isFinite(value)
      ? Math.max(0, Math.min(MAX_STAT_POINTS, Math.round(value)))
      : 0;
    setPoints((current) => ({ ...current, [stat]: nextValue }));
  }

  function toggleNature(stat: StatKey, modifier: 0.9 | 1.1) {
    if (stat === "hp") return;
    setNatures((current) => {
      const next = { ...current };
      if (current[stat] === modifier) {
        next[stat] = 1;
        return next;
      }
      for (const key of STAT_ORDER) {
        if (next[key] === modifier) next[key] = 1;
      }
      next[stat] = modifier;
      return next;
    });
  }

  return (
    <section className="stats-card" aria-labelledby="stats-heading">
      <div className="detail-section-heading">
        <h2 id="stats-heading">{text.stats}</h2>
        <div className="segmented-control" aria-label={text.stats}>
          {(["min", "max", "custom"] as StatMode[]).map((item) => (
            <button
              type="button"
              key={item}
              className={mode === item ? "active" : ""}
              aria-pressed={mode === item}
              onClick={() => setMode(item)}
            >
              {item === "custom" ? text.custom : text[item]}
            </button>
          ))}
        </div>
      </div>

      {mode !== "custom" ? (
        <div className="stat-table fixed-stat-table">
          <div className="stat-table-header">
            <span />
            <span>{text.base}</span>
            <span />
            <span>{mode === "min" ? text.min : text.max}</span>
            <span />
            <span>{mode === "min" ? text.minNature : text.maxNature}</span>
          </div>
          {STAT_ORDER.map((stat) => (
            <div className="stat-row" key={stat}>
              <span className="stat-name">{STAT_NAMES[language][stat]}</span>
              <span>{form.base_stats[stat]}</span>
              <span className="stat-arrow">→</span>
              <strong>{neutralValues[stat]}</strong>
              <span className="stat-arrow">→</span>
              <strong>{natureValues[stat]}</strong>
            </div>
          ))}
          <div className="stat-row stat-total-row">
            <span className="stat-name">{text.total}</span>
            <span>{baseTotal}</span>
            <span className="stat-arrow">→</span>
            <strong>{neutralTotal}</strong>
            <span className="stat-arrow">→</span>
            <strong>{natureTotal}</strong>
          </div>
        </div>
      ) : (
        <div className="stat-table custom-stat-table">
          <div className="stat-table-header">
            <span />
            <span>{text.base}</span>
            <span />
            <span>{text.value}</span>
            <span>{text.points}</span>
            <span>{text.nature}</span>
          </div>
          {STAT_ORDER.map((stat) => (
            <div className="stat-row" key={stat}>
              <span className="stat-name">{STAT_NAMES[language][stat]}</span>
              <span>{form.base_stats[stat]}</span>
              <span className="stat-arrow">→</span>
              <strong>{customValues[stat]}</strong>
              <div className="stat-slider">
                <input
                  type="range"
                  aria-label={`${STAT_NAMES[language][stat]} ${text.points}`}
                  min="0"
                  max={MAX_STAT_POINTS}
                  value={points[stat]}
                  onChange={(event) => updatePoints(stat, Number(event.target.value))}
                />
                <input
                  className="stat-points-input"
                  type="number"
                  inputMode="numeric"
                  aria-label={`${STAT_NAMES[language][stat]} ${text.points}`}
                  min="0"
                  max={MAX_STAT_POINTS}
                  step="1"
                  value={points[stat]}
                  onFocus={(event) => event.currentTarget.select()}
                  onChange={(event) => updatePoints(stat, event.currentTarget.valueAsNumber)}
                />
              </div>
              <div className="nature-buttons">
                <button
                  type="button"
                  disabled={stat === "hp"}
                  className={natures[stat] === 0.9 ? "active negative" : ""}
                  aria-pressed={natures[stat] === 0.9}
                  onClick={() => toggleNature(stat, 0.9)}
                >−</button>
                <button
                  type="button"
                  disabled={stat === "hp"}
                  className={natures[stat] === 1.1 ? "active positive" : ""}
                  aria-pressed={natures[stat] === 1.1}
                  onClick={() => toggleNature(stat, 1.1)}
                >+</button>
              </div>
            </div>
          ))}
          <div className="stat-row stat-total-row">
            <span className="stat-name">{text.total}</span>
            <span>{baseTotal}</span>
            <span className="stat-arrow">→</span>
            <strong>{customTotal}</strong>
            <strong
              className={`points-total${pointsTotal > MAX_TOTAL_STAT_POINTS ? " over-budget" : ""}`}
              aria-live="polite"
            >
              {pointsTotal}/{MAX_TOTAL_STAT_POINTS}
            </strong>
            <span aria-hidden="true" />
          </div>
        </div>
      )}
    </section>
  );
}

function MovesPanel({ index, form, language }: {
  index: PokedexIndex;
  form: PokemonForm;
  language: Language;
}) {
  const text = COPY[language];
  const learnset = index.learnsetsByPokemonId.get(form.pokemon_id);
  const currentMoves = useMemo(() => index.resolvedMoves(form.pokemon_id), [form.pokemon_id, index]);
  const currentMoveIds = useMemo(() => new Set(currentMoves.map((move) => move.move_id)), [currentMoves]);
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [searchState, setSearchState] = useState<SearchState>(null);
  const [selectedMoveId, setSelectedMoveId] = useState<number | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<MoveCategory | "">("");
  const [rubricFilter, setRubricFilter] = useState<MoveRubric | "">("");
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(() => new Set());
  const [expandedMoves, setExpandedMoves] = useState<Set<number>>(() => new Set());
  const [highlightedMoveId, setHighlightedMoveId] = useState<number | null>(null);
  const highlightTimer = useRef<number | null>(null);

  const filteredMoves = useMemo(() => currentMoves.filter((move) => (
    (!categoryFilter || move.category === categoryFilter)
    && moveMatchesRubric(move, rubricFilter)
  )), [categoryFilter, currentMoves, rubricFilter]);
  const groups = useMemo(() => groupAndSortMoves(filteredMoves, language), [filteredMoves, language]);
  const moveSuggestions = useMemo(() => {
    if (!query.trim() || selectedMoveId !== null) return [];
    return index.moves
      .map((move) => ({ move, rank: matchRank(query, [move.api_name, move.name_de, move.name_en]) }))
      .filter((entry): entry is { move: Move; rank: number } => entry.rank !== null)
      .toSorted((left, right) => (
        left.rank - right.rank
        || localizedName(left.move, language).localeCompare(localizedName(right.move, language), language)
      ))
      .slice(0, 10)
      .map((entry) => entry.move);
  }, [index.moves, language, query, selectedMoveId]);

  const allExpanded = groups.length > 0 && groups.every((group) => expandedTypes.has(group.type));
  const note = useMemo(() => {
    if (!learnset) return "";
    const lines: string[] = [];
    if (!learnset.available_in_champions && learnset.learnset_source) {
      const source = SOURCE_NAMES[language][learnset.learnset_source] ?? learnset.learnset_source;
      lines.push(text.fallback(source));
    }
    if (learnset.note) lines.push(learnset.note);
    return lines.join("\n");
  }, [language, learnset, text]);

  useEffect(() => () => {
    if (highlightTimer.current !== null) window.clearTimeout(highlightTimer.current);
  }, []);

  function runMoveSearch(move?: Move) {
    const match = move ?? moveSuggestions[0];
    if (!match) {
      setSearchState("not-found");
      setSelectedMoveId(null);
      return;
    }
    const learned = currentMoveIds.has(match.move_id);
    setQuery(localizedName(match, language));
    setSelectedMoveId(match.move_id);
    setSearchFocused(false);
    setSearchState(learned ? "learned" : "not-learned");
    if (!learned) return;

    setExpandedTypes((current) => new Set(current).add(match.type));
    setHighlightedMoveId(match.move_id);
    if (highlightTimer.current !== null) window.clearTimeout(highlightTimer.current);
    highlightTimer.current = window.setTimeout(() => setHighlightedMoveId(null), 1600);
    window.setTimeout(() => {
      document.getElementById(`move-${match.move_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  }

  function toggleType(type: string) {
    setExpandedTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) {
        next.delete(type);
        setExpandedMoves((moves) => new Set([...moves].filter((moveId) => index.movesById.get(moveId)?.type !== type)));
      } else next.add(type);
      return next;
    });
  }

  const searchMessage = searchState === "not-found"
    ? text.notFound
    : selectedMoveId !== null
      ? (() => {
        const move = index.movesById.get(selectedMoveId);
        if (!move) return "";
        return searchState === "learned"
          ? text.learned(localizedName(move, language))
          : text.notLearned(localizedName(move, language));
      })()
      : "";
  const selectedMove = selectedMoveId === null ? undefined : index.movesById.get(selectedMoveId);
  const displayQuery = selectedMove ? localizedName(selectedMove, language) : query;

  return (
    <section className="moves-card" aria-labelledby="moves-heading">
      <h2 id="moves-heading">{text.moves}</h2>
      {note && <p className="learnset-note">{note}</p>}
      <div className="move-tools">
        <div className="move-search">
          <input
            value={displayQuery}
            placeholder={text.moveSearch}
            autoComplete="off"
            onFocus={() => setSearchFocused(true)}
            onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)}
            onChange={(event) => {
              setQuery(event.target.value);
              setSearchState(null);
              setSelectedMoveId(null);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                runMoveSearch();
              }
              if (event.key === "Escape") setSearchFocused(false);
            }}
          />
          {displayQuery && (
            <button
              type="button"
              aria-label={language === "de" ? "Attackensuche leeren" : "Clear move search"}
              onClick={() => {
                setQuery("");
                setSearchState(null);
                setSelectedMoveId(null);
              }}
            >×</button>
          )}
          {searchFocused && moveSuggestions.length > 0 && (
            <div className="move-suggestions">
              {moveSuggestions.map((move) => (
                <button
                  type="button"
                  key={move.move_id}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => runMoveSearch(move)}
                >
                  <TypeIcon type={move.type} size={18} />
                  <span>{localizedName(move, language)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="move-filter-label">{text.filters}</span>
        <select
          className={categoryFilter ? "active" : ""}
          aria-label={text.category}
          value={categoryFilter}
          onFocus={() => setExpandedTypes(new Set(groups.map((group) => group.type)))}
          onChange={(event) => {
            const nextCategory = event.target.value as MoveCategory | "";
            setCategoryFilter(nextCategory);
            if (nextCategory || rubricFilter) {
              setExpandedTypes(new Set(currentMoves
                .filter((move) => (
                  (!nextCategory || move.category === nextCategory)
                  && moveMatchesRubric(move, rubricFilter)
                ))
                .map((move) => move.type)));
            }
          }}
        >
          <option value="">{text.category}</option>
          {(["physical", "special", "status"] as MoveCategory[]).map((category) => (
            <option key={category} value={category}>{CATEGORY_NAMES[language][category]}</option>
          ))}
        </select>
        <select
          className={rubricFilter ? "active" : ""}
          aria-label={text.group}
          value={rubricFilter}
          onFocus={() => setExpandedTypes(new Set(groups.map((group) => group.type)))}
          onChange={(event) => {
            const nextRubric = event.target.value as MoveRubric | "";
            setRubricFilter(nextRubric);
            if (categoryFilter || nextRubric) {
              setExpandedTypes(new Set(currentMoves
                .filter((move) => (
                  (!categoryFilter || move.category === categoryFilter)
                  && moveMatchesRubric(move, nextRubric)
                ))
                .map((move) => move.type)));
            }
          }}
        >
          <option value="">{text.group}</option>
          {RUBRIC_ORDER.map((rubric) => (
            <option key={rubric} value={rubric}>{RUBRIC_NAMES[language][rubric]}</option>
          ))}
        </select>
      </div>
      {searchMessage && (
        <p className={`move-search-message ${searchState === "learned" ? "success" : "error"}`}>
          {searchMessage}
        </p>
      )}

      <div className="moves-table">
        <div className="move-table-header">
          <span>{text.move}</span>
          <span>{language === "de" ? "Kat." : "Cat."}</span>
          <span>{text.power}</span>
          <span>{text.accuracy}</span>
          <span>{text.pp}</span>
          <button
            type="button"
            title={allExpanded ? text.collapseAll : text.expandAll}
            aria-label={allExpanded ? text.collapseAll : text.expandAll}
            onClick={() => setExpandedTypes(allExpanded ? new Set() : new Set(groups.map((group) => group.type)))}
          >
            {allExpanded ? "▲" : "▼"}
          </button>
        </div>

        {groups.map((group) => {
          const expanded = expandedTypes.has(group.type);
          return (
            <div className="move-type-group" key={group.type}>
              <button
                type="button"
                className="move-type-row"
                style={{ backgroundColor: TYPE_COLORS[group.type] ?? "#94A3B8" }}
                aria-expanded={expanded}
                onClick={() => toggleType(group.type)}
              >
                <strong>{TYPE_NAMES[language][group.type] ?? group.type}</strong>
                <span>{group.moves.length}</span>
              </button>
              {expanded && (
                <div className="move-rows">
                  {group.moves.map((move) => {
                    const moveExpanded = expandedMoves.has(move.move_id);
                    const highlighted = highlightedMoveId === move.move_id;
                    return (
                      <div
                        className={`move-entry${highlighted ? " highlighted" : ""}`}
                        id={`move-${move.move_id}`}
                        key={move.move_id}
                        style={highlighted ? { "--highlight-color": TYPE_COLORS[move.type] } as CSSProperties : undefined}
                      >
                        <button
                          type="button"
                          className="move-row"
                          aria-expanded={moveExpanded}
                          onClick={() => setExpandedMoves((current) => {
                            const next = new Set(current);
                            if (next.has(move.move_id)) next.delete(move.move_id);
                            else next.add(move.move_id);
                            return next;
                          })}
                        >
                          <span className="move-name-cell">
                            <TypeIcon type={move.type} />
                            <span>{localizedName(move, language)}</span>
                          </span>
                          <span><CategoryIcon category={move.category} language={language} /></span>
                          <span>{move.power ?? "–"}</span>
                          <span>{move.always_hits || move.accuracy === null ? "–" : `${move.accuracy}%`}</span>
                          <span>{moveDisplayPp(move, learnset?.learnset_source)}</span>
                          <span aria-hidden="true" />
                        </button>
                        {moveExpanded && (
                          <div className="move-description">
                            <i style={{ backgroundColor: TYPE_COLORS[move.type] ?? "#94A3B8" }} />
                            <p>{formatMoveEffect(move, language)}</p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function PokemonDetails({
  index,
  form,
  language,
  onBack,
}: {
  index: PokedexIndex;
  form: PokemonForm;
  language: Language;
  onBack: () => void;
}) {
  const text = COPY[language];
  const [selectedAbility, setSelectedAbility] = useState<string | null>(null);
  const [shiny, setShiny] = useState(false);
  const selectedAbilityRecord = selectedAbility
    ? index.abilitiesByApiName.get(selectedAbility)
    : undefined;

  return (
    <section className="detail-view">
      <button className="back-button" type="button" onClick={onBack}>{text.back}</button>
      <section className="identity-card">
        <div className="sprite-column">
          <div className="sprite-stage">
            <DetailSprite
              key={shiny ? "shiny" : "normal"}
              form={form}
              shiny={shiny}
              noSpriteText={text.noSprite}
            />
          </div>
          <label className="shiny-control">
            <input type="checkbox" checked={shiny} onChange={(event) => setShiny(event.target.checked)} />
            <span>{text.shiny}</span>
          </label>
        </div>
        <div className="identity-name">
          <p className="dex-label">{text.dex} #{String(form.national_dex).padStart(4, "0")}</p>
          <h2>{localizedName(form, language)}</h2>
          {form.name_de !== form.name_en && (
            <p className="other-name">{localizedName(form, language === "de" ? "en" : "de")}</p>
          )}
          <TypeChips types={form.types} language={language} />
        </div>
        <div className="identity-abilities">
          <h3>{text.abilities}</h3>
          <div className="ability-buttons">
            {form.abilities.map((reference) => {
              const ability = index.abilityFor(reference);
              const active = selectedAbility === reference.api_name;
              return (
                <button
                  type="button"
                  className={active ? "active" : ""}
                  aria-expanded={active}
                  key={reference.api_name}
                  onClick={() => setSelectedAbility(active ? null : reference.api_name)}
                >
                  {localizedName(ability, language)}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {selectedAbilityRecord && (
        <section className="ability-description">
          <h3>{localizedName(selectedAbilityRecord, language)}</h3>
          <p>{language === "de"
            ? selectedAbilityRecord.description_de || selectedAbilityRecord.description_en || text.abilityMissing
            : selectedAbilityRecord.description_en || text.abilityMissing}</p>
        </section>
      )}

      <StatsPanel form={form} language={language} />
      <MovesPanel index={index} form={form} language={language} />
    </section>
  );
}