// speed-tier-trainer-app.tsx — Speed Tier Trainer PWA V1
import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
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

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface NavigatorWithStandalone extends Navigator {
  standalone?: boolean;
}

const COPY = {
  de: {
    subtitle: "Speed Tier Trainer",
    switchLanguage: "Switch to English",
    install: "App installieren",
    scope: "Pokémon-Auswahl",
    usage: "Nutzungsfilter",
    all: "Alle",
    top: (limit: number) => `Top ${limit}`,
    newGame: "Neues Spiel",
    question: "Frage",
    correctCount: "Richtig",
    accuracy: "Trefferquote",
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
    speedShort: "Init",
    loading: "Trainer wird geladen …",
    loadError: "Der Speed Tier Trainer konnte nicht geladen werden.",
    usageSource: (month: string, cutoff: number) => (
      `Showdown Usage · ${month} · Rating ${cutoff}`
    ),
    installTitle: "Speed Trainer installieren",
    installIos: "Tippe in Safari auf Teilen und anschließend auf „Zum Home-Bildschirm“.",
    installOther: "Öffne das Browser-Menü und wähle „App installieren“ oder „Zum Startbildschirm hinzufügen“.",
    close: "Schließen",
  },
  en: {
    subtitle: "Speed Tier Trainer",
    switchLanguage: "Wechsel zu Deutsch",
    install: "Install app",
    scope: "Pokémon pool",
    usage: "Usage filter",
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
    speedShort: "Spe",
    loading: "Loading trainer …",
    loadError: "The Speed Tier Trainer could not be loaded.",
    usageSource: (month: string, cutoff: number) => (
      `Showdown usage · ${month} · rating ${cutoff}`
    ),
    installTitle: "Install Speed Trainer",
    installIos: "In Safari, tap Share and then “Add to Home Screen”.",
    installOther: "Open the browser menu and choose “Install app” or “Add to Home screen”.",
    close: "Close",
  },
} as const;

function initialLanguage(): Language {
  const stored = window.localStorage.getItem("mishiro-speed-trainer-language");
  return stored === "en" ? "en" : "de";
}

function parseUsageLimit(value: string): UsageLimit {
  const parsed = Number(value);
  return parsed === 10 || parsed === 50 || parsed === 100 ? parsed : null;
}

function isStandalone(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches
    || Boolean((window.navigator as NavigatorWithStandalone).standalone);
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

export default function SpeedTierTrainerApp() {
  const [language, setLanguage] = useState<Language>(initialLanguage);
  const [catalog, setCatalog] = useState<TrainerCatalog | null>(null);
  const [selectedScopeKey, setSelectedScopeKey] = useState("");
  const [selectedUsageLimit, setSelectedUsageLimit] = useState<UsageLimit>(null);
  const [gameScopeKey, setGameScopeKey] = useState("");
  const [session, setSession] = useState<TrainerSession | null>(null);
  const [, setRevision] = useState(0);
  const [activePokemon, setActivePokemon] = useState<PokemonForm | null>(null);
  const [answer, setAnswer] = useState("");
  const [validationError, setValidationError] = useState(false);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [loadError, setLoadError] = useState("");
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(isStandalone);
  const [showInstallHelp, setShowInstallHelp] = useState(false);

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
    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const currentPokemon = session?.current ?? null;
  const formVariants = useMemo(() => {
    if (!catalog || !currentPokemon || !gameScopeKey) return [];
    return catalog.megaVariants(currentPokemon, gameScopeKey);
  }, [catalog, currentPokemon, gameScopeKey]);
  const selectedUsageDataset = catalog?.usageDatasetForScope(selectedScopeKey) ?? null;
  const speedValues = result ? calculateSpeedValues(result.pokemon.base_stats.spe) : null;

  const beginGame = () => {
    if (!catalog || !selectedScopeKey) return;
    try {
      const nextSession = new TrainerSession(
        catalog.entriesForScope(selectedScopeKey, selectedUsageLimit),
      );
      setSession(nextSession);
      setGameScopeKey(selectedScopeKey);
      setActivePokemon(nextSession.current);
      setAnswer("");
      setValidationError(false);
      setResult(null);
      setRevision((value) => value + 1);
    } catch (error: unknown) {
      setLoadError(error instanceof Error ? error.message : text.loadError);
    }
  };

  const acceptResult = (nextResult: AnswerResult) => {
    setResult(nextResult);
    setValidationError(false);
    setRevision((value) => value + 1);
  };

  const submitAnswer = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!session || session.currentAnswered || !activePokemon) return;
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

  const nextQuestion = () => {
    if (!session || !session.currentAnswered) return;
    session.advance();
    setActivePokemon(session.current);
    setAnswer("");
    setValidationError(false);
    setResult(null);
    setRevision((value) => value + 1);
  };

  const requestInstall = async () => {
    if (!installPrompt) {
      setShowInstallHelp(true);
      return;
    }
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
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
  const isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent);

  return (
    <main className="trainer-app-shell">
      <section className="trainer-card">
        <header className="trainer-header">
          <div>
            <p className="trainer-brand">MISHIRO</p>
            <h1>{text.subtitle}</h1>
          </div>
          <div className="trainer-header-actions">
            {!installed && (
              <button type="button" className="trainer-install" onClick={() => void requestInstall()}>
                {text.install}
              </button>
            )}
            <button
              type="button"
              className="trainer-language"
              onClick={() => setLanguage(language === "de" ? "en" : "de")}
            >
              {text.switchLanguage}
            </button>
          </div>
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
              title={selectedUsageDataset
                ? text.usageSource(selectedUsageDataset.month, selectedUsageDataset.rating_cutoff)
                : ""}
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

          {formVariants.length > 1 && (
            <label className="trainer-form-selector">
              <span>{text.form}</span>
              <select
                value={activePokemon.pokemon_id}
                disabled={result !== null}
                onChange={(event) => {
                  const nextPokemon = catalog.entryById(Number(event.target.value));
                  if (nextPokemon) setActivePokemon(nextPokemon);
                }}
              >
                {formVariants.map((pokemon) => (
                  <option key={pokemon.pokemon_id} value={pokemon.pokemon_id}>
                    {displayName(pokemon, language)}
                  </option>
                ))}
              </select>
            </label>
          )}

          <p className="trainer-prompt">{text.prompt}</p>
          <form className="trainer-answer-row" onSubmit={submitAnswer}>
            <input
              type="text"
              inputMode="numeric"
              enterKeyHint={result ? "next" : "done"}
              pattern="[0-9]*"
              maxLength={3}
              value={answer}
              placeholder={text.placeholder}
              aria-label={text.prompt}
              disabled={result !== null}
              onChange={(event) => {
                setAnswer(event.target.value.replace(/[^0-9]/g, ""));
                setValidationError(false);
              }}
            />
            <button type="submit" className="trainer-primary-button" disabled={result !== null}>
              {text.check}
            </button>
          </form>
          {validationError && <p className="trainer-validation">{text.invalid}</p>}

          {result && speedValues && (
            <section className="trainer-result" aria-live="polite">
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
                  <strong>{result.pokemon.base_stats.spe}</strong>
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
              </div>
            </section>
          )}

          <div className="trainer-action-slot">
            {result ? (
              <button type="button" className="trainer-primary-button" onClick={nextQuestion}>
                {text.next}
              </button>
            ) : (
              <button type="button" className="trainer-reveal-button" onClick={revealAnswer}>
                {text.reveal}
              </button>
            )}
          </div>
        </section>

        {selectedUsageDataset && (
          <p className="trainer-source-note">
            {text.usageSource(selectedUsageDataset.month, selectedUsageDataset.rating_cutoff)}
          </p>
        )}
      </section>

      {showInstallHelp && (
        <div className="trainer-modal-backdrop" role="presentation" onClick={() => setShowInstallHelp(false)}>
          <section
            className="trainer-install-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="install-dialog-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="install-dialog-title">{text.installTitle}</h2>
            <p>{isIos ? text.installIos : text.installOther}</p>
            <button type="button" className="trainer-primary-button" onClick={() => setShowInstallHelp(false)}>
              {text.close}
            </button>
          </section>
        </div>
      )}
    </main>
  );
}
