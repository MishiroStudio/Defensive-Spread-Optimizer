// pokedex-app.tsx — Pokédex V10
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  type ActiveFilter,
  type FilterKind,
  type Language,
  type PokemonForm,
  type StatKey,
  PokedexIndex,
  STAT_NAMES,
  STAT_ORDER,
  TYPE_NAMES,
  defensiveBulk,
  loadPokedexBundle,
  localizedName,
  matchRank,
  statTotal,
} from "./pokedex-data";
import PokemonDetails from "./pokedex-detail";
import { publicPath } from "./public-path";

type SearchKind = "pokemon" | FilterKind;
type SortKey = StatKey | "bulk" | "bst" | null;
type SortDirection = "asc" | "desc";

interface SearchSuggestion {
  kind: SearchKind;
  label: string;
  value: PokemonForm | string | number;
  names: string[];
}

const COPY = {
  de: {
    subtitle: "The Pokédex for VGC Players",
    switchPrompt: "Switch to",
    switchLanguage: "English",
    search: "Suche",
    searchIn: "Suche in",
    placeholder: "Pokémon, Typ, Fähigkeit, Attacke …",
    noMatch: "Kein passender Suchbegriff gefunden.",
    pokemon: "Pokémon",
    type: "Typ",
    ability: "Fähigkeit",
    move: "Attacke",
    removeAll: "Alle entfernen",
    results: (count: number) => `${count} Pokémon gefunden`,
    noResults: "Keine Pokémon erfüllen alle ausgewählten Filter.",
    abilities: "Fähigkeiten",
    stats: "Basiswerte",
    dex: "Nationaldex",
    shiny: "Shiny",
    back: "← Zurück zu den Ergebnissen",
    loadMore: "Mehr Pokémon anzeigen",
    sort: "Sortieren",
    dexOrder: "Dex Nummer",
    previousRegulations: "Frühere Regulationen",
    bulk: "Bulk",
    bst: "BST",
    ascending: "Aufsteigend",
    descending: "Absteigend",
    noSprite: "Kein Sprite verfügbar",
    abilityMissing: "Für diese Fähigkeit ist noch keine Beschreibung hinterlegt.",
    loading: "Pokédex wird geladen …",
    loadError: "Der Pokédex konnte nicht geladen werden.",
  },
  en: {
    subtitle: "The Pokédex for VGC Players",
    switchPrompt: "Wechsel zu",
    switchLanguage: "Deutsch",
    search: "Search",
    searchIn: "Search in",
    placeholder: "Pokémon, type, ability, move …",
    noMatch: "No matching search term found.",
    pokemon: "Pokémon",
    type: "Type",
    ability: "Ability",
    move: "Move",
    removeAll: "Remove all",
    results: (count: number) => `${count} Pokémon found`,
    noResults: "No Pokémon match all selected filters.",
    abilities: "Abilities",
    stats: "Base stats",
    dex: "National Dex",
    shiny: "Shiny",
    back: "← Back to results",
    loadMore: "Show more Pokémon",
    sort: "Sort",
    dexOrder: "Dex Number",
    previousRegulations: "Previous regulations",
    bulk: "Bulk",
    bst: "BST",
    ascending: "Ascending",
    descending: "Descending",
    noSprite: "No sprite available",
    abilityMissing: "No description has been stored for this ability yet.",
    loading: "Loading Pokédex …",
    loadError: "The Pokédex could not be loaded.",
  },
} as const;

const KIND_ORDER: SearchKind[] = ["pokemon", "type", "ability", "move"];
const RESULT_PAGE_SIZE = 120;

function searchKindLabel(kind: SearchKind, language: Language): string {
  return COPY[language][kind];
}

function TypeIcon({ type, size = 18 }: { type: string; size?: number }) {
  return (
    <img
      className="type-icon"
      src={publicPath(`assets/types/${type}.png`)}
      alt={TYPE_NAMES.en[type] ?? type}
      title={TYPE_NAMES.en[type] ?? type}
      width={size}
      height={size}
    />
  );
}

function CompactSprite({ form }: { form: PokemonForm }) {
  return (
    <img
      className="result-sprite"
      src={publicPath(`assets/sprites/list/normal/${form.api_name}.png`)}
      alt=""
      width="36"
      height="36"
      loading="lazy"
      onError={(event) => {
        const image = event.currentTarget;
        if (image.dataset.fallback) return;
        image.dataset.fallback = "true";
        image.src = publicPath("assets/sprites/missingno.png");
      }}
    />
  );
}

function bst(form: PokemonForm): number {
  return statTotal(form.base_stats);
}

function bulk(form: PokemonForm): number {
  return defensiveBulk(form.base_stats);
}

function AppHeader({
  language,
  onToggleLanguage,
}: {
  language: Language;
  onToggleLanguage: () => void;
}) {
  const text = COPY[language];
  return (
    <header className="app-header">
      <div className="brand-block">
        <p className="eyebrow">MISHIRO</p>
        <h1>Pokédex</h1>
        <p className="description">{text.subtitle}</p>
      </div>
      <div className="language-control">
        <span>{text.switchPrompt}</span>
        <button type="button" onClick={onToggleLanguage}>
          {text.switchLanguage}
        </button>
      </div>
    </header>
  );
}

export default function PokedexApp() {
  const [index, setIndex] = useState<PokedexIndex | null>(null);
  const [language, setLanguage] = useState<Language>("de");
  const [regulation, setRegulation] = useState("");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [inputFocused, setInputFocused] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const [searchFeedback, setSearchFeedback] = useState("");
  const [filters, setFilters] = useState<ActiveFilter[]>([]);
  const [selectedForm, setSelectedForm] = useState<PokemonForm | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [visibleCount, setVisibleCount] = useState(RESULT_PAGE_SIZE);
  const [loadError, setLoadError] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void loadPokedexBundle(controller.signal)
      .then((bundle) => {
        const nextIndex = new PokedexIndex(bundle);
        setIndex(nextIndex);
        setRegulation(nextIndex.currentRegulationId);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLoadError(error instanceof Error ? error.message : COPY.de.loadError);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem("mishiro-pokedex-language", language);
  }, [language]);

  useEffect(() => {
    const stored = window.localStorage.getItem("mishiro-pokedex-language");
    const restoreLanguage = window.setTimeout(() => {
      if (stored === "de" || stored === "en") setLanguage(stored);
    }, 0);
    return () => window.clearTimeout(restoreLanguage);
  }, []);

  useLayoutEffect(() => {
    if (!selectedForm) return;
    const scrollToTop = () => {
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    };
    scrollToTop();
    const frame = window.requestAnimationFrame(scrollToTop);
    return () => window.cancelAnimationFrame(frame);
  }, [selectedForm]);

  const text = COPY[language];
  const scopeForms = useMemo(
    () => index?.formsForRegulation(regulation) ?? [],
    [index, regulation],
  );
  const scopeEntities = useMemo(
    () => (index && query.trim() ? index.scopeEntities(scopeForms) : null),
    [index, query, scopeForms],
  );

  const suggestions = useMemo(() => {
    if (!index || !scopeEntities || !query.trim()) return [];
    const grouped: Record<SearchKind, SearchSuggestion[]> = {
      pokemon: [],
      type: [],
      ability: [],
      move: [],
    };

    for (const form of scopeForms) {
      const names = [form.api_name, form.name_de, form.name_en];
      const rank = query.trim().match(/^\d+$/)
        ? (form.national_dex === Number(query.trim()) ? 0 : null)
        : matchRank(query, names);
      if (rank !== null) {
        grouped.pokemon.push({
          kind: "pokemon",
          label: localizedName(form, language),
          value: form,
          names,
          rank,
        } as SearchSuggestion & { rank: number });
      }
    }
    for (const type of scopeEntities.types) {
      const names = [type, TYPE_NAMES.de[type] ?? "", TYPE_NAMES.en[type] ?? ""];
      const rank = matchRank(query, names);
      if (rank !== null) grouped.type.push({
        kind: "type",
        label: TYPE_NAMES[language][type] ?? type,
        value: type,
        names,
        rank,
      } as SearchSuggestion & { rank: number });
    }
    for (const abilityName of scopeEntities.abilities) {
      const ability = index.abilitiesByApiName.get(abilityName);
      const names = [abilityName, ability?.name_de ?? "", ability?.name_en ?? ""];
      const rank = matchRank(query, names);
      if (rank !== null) grouped.ability.push({
        kind: "ability",
        label: ability ? localizedName(ability, language) : abilityName,
        value: abilityName,
        names,
        rank,
      } as SearchSuggestion & { rank: number });
    }
    for (const moveId of scopeEntities.moves) {
      const move = index.movesById.get(moveId);
      if (!move) continue;
      const names = [move.api_name, move.name_de, move.name_en];
      const rank = matchRank(query, names);
      if (rank !== null) grouped.move.push({
        kind: "move",
        label: localizedName(move, language),
        value: moveId,
        names,
        rank,
      } as SearchSuggestion & { rank: number });
    }

    return KIND_ORDER.flatMap((kind) => grouped[kind]
      .toSorted((left, right) => {
        const leftRank = (left as SearchSuggestion & { rank: number }).rank;
        const rightRank = (right as SearchSuggestion & { rank: number }).rank;
        return leftRank - rightRank || left.label.localeCompare(right.label, language);
      })
      .slice(0, 8));
  }, [index, language, query, scopeEntities, scopeForms]);

  const results = useMemo(() => {
    if (!index) return [];
    const normalizedSubmittedQuery = submittedQuery.trim();
    const numericDexQuery = /^\d+$/.test(normalizedSubmittedQuery)
      ? Number(normalizedSubmittedQuery)
      : null;
    const filtered = scopeForms.filter((form) => (
      index.formMatchesFilters(form, filters)
      && (
        !normalizedSubmittedQuery
        || (numericDexQuery !== null
          ? form.national_dex === numericDexQuery
          : matchRank(normalizedSubmittedQuery, [form.api_name, form.name_de, form.name_en]) !== null)
      )
    ));
    if (!sortKey) {
      return sortDirection === "asc" ? filtered : [...filtered].reverse();
    }
    return filtered.toSorted((left, right) => {
      const leftValue = sortKey === "bst"
        ? bst(left)
        : sortKey === "bulk"
          ? bulk(left)
          : left.base_stats[sortKey];
      const rightValue = sortKey === "bst"
        ? bst(right)
        : sortKey === "bulk"
          ? bulk(right)
          : right.base_stats[sortKey];
      const delta = leftValue - rightValue;
      return sortDirection === "asc" ? delta : -delta;
    });
  }, [filters, index, scopeForms, sortDirection, sortKey, submittedQuery]);

  function filterLabel(filter: ActiveFilter): string {
    if (!index) return String(filter.value);
    if (filter.kind === "type") {
      return TYPE_NAMES[language][String(filter.value)] ?? String(filter.value);
    }
    if (filter.kind === "ability") {
      const ability = index.abilitiesByApiName.get(String(filter.value));
      return ability ? localizedName(ability, language) : String(filter.value);
    }
    const move = index.movesById.get(Number(filter.value));
    return move ? localizedName(move, language) : String(filter.value);
  }

  function chooseSuggestion(suggestion: SearchSuggestion) {
    setSearchFeedback("");
    setSubmittedQuery("");
    if (suggestion.kind === "pokemon") {
      const form = suggestion.value as PokemonForm;
      setSelectedForm(form);
      setQuery(localizedName(form, language));
      setInputFocused(false);
      return;
    }
    const nextFilter: ActiveFilter = {
      kind: suggestion.kind,
      value: suggestion.value as string | number,
    };
    setFilters((current) => (
      current.some((item) => item.kind === nextFilter.kind && String(item.value) === String(nextFilter.value))
        ? current
        : [...current, nextFilter]
    ));
    setVisibleCount(RESULT_PAGE_SIZE);
    setSelectedForm(null);
    setQuery("");
    setInputFocused(false);
    requestAnimationFrame(() => searchRef.current?.focus());
  }

  function submitSearch() {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;
    const selectedSuggestion = activeSuggestion >= 0
      ? suggestions[activeSuggestion]
      : undefined;
    const exactSuggestion = suggestions.find((suggestion) => (
      matchRank(trimmedQuery, suggestion.names) === 0
    ));
    const suggestion = selectedSuggestion ?? exactSuggestion;
    if (suggestion) {
      chooseSuggestion(suggestion);
      return;
    }
    setSubmittedQuery(trimmedQuery);
    setSelectedForm(null);
    setInputFocused(false);
    setVisibleCount(RESULT_PAGE_SIZE);
    setSearchFeedback("");
  }

  function cycleSort(nextKey: Exclude<SortKey, null>) {
    setVisibleCount(RESULT_PAGE_SIZE);
    if (sortKey !== nextKey) {
      setSortKey(nextKey);
      setSortDirection("desc");
    } else if (sortDirection === "desc") {
      setSortDirection("asc");
    } else {
      setSortKey(null);
      setSortDirection("asc");
    }
  }

  function toggleLanguage() {
    const nextLanguage = language === "de" ? "en" : "de";
    setLanguage(nextLanguage);
    if (selectedForm) setQuery(localizedName(selectedForm, nextLanguage));
  }

  if (!index) {
    return (
      <main className="app-shell">
        <section className="pokedex-card loading-card">
          <AppHeader language={language} onToggleLanguage={toggleLanguage} />
          <p className={loadError ? "status-message error-message" : "status-message"}>
            {loadError || text.loading}
          </p>
        </section>
      </main>
    );
  }

  const suggestionGroups = KIND_ORDER.map((kind) => ({
    kind,
    items: suggestions.filter((item) => item.kind === kind),
  })).filter((group) => group.items.length > 0);
  const groupedSuggestions = suggestionGroups.map((group, groupIndex) => ({
    ...group,
    offset: suggestionGroups
      .slice(0, groupIndex)
      .reduce((total, previous) => total + previous.items.length, 0),
  }));
  const regulationChoices = index.regulationChoices();
  const featuredRegulations = regulationChoices.filter((choice) => (
    choice.id === index.currentRegulationId || choice.id === "national_dex"
  ));
  const previousRegulations = regulationChoices.filter((choice) => (
    choice.id !== index.currentRegulationId && choice.id !== "national_dex"
  ));

  return (
    <main className="app-shell">
      <section className="pokedex-card">
        <AppHeader language={language} onToggleLanguage={toggleLanguage} />

        <section className="search-section" aria-labelledby="search-heading">
          <div className="section-heading-row">
            <h2 id="search-heading">{text.search}</h2>
            <label className="regulation-label">
              <span>{text.searchIn}</span>
              <select
                value={regulation}
                onChange={(event) => {
                  const next = event.target.value;
                  setRegulation(next);
                  setVisibleCount(RESULT_PAGE_SIZE);
                  setSelectedForm((current) => (
                    current && index.formInRegulation(current, next) ? current : null
                  ));
                  setSearchFeedback("");
                }}
              >
                {featuredRegulations.map((choice) => (
                  <option key={choice.id} value={choice.id}>{choice.name}</option>
                ))}
                {previousRegulations.length > 0 && (
                  <optgroup label={text.previousRegulations}>
                    {previousRegulations.map((choice) => (
                      <option key={choice.id} value={choice.id}>{choice.name}</option>
                    ))}
                  </optgroup>
                )}
              </select>
            </label>
          </div>

          <div className="global-search">
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              ref={searchRef}
              value={query}
              placeholder={text.placeholder}
              autoComplete="off"
              onFocus={() => setInputFocused(true)}
              onBlur={() => window.setTimeout(() => setInputFocused(false), 120)}
              onChange={(event) => {
                setQuery(event.target.value);
                setSubmittedQuery("");
                setSearchFeedback("");
                setActiveSuggestion(-1);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" && suggestions.length) {
                  event.preventDefault();
                  setActiveSuggestion((current) => current < 0 ? 0 : (current + 1) % suggestions.length);
                } else if (event.key === "ArrowUp" && suggestions.length) {
                  event.preventDefault();
                  setActiveSuggestion((current) => current < 0
                    ? suggestions.length - 1
                    : (current - 1 + suggestions.length) % suggestions.length);
                } else if (event.key === "Enter") {
                  event.preventDefault();
                  submitSearch();
                } else if (event.key === "Escape") {
                  setInputFocused(false);
                }
              }}
              role="combobox"
              aria-expanded={inputFocused && suggestions.length > 0}
              aria-controls="global-suggestions"
              aria-autocomplete="list"
            />
            {query && (
              <button
                className="clear-search"
                type="button"
                aria-label={language === "de" ? "Suche leeren" : "Clear search"}
                onClick={() => {
                  setQuery("");
                  setSubmittedQuery("");
                  setSearchFeedback("");
                  setSelectedForm(null);
                  searchRef.current?.focus();
                }}
              >×</button>
            )}

            {inputFocused && query.trim() && groupedSuggestions.length > 0 && (
              <div className="suggestions" id="global-suggestions" role="listbox">
                {groupedSuggestions.map((group) => {
                  return (
                    <div className="suggestion-group" key={group.kind}>
                      <p>{searchKindLabel(group.kind, language)}</p>
                      {group.items.map((suggestion, indexInGroup) => {
                        const overallIndex = group.offset + indexInGroup;
                        return (
                          <button
                            type="button"
                            role="option"
                            aria-selected={overallIndex === activeSuggestion}
                            className={overallIndex === activeSuggestion ? "active" : ""}
                            key={`${suggestion.kind}-${String(typeof suggestion.value === "object" ? suggestion.value.pokemon_id : suggestion.value)}`}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => chooseSuggestion(suggestion)}
                          >
                            <span>{suggestion.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {searchFeedback && <p className="search-feedback">{searchFeedback}</p>}

          {filters.length > 0 && (
            <div className="filter-chips" aria-label="Active filters">
              {filters.map((filter) => (
                <button
                  type="button"
                  key={`${filter.kind}-${filter.value}`}
                  onClick={() => {
                    setFilters((current) => current.filter((item) => (
                      item.kind !== filter.kind || String(item.value) !== String(filter.value)
                    )));
                    setVisibleCount(RESULT_PAGE_SIZE);
                  }}
                >
                  {searchKindLabel(filter.kind, language)}: {filterLabel(filter)} <span>×</span>
                </button>
              ))}
              {filters.length > 1 && (
                <button
                  className="clear-filters"
                  type="button"
                  onClick={() => {
                    setFilters([]);
                    setVisibleCount(RESULT_PAGE_SIZE);
                  }}
                >
                  {text.removeAll}
                </button>
              )}
            </div>
          )}
        </section>

        {selectedForm ? (
          <PokemonDetails
            key={selectedForm.pokemon_id}
            index={index}
            form={selectedForm}
            language={language}
            onBack={() => {
              setSelectedForm(null);
              setQuery("");
              setSubmittedQuery("");
            }}
            onSelectForm={(form) => {
              setSelectedForm(form);
              setQuery(localizedName(form, language));
              setSubmittedQuery("");
            }}
          />
        ) : (
          <section className="results-view">
            <div className="results-toolbar">
              <p>{text.results(results.length)}</p>
              <div className="mobile-sort">
                <label>
                  <span>{text.sort}</span>
                  <select
                    value={sortKey ?? ""}
                    onChange={(event) => {
                      const nextKey = (event.target.value || null) as SortKey;
                      setSortKey(nextKey);
                      setSortDirection(nextKey ? "desc" : "asc");
                      setVisibleCount(RESULT_PAGE_SIZE);
                    }}
                  >
                    <option value="">{text.dexOrder}</option>
                    {STAT_ORDER.map((stat) => <option key={stat} value={stat}>{STAT_NAMES[language][stat]}</option>)}
                    <option value="bulk">{text.bulk}</option>
                    <option value="bst">BST</option>
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setSortDirection((current) => current === "desc" ? "asc" : "desc");
                    setVisibleCount(RESULT_PAGE_SIZE);
                  }}
                >
                  {sortDirection === "desc" ? "↓" : "↑"}
                  <span className="sr-only">{sortDirection === "desc" ? text.descending : text.ascending}</span>
                </button>
              </div>
            </div>

            {results.length === 0 ? (
              <p className="empty-results">{text.noResults}</p>
            ) : (
              <>
                <div className="desktop-results-table">
                  <table>
                    <thead>
                      <tr>
                        <th aria-label="Sprite" />
                        <th>{text.pokemon}</th>
                        <th>{language === "de" ? "Typen" : "Types"}</th>
                        <th>{text.abilities}</th>
                        {STAT_ORDER.map((stat) => (
                          <th key={stat}>
                            <button type="button" onClick={() => cycleSort(stat)}>
                              {STAT_NAMES[language][stat]}
                              {sortKey === stat ? (sortDirection === "desc" ? " ↓" : " ↑") : ""}
                            </button>
                          </th>
                        ))}
                        <th>
                          <button type="button" onClick={() => cycleSort("bulk")}>
                            {text.bulk}{sortKey === "bulk" ? (sortDirection === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                        <th>
                          <button type="button" onClick={() => cycleSort("bst")}>
                            BST{sortKey === "bst" ? (sortDirection === "desc" ? " ↓" : " ↑") : ""}
                          </button>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.slice(0, visibleCount).map((form) => (
                        <tr key={form.pokemon_id} onClick={() => chooseSuggestion({
                          kind: "pokemon",
                          label: localizedName(form, language),
                          value: form,
                          names: [form.name_de, form.name_en, form.api_name],
                        })}>
                          <td><CompactSprite form={form} /></td>
                          <td><strong>{localizedName(form, language)}</strong></td>
                          <td><div className="result-type-icons">{form.types.map((type) => <TypeIcon key={type} type={type} />)}</div></td>
                          <td>{form.abilities.map((ability) => localizedName(index.abilityFor(ability), language)).join(", ") || "–"}</td>
                          {STAT_ORDER.map((stat) => <td key={stat}>{form.base_stats[stat]}</td>)}
                          <td>{bulk(form)}</td>
                          <td>{bst(form)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mobile-result-cards">
                  {results.slice(0, visibleCount).map((form) => (
                    <button
                      type="button"
                      className="result-card"
                      key={form.pokemon_id}
                      onClick={() => chooseSuggestion({
                        kind: "pokemon",
                        label: localizedName(form, language),
                        value: form,
                        names: [form.name_de, form.name_en, form.api_name],
                      })}
                    >
                      <span className="result-card-visual">
                        <CompactSprite form={form} />
                        <span className="result-type-icons">
                          {form.types.map((type) => <TypeIcon key={type} type={type} />)}
                        </span>
                      </span>
                      <span className="result-card-main">
                        <span className="result-card-title">
                          <strong>{localizedName(form, language)}</strong>
                          <small>#{String(form.national_dex).padStart(4, "0")}</small>
                        </span>
                        <span className="result-abilities">
                          {form.abilities.map((ability) => localizedName(index.abilityFor(ability), language)).join(" · ") || "–"}
                        </span>
                        <span className="result-stats">
                          {STAT_ORDER.map((stat) => (
                            <span key={stat}><small>{STAT_NAMES[language][stat]}</small>{form.base_stats[stat]}</span>
                          ))}
                          <span><small>{text.bulk}</small>{bulk(form)}</span>
                          <span><small>BST</small>{bst(form)}</span>
                        </span>
                      </span>
                    </button>
                  ))}
                </div>

                {visibleCount < results.length && (
                  <button className="load-more" type="button" onClick={() => setVisibleCount((current) => current + RESULT_PAGE_SIZE)}>
                    {text.loadMore}
                  </button>
                )}
              </>
            )}
          </section>
        )}
      </section>
    </main>
  );
}
