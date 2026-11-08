// speed-tier-trainer-app.tsx — Speed Tier Trainer PWA V3
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { publicPath } from "../pokedex/public-path";
import {
  TrainerCatalog,
  TrainerSession,
  USAGE_LIMITS,
  calculateSpeedValues,
  displayName,
  loadTrainerBundle,
  type AnswerResult,
  type UsageLimit,
} from "./speed-tier-trainer-data";
import type { Language, PokemonForm } from "../pokedex/pokedex-data";

const COPY = {
  de: {
    subtitle: "Speed Tier Trainer",
    switchLanguage: "Switch to English",
    scope: "Pokémon-Auswahl",
    usage: "Filter",
    all: "Alle",
    top: (limit: number) => `Top ${limit}`,
    newGame: "Neues Spiel",
    question: "Frage",
    correctCount: "Richtig",
    accuracy: "Quote",
    streak: "Serie",
    form: "Form",
    prompt: "Wie hoch ist der Initiative-Basiswert?",
    placeholder: "z. B. 90",
    check: "Antwort prüfen",
    reveal: "Auflösen",
    next: "Nächstes Pokémon",
    invalid: "Bitte gib eine ganze Zahl zwischen 1 und 255 ein.",
    result: {
      exact: "Richtig!",
      low: "Zu niedrig",
      high: "Zu hoch",
      revealed: "Aufgelöst",
    },
    difference: "Abweichung",
    baseSpeed: "Base Speed",
    range: "Bereich",
    neutral: "Neutral",
    alignment: "Ausrichtung",
    maximum: "Maximum · 32 SP",
    minimum: "Minimum · 0 SP",
    choiceScarf: "Wahlschal · 32 SP",
    speedShort: "Init",
    roundComplete: "Runde abgeschlossen",
    roundScore: (correct: number, total: number) => `${correct} von ${total} richtig`,
    playAgain: "Alle erneut spielen",
    retryWrong: (count: number) => `Nur falsche erneut (${count})`,
    allCorrect: "Alle Pokémon waren richtig!",
    loading: "Trainer wird geladen …",
    loadError: "Der Speed Tier Trainer konnte nicht geladen werden.",
  },
  en: {
    subtitle: "Speed Tier Trainer",
    switchLanguage: "Wechsel zu Deutsch",
    scope: "Pokémon pool",
    usage: "Filter",
    all: "All",
    top: (limit: number) => `Top ${limit}`,
    newGame: "New game",
    question: "Question",
    correctCount: "Correct",
    accuracy: "Accuracy",
    streak: "Streak",
    form: "Form",
    prompt: "What is this Pokémon's base Speed?",
    placeholder: "e.g. 90",
    check: "Check answer",
    reveal: "Reveal",
    next: "Next Pokémon",
    invalid: "Enter a whole number between 1 and 255.",
    result: {
      exact: "Correct!",
      low: "Too low",
      high: "Too high",
      revealed: "Revealed",
    },
    difference: "Difference",
    baseSpeed: "Base Speed",
    range: "Range",
    neutral: "Neutral",
    alignment: "Alignment",
    maximum: "Maximum · 32 SP",
    minimum: "Minimum · 0 SP",
    choiceScarf: "Choice Scarf · 32 SP",
    speedShort: "Spe",
    roundComplete: "Round complete",
    roundScore: (correct: number, total: number) => `${correct} of ${total} correct`,
    playAgain: "Play all again",
    retryWrong: (count: number) => `Retry incorrect only (${count})`,
    allCorrect: "Every Pokémon was correct!",
    loading: "Loading trainer …",
    loadError: "The Speed Tier Trainer could not be loaded.",
  },
} as const;

function initialLanguage(): Language {
  const stored = window.localStorage.getItem("mishiro-speed-trainer-language");
  return stored === "en" ? "en" : "de";
}

function parseUsageLimit(value: string): UsageLimit {
  const parsed = Number(value);
  return parsed === 10 || parsed === 25 || parsed === 50 || parsed === 100
    ? parsed
    : null;
}

function pokemonSprite(pokemon: PokemonForm): string {
  return publicPath(
    pokemon.sprites.home
      ?? `assets/sprites/home/normal/${pokemon.api_name}.png`,
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="trainer-stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PokemonFormSelector({
  activePokemon,
  label,
  language,
  onChange,
  variants,
}: {
  activePokemon: PokemonForm;
  label: string;
  language: Language;
  onChange: (pokemonId: number) => void;
  variants: PokemonForm[];
}) {
  return (
    <label className="trainer-form-selector">
      <span>{label}</span>
      <select
        value={activePokemon.pokemon_id}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {variants.map((pokemon) => (
          <option key={pokemon.pokemon_id} value={pokemon.pokemon_id}>
            {displayName(pokemon, language)}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function SpeedTierTrainerApp() {
  const [language, setLanguage] = useState<Language>(initialLanguage);
  const [catalog, setCatalog] = useState<TrainerCatalog | null>(null);
  const [selectedScopeKey, setSelectedScopeKey] = useState("");
  const [selectedUsageLimit, setSelectedUsageLimit] = useState<UsageLimit>(null);
  const [gameScopeKey, setGameScopeKey] = useState("");
  const [session, setSession] = useState<TrainerSession | null>(null);
  const [fullGamePool, setFullGamePool] = useState<readonly PokemonForm[]>([]);
  const [, setRevision] = useState(0);
  const [activePokemon, setActivePokemon] = useState<PokemonForm | null>(null);
  const [answer, setAnswer] = useState("");
  const [validationError, setValidationError] = useState(false);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [loadError, setLoadError] = useState("");
  const answerInputRef = useRef<HTMLInputElement>(null);

  const text = COPY[language];

  useEffect(() => {
    const controller = new AbortController();
    void loadTrainerBundle(controller.signal)
      .then((bundle) => {
        const nextCatalog = new TrainerCatalog(bundle);
        const initialScope = nextCatalog.scopes[0].key;
        const nextSession = new TrainerSession(nextCatalog.entriesForScope(initialScope));
        setCatalog(nextCatalog);
        setSelectedScopeKey(initialScope);
        setGameScopeKey(initialScope);
        setSession(nextSession);
        setFullGamePool(nextSession.roundPokemon);
        setActivePokemon(nextSession.current);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLoadError(error instanceof Error ? error.message : COPY.de.loadError);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem("mishiro-speed-trainer-language", language);
  }, [language]);

  useEffect(() => {
    if (!result) return undefined;
    const frame = window.requestAnimationFrame(() => {
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: reducedMotion ? "auto" : "smooth",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [result]);

  const currentPokemon = session?.current ?? null;
  const formVariants = useMemo(() => {
    if (!catalog || !currentPokemon || !gameScopeKey) return [];
    return catalog.megaVariants(currentPokemon, gameScopeKey);
  }, [catalog, currentPokemon, gameScopeKey]);
  const speedValues = result && activePokemon
    ? calculateSpeedValues(activePokemon.base_stats.spe)
    : null;

  const focusAnswerInput = () => {
    const input = answerInputRef.current;
    if (!input) return;
    input.focus({ preventScroll: true });
    window.requestAnimationFrame(() => {
      input.focus({ preventScroll: true });
      input.select();
    });
  };

  const preserveAnswerFocus = (event: ReactPointerEvent<HTMLButtonElement>) => {
    if (document.activeElement === answerInputRef.current) event.preventDefault();
  };

  const activateRound = (
    pokemon: readonly PokemonForm[],
    scopeKey: string,
    finite: boolean,
  ) => {
    const nextSession = new TrainerSession(pokemon, { finite });
    setSession(nextSession);
    setGameScopeKey(scopeKey);
    setActivePokemon(nextSession.current);
    setAnswer("");
    setValidationError(false);
    setResult(null);
    setRevision((value) => value + 1);
  };

  const beginGame = () => {
    if (!catalog || !selectedScopeKey) return;
    try {
      const nextPool = catalog.entriesForScope(selectedScopeKey, selectedUsageLimit);
      setFullGamePool(nextPool);
      activateRound(nextPool, selectedScopeKey, selectedUsageLimit !== null);
      focusAnswerInput();
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : text.loadError);
    }
  };

  const acceptResult = (nextResult: AnswerResult) => {
    answerInputRef.current?.focus({ preventScroll: true });
    setResult(nextResult);
    setValidationError(false);
    setRevision((value) => value + 1);
  };

  const nextQuestion = () => {
    if (!session || !session.currentAnswered || session.isComplete) return;
    session.advance();
    setActivePokemon(session.current);
    setAnswer("");
    setValidationError(false);
    setResult(null);
    setRevision((value) => value + 1);
    focusAnswerInput();
  };

  const submitAnswer = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!session || !activePokemon) return;
    if (session.currentAnswered) {
      nextQuestion();
      return;
    }
    const guess = Number(answer.trim());
    if (!/^\d+$/.test(answer.trim()) || !Number.isInteger(guess) || guess < 1 || guess > 255) {
      setValidationError(true);
      return;
    }
    acceptResult(session.submit(guess, activePokemon));
  };

  const revealAnswer = () => {
    if (!session || session.currentAnswered || !activePokemon) return;
    acceptResult(session.submit(null, activePokemon));
  };

  const changeActivePokemon = (pokemonId: number) => {
    if (!catalog || !session) return;
    const nextPokemon = catalog.entryById(pokemonId);
    if (!nextPokemon) return;
    setActivePokemon(nextPokemon);
  };

  const replayAll = () => {
    if (!session || fullGamePool.length === 0) return;
    activateRound(fullGamePool, gameScopeKey, true);
    focusAnswerInput();
  };

  const replayIncorrect = () => {
    if (!session || session.incorrectPokemon.length === 0) return;
    activateRound(session.incorrectPokemon, gameScopeKey, true);
    focusAnswerInput();
  };

  if (loadError) {
    return (
      <main className="trainer-app-shell">
        <section className="trainer-card trainer-status-card">
          <p className="trainer-error">{loadError || text.loadError}</p>
        </section>
      </main>
    );
  }

  if (!catalog || !session || !activePokemon) {
    return (
      <main className="trainer-app-shell">
        <section className="trainer-card trainer-status-card">
          <p>{text.loading}</p>
        </section>
      </main>
    );
  }

  const accuracy = session.answered > 0
    ? `${Math.round(session.accuracy * 100)}%`
    : "—";
  const incorrectCount = session.incorrectPokemon.length;

  return (
    <main className="trainer-app-shell">
      <section className="trainer-card">
        <header className="trainer-header">
          <div>
            <p className="trainer-brand">MISHIRO</p>
            <h1>{text.subtitle}</h1>
          </div>
          <button
            type="button"
            className="trainer-language"
            onClick={() => setLanguage(language === "de" ? "en" : "de")}
          >
            {text.switchLanguage}
          </button>
        </header>

        <section className="trainer-settings" aria-label={text.scope}>
          <label>
            <span>{text.scope}</span>
            <select
              value={selectedScopeKey}
              onChange={(event) => setSelectedScopeKey(event.target.value)}
            >
              {catalog.scopes.map((scope) => (
                <option key={scope.key} value={scope.key}>
                  {catalog.scopeLabel(scope, language)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{text.usage}</span>
            <select
              value={selectedUsageLimit ?? "all"}
              onChange={(event) => setSelectedUsageLimit(parseUsageLimit(event.target.value))}
            >
              <option value="all">{text.all}</option>
              {USAGE_LIMITS.map((limit) => (
                <option key={limit} value={limit}>{text.top(limit)}</option>
              ))}
            </select>
          </label>
          <button type="button" className="trainer-secondary-button" onClick={beginGame}>
            {text.newGame}
          </button>
        </section>

        <section className="trainer-score" aria-label="Score">
          <StatCard label={text.question} value={session.questionNumber} />
          <StatCard label={text.correctCount} value={session.exact} />
          <StatCard label={text.accuracy} value={accuracy} />
          <StatCard label={text.streak} value={session.currentStreak} />
        </section>

        <section className="trainer-quiz-card">
          <img
            key={activePokemon.pokemon_id}
            className="trainer-sprite"
            src={pokemonSprite(activePokemon)}
            alt={displayName(activePokemon, language)}
            onError={(event) => {
              const image = event.currentTarget;
              if (image.dataset.fallback) return;
              image.dataset.fallback = "true";
              image.src = publicPath("assets/sprites/missingno.png");
            }}
          />
          <h2>{displayName(activePokemon, language)}</h2>

          {formVariants.length > 1 && !result && (
            <PokemonFormSelector
              activePokemon={activePokemon}
              label={text.form}
              language={language}
              onChange={changeActivePokemon}
              variants={formVariants}
            />
          )}

          <p className="trainer-prompt">{text.prompt}</p>
          <form className="trainer-answer-row" onSubmit={submitAnswer}>
            <input
              ref={answerInputRef}
              type="text"
              inputMode="numeric"
              enterKeyHint={result ? "next" : "go"}
              pattern="[0-9]*"
              maxLength={3}
              autoComplete="off"
              value={answer}
              placeholder={text.placeholder}
              aria-label={text.prompt}
              aria-readonly={result !== null}
              onChange={(event) => {
                if (result) return;
                setAnswer(event.target.value.replace(/[^0-9]/g, ""));
                setValidationError(false);
              }}
            />
            <button
              type="submit"
              className="trainer-primary-button"
              disabled={result !== null}
              onPointerDown={preserveAnswerFocus}
            >
              {text.check}
            </button>
          </form>
          {validationError && <p className="trainer-validation">{text.invalid}</p>}

          {result && speedValues && (
            <section className="trainer-result" aria-live="polite">
              {formVariants.length > 1 && (
                <PokemonFormSelector
                  activePokemon={activePokemon}
                  label={text.form}
                  language={language}
                  onChange={changeActivePokemon}
                  variants={formVariants}
                />
              )}
              <div className="trainer-result-heading">
                <div>
                  <h3 className={`trainer-result-${result.direction}`}>
                    {text.result[result.direction]}
                  </h3>
                  <p>
                    {text.difference}: {result.difference === null ? "—" : Math.abs(result.difference)}
                  </p>
                </div>
                <div className="trainer-base-speed">
                  <span>{text.baseSpeed}</span>
                  <strong>{activePokemon.base_stats.spe}</strong>
                </div>
              </div>

              <div className="trainer-speed-table">
                <strong>{text.range}</strong>
                <strong>{text.neutral}</strong>
                <strong>{text.alignment}</strong>
                <b>{text.maximum}</b>
                <span>{speedValues.maximumNeutral}</span>
                <span className="trainer-increased">
                  {speedValues.maximumIncreased} (+{text.speedShort})
                </span>
                <b>{text.minimum}</b>
                <span>{speedValues.minimumNeutral}</span>
                <span className="trainer-decreased">
                  {speedValues.minimumDecreased} (−{text.speedShort})
                </span>
                <b>{text.choiceScarf}</b>
                <span>{speedValues.choiceScarfNeutral}</span>
                <span className="trainer-increased">
                  {speedValues.choiceScarfIncreased} (+{text.speedShort})
                </span>
              </div>
            </section>
          )}

          <div className={`trainer-action-slot${session.isComplete ? " trainer-action-slot-complete" : ""}`}>
            {result && session.isComplete ? (
              <section className="trainer-round-complete" aria-live="polite">
                <h3>{text.roundComplete}</h3>
                <p>{text.roundScore(session.exact, session.answered)}</p>
                <div className="trainer-round-actions">
                  <button
                    type="button"
                    className="trainer-primary-button"
                    onPointerDown={preserveAnswerFocus}
                    onClick={replayAll}
                  >
                    {text.playAgain}
                  </button>
                  {incorrectCount > 0 ? (
                    <button
                      type="button"
                      className="trainer-secondary-button"
                      onPointerDown={preserveAnswerFocus}
                      onClick={replayIncorrect}
                    >
                      {text.retryWrong(incorrectCount)}
                    </button>
                  ) : (
                    <span className="trainer-all-correct">{text.allCorrect}</span>
                  )}
                </div>
              </section>
            ) : result ? (
              <button
                type="button"
                className="trainer-primary-button"
                onPointerDown={preserveAnswerFocus}
                onClick={nextQuestion}
              >
                {text.next}
              </button>
            ) : (
              <button
                type="button"
                className="trainer-reveal-button"
                onPointerDown={preserveAnswerFocus}
                onClick={revealAnswer}
              >
                {text.reveal}
              </button>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
