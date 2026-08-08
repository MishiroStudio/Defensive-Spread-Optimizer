"""Cordy's Lab move importer — version 3.

Build ``data/moves.json`` for the Pokédex from Pokémon Showdown.

The database contains the union of moves available in:

1. Pokémon Champions
2. Scarlet/Violet
3. Sword/Shield
4. Brilliant Diamond/Shining Pearl

If a move exists in several sources, its displayed values come from the first
source in that order. Pokémon Showdown's own Dex loader is used so inherited
move data and Champions overrides are resolved correctly.

The importer also adds:
- official German move names from PokéAPI, with a small manual supplement;
- English Showdown short descriptions as ``effects.summary_en``;
- German short descriptions as ``effects.summary_de`` from the built-in
  translation catalog below.

The German summary catalog is deliberately part of this single importer file.
If a future Showdown update introduces a new or changed short description, the
English text is kept as a temporary fallback and the final console output will
report ``German-summary fallbacks`` greater than zero.

Run from the project root with:

    python3 tools/import_moves_v3.py

The normal import writes ``data/moves.json``. A limited test import writes
``data/moves_preview.json`` so preview data cannot overwrite the full file.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"
SHOWDOWN_PACKAGE_METADATA_URL = (
    "https://registry.npmjs.org/pokemon-showdown/latest"
)

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
OUTPUT_FILE = DATA_DIRECTORY / "moves.json"
PREVIEW_OUTPUT_FILE = DATA_DIRECTORY / "moves_preview.json"

REQUEST_TIMEOUT_SECONDS = 60
MAX_REQUEST_ATTEMPTS = 6
RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
USER_AGENT = "Cordys-Lab-Pokedex/0.2"


# First match wins. This is the value priority, not the learnset priority.
MOVE_VALUE_SOURCES = (
    {
        "key": "champions",
        "showdown_mod": "champions",
        "label": "Pokémon Champions",
    },
    {
        "key": "scarlet-violet",
        "showdown_mod": "gen9",
        "label": "Scarlet/Violet",
    },
    {
        "key": "sword-shield",
        "showdown_mod": "gen8",
        "label": "Sword/Shield",
    },
    {
        "key": "bdsp",
        "showdown_mod": "gen8bdsp",
        "label": "Brilliant Diamond/Shining Pearl",
    },
)

VALUE_SOURCE_KEYS = {source["key"] for source in MOVE_VALUE_SOURCES}
VALUE_SOURCE_MODS = {
    source["key"]: source["showdown_mod"]
    for source in MOVE_VALUE_SOURCES
}


# PokéAPI currently omits German names for these Hisui/Paldea moves.
GERMAN_MOVE_NAME_SUPPLEMENTS = {
    827: "Unheilsklauen",
    828: "Barrierenstoß",
    829: "Kraftwechsel",
    830: "Felsaxt",
    831: "Frühlingsorkan",
    832: "Mythenkraft",
    833: "Flammenwut",
    834: "Wellentackle",
    835: "Chlorostrahl",
    836: "Frostfallwind",
    837: "Siegestanz",
    838: "Schmetterramme",
    839: "Giftstachelregen",
    840: "Auraschwingen",
    841: "Niedertracht",
    842: "Refugium",
    843: "Drillingspfeile",
    844: "Phantomparade",
    845: "Klingenschwall",
    846: "Polarorkan",
    847: "Donnerorkan",
    848: "Wüstenorkan",
    849: "Lunargebet",
    850: "Mutschub",
    851: "Tera-Ausbruch",
    852: "Fadenfalle",
    853: "Fersenkick",
    854: "Letzte Ehre",
    855: "Lichteinschlag",
    856: "Auftischen",
    857: "Düsenhieb",
    858: "Chili-Essenz",
    859: "Reifendrehung",
    860: "Mäuseplage",
    861: "Eiskreisel",
    862: "Großklingenstoß",
    863: "Vitalsegen",
    864: "Pökelsalz",
    865: "Tauchtriade",
    866: "Letalwirbler",
    867: "Abpausen",
    868: "Abspaltung",
    869: "Kniefallspalter",
    870: "Blumentrick",
    871: "Loderlied",
    872: "Wogentanz",
    873: "Rasender Stier",
    874: "Goldrausch",
    875: "Psychoschneide",
    876: "Hydrodampf",
    877: "Verderben",
    878: "Kollisionskurs",
    879: "Blitztour",
    880: "Schwanzabwurf",
    881: "Eisige Stimmung",
    882: "Aufräumen",
    883: "Schneelandschaft",
    884: "Anspringen",
    885: "Wegbereiter",
    886: "Kalte Dusche",
    887: "Hyperbohrer",
    888: "Doppelstrahl",
    889: "Zornesfaust",
    890: "Rüstungskanone",
    891: "Reueschwert",
    892: "Zweifachladung",
    893: "Riesenhammer",
    894: "Vendetta",
    895: "Aquaschnitt",
    901: "Blutmond",
    902: "Quirlschuss",
    903: "Sirupbombe",
    904: "Rankenkeule",
}


# German translations of Pokémon Showdown shortDesc strings.
# Kept directly in this importer so no extra translation module is required.
SUMMARY_DE_TRANSLATIONS: dict[str, str] = {'Scatters coins.': 'Verstreut Münzen.', 'Power doubles during Bounce, Fly, and Sky Drop.': 'Die Stärke verdoppelt sich gegen Ziele, die Sprungfeder, Fliegen oder Freier Fall einsetzen.', 'Flies up on first turn, then strikes the next turn.': 'Der Anwender fliegt in Runde 1 hoch und greift in Runde 2 an.', 'Lasts 2-3 turns. Confuses the user afterwards.': 'Dauert 2–3 Runden. Anschließend wird der Anwender verwirrt.', "For 4 turns, disables the target's last move used.": 'Blockiert für 4 Runden die zuletzt eingesetzte Attacke des Ziels.', "For 5 turns, protects user's party from stat drops.": 'Schützt das Team des Anwenders 5 Runden lang vor Senkungen der Statuswerte.', 'Hits adjacent Pokemon. Double damage on Dive.': 'Trifft alle angrenzenden Pokémon. Verursacht doppelten Schaden gegen ein Ziel, das Taucher einsetzt.', "10% chance to freeze foe(s). Can't miss in Snow.": '10% Chance, Gegner einzufrieren. Trifft bei Schnee immer.', 'User cannot move next turn.': 'Der Anwender muss in der nächsten Runde aussetzen.', 'More power the heavier the target.': 'Je schwerer das Ziel, desto höher die Stärke.', 'If hit by physical attack, returns double damage.': 'Wurde der Anwender von einer physischen Attacke getroffen, fügt er den doppelten erlittenen Schaden zu.', "1/8 of target's HP is restored to user every turn.": 'Entzieht dem Ziel jede Runde 1/8 seiner maximalen KP und heilt den Anwender entsprechend.', "Raises user's Attack and Sp. Atk by 1; 2 in Sun.": 'Erhöht Angriff und Sp.-Ang. des Anwenders um 1 Stufe, bei Sonne um 2 Stufen.', 'Charges turn 1. Hits turn 2. No charge in sunlight.': 'Lädt in Runde 1 auf und greift in Runde 2 an. Bei Sonne entfällt die Aufladerunde.', "30% chance to paralyze. Can't miss in rain.": '30% Chance, das Ziel zu paralysieren. Trifft bei Regen immer.', 'Hits adjacent Pokemon. Double damage on Dig.': 'Trifft alle angrenzenden Pokémon. Verursacht doppelten Schaden gegen ein Ziel, das Schaufler einsetzt.', 'Digs underground turn 1, strikes turn 2.': 'Der Anwender gräbt sich in Runde 1 ein und greift in Runde 2 an.', 'Usually goes first.': 'Kein zusätzlicher Effekt.', 'User switches out.': 'Der Anwender wechselt aus.', 'The last move the target used replaces this one.': 'Ersetzt diese Attacke durch die zuletzt vom Ziel eingesetzte Attacke.', 'For 5 turns, special damage to allies is halved.': 'Halbiert 5 Runden lang den speziellen Schaden gegen das eigene Team.', 'Eliminates all stat changes.': 'Setzt alle Statuswertveränderungen aller aktiven Pokémon zurück.', 'For 5 turns, physical damage to allies is halved.': 'Halbiert 5 Runden lang den physischen Schaden gegen das eigene Team.', "Raises the user's critical hit ratio by 2.": 'Erhöht die Volltrefferquote des Anwenders um 2 Stufen.', 'Picks a random move.': 'Setzt eine zufällige Attacke ein.', 'This move does not check accuracy. Hits foes.': 'Trifft garantiert. Trifft beide Gegner.', "Raises user's Defense by 1 on turn 1. Hits turn 2.": 'Erhöht in Runde 1 die Verteidigung des Anwenders um 1 Stufe und greift in Runde 2 an.', 'User is hurt by 50% of its max HP if it misses.': 'Verliert der Anwender beim Verfehlen 50% seiner maximalen KP.', 'User gains 1/2 HP inflicted. Sleeping target only.': 'Heilt den Anwender um 50% des verursachten Schadens. Funktioniert nur gegen schlafende Ziele.', 'Charges, then hits turn 2. 30% flinch. High crit.': 'Lädt eine Runde auf und greift in Runde 2 an. 30% Zurückschreck-Chance und erhöhte Volltrefferquote.', "Copies target's stats, moves, types, and Ability.": 'Kopiert Statuswerte, Attacken, Typen und Fähigkeit des Ziels.', 'No competitive use.': 'Hat keinen zusätzlichen Kampfeffekt.', 'User sleeps 2 turns and restores HP and status.': 'Der Anwender schläft 2 Runden und stellt dabei KP sowie Statusprobleme vollständig wieder her.', "Changes user's type to match its first move.": 'Ändert den Typ des Anwenders passend zu seiner ersten Attacke.', '20% chance to paralyze or burn or freeze target.': '20% Chance, das Ziel zu paralysieren, zu verbrennen oder einzufrieren.', "Does damage equal to 1/2 target's current HP.": 'Verursacht Schaden in Höhe der Hälfte der aktuellen KP des Ziels.', 'User takes 1/4 its max HP to put in a substitute.': 'Der Anwender verliert 1/4 seiner maximalen KP und erzeugt einen Delegator.', 'User loses 1/4 of its max HP.': 'Der Anwender verliert 1/4 seiner maximalen KP.', 'Permanently copies the last move target used.': 'Kopiert dauerhaft die zuletzt vom Ziel eingesetzte Attacke.', 'Hits 3 times. Each hit can miss, but power rises.': 'Trifft 3-mal. Jeder Treffer kann verfehlen; die Stärke steigt mit jedem Treffer.', "If the user has no item, it steals the target's.": 'Hat der Anwender kein Item, stiehlt er das Item des Ziels.', "User's next move will not miss the target.": 'Die nächste Attacke des Anwenders gegen dieses Ziel trifft sicher.', 'User must be asleep. 30% chance to flinch target.': 'Der Anwender muss schlafen. 30% Chance, das Ziel zurückschrecken zu lassen.', 'Curses if Ghost, else -1 Spe, +1 Atk, +1 Def.': 'Als Geist verflucht der Anwender das Ziel; sonst Initiative −1 sowie Angriff und Verteidigung +1.', 'More power the less HP the user has left.': 'Je weniger KP der Anwender hat, desto höher die Stärke.', "Changes user's type to resist target's last move.": 'Ändert den Typ des Anwenders so, dass er die zuletzt eingesetzte Attacke des Ziels resistiert.', "Lowers the PP of the target's last move by 4.": 'Senkt die AP der zuletzt eingesetzten Attacke des Ziels um 4.', 'Prevents moves from affecting the user this turn.': 'Schützt den Anwender in dieser Runde vor Attacken.', 'User loses 50% max HP. Maximizes Attack.': 'Der Anwender verliert 50% seiner maximalen KP und maximiert seinen Angriff.', 'Hurts grounded foes on switch-in. Max 3 layers.': 'Schädigt eingewechselte, geerdete Gegner. Kann bis zu 3 Schichten gelegt werden.', 'If an opponent knocks out the user, it also faints.': 'Wird der Anwender durch einen Gegner besiegt, wird dieser ebenfalls kampfunfähig.', 'All active Pokemon will faint in 3 turns.': 'Alle aktiven Pokémon werden nach 3 Runden kampfunfähig.', 'User survives attacks this turn with at least 1 HP.': 'Der Anwender überlebt in dieser Runde Angriffe mit mindestens 1 KP.', 'Power doubles with each hit. Repeats for 5 turns.': 'Die Stärke verdoppelt sich mit jedem Treffer. Wird bis zu 5 Runden lang wiederholt.', 'Always leaves the target with at least 1 HP.': 'Lässt dem Ziel immer mindestens 1 KP.', 'Power doubles with each hit, up to 160.': 'Die Stärke verdoppelt sich bei aufeinanderfolgenden Treffern bis maximal 160.', 'Prevents the target from switching out.': 'Verhindert, dass das Ziel auswechselt.', 'A target of the opposite gender gets infatuated.': 'Ein Ziel des anderen Geschlechts wird vernarrt.', 'User must be asleep. Uses another known move.': 'Der Anwender muss schlafen und setzt zufällig eine seiner anderen bekannten Attacken ein.', "Cures the user's party of all status conditions.": 'Heilt alle Statusprobleme im Team des Anwenders.', '40, 80, 120 power, or heals target 1/4 max HP.': 'Hat 40, 80 oder 120 Stärke oder heilt das Ziel um 1/4 seiner maximalen KP.', "For 5 turns, protects user's party from status.": 'Schützt das Team des Anwenders 5 Runden lang vor Statusproblemen.', 'Shares HP of user and target equally.': 'Gleicht die KP von Anwender und Ziel an.', 'User switches, passing stat changes and more.': 'Der Anwender wechselt aus und überträgt dabei Statuswertveränderungen und weitere Effekte.', 'Free user from hazards/bind/Leech Seed; +1 Spe.': 'Entfernt Gefahren, Fessel- und Egelsamen-Effekte vom Anwender und erhöht seine Initiative um 1 Stufe.', 'This move does not check accuracy. Goes last.': 'Trifft garantiert.', 'Heals the user by a weather-dependent amount.': 'Heilt den Anwender abhängig vom Wetter.', "Varies in type based on the user's IVs.": 'Der Typ hängt von den DVs des Anwenders ab.', 'If hit by special attack, returns double damage.': 'Wurde der Anwender von einer speziellen Attacke getroffen, fügt er den doppelten erlittenen Schaden zu.', "Copies the target's current stat stages.": 'Kopiert die aktuellen Statuswertveränderungen des Ziels.', 'Nearly always goes first.': 'Kein zusätzlicher Effekt.', 'Hits two turns after being used.': 'Trifft das Ziel zwei Runden nach dem Einsatz.', 'All healthy allies aid in damaging the target.': 'Alle nicht kampfunfähigen Teammitglieder helfen dabei, dem Ziel Schaden zuzufügen.', 'Hits first. First turn out only. 100% flinch chance.': 'Funktioniert nur in der ersten Runde nach dem Einwechseln und lässt das Ziel sicher zurückschrecken.', 'Lasts 3 turns. Active Pokemon cannot fall asleep.': 'Dauert 3 Runden. Aktive Pokémon können währenddessen nicht einschlafen.', "Raises user's Defense, Sp. Def by 1. Max 3 uses.": 'Erhöht Verteidigung und Sp.-Vert. des Anwenders um 1 Stufe. Maximal 3-mal stapelbar.', 'More power with more uses of Stockpile.': 'Die Stärke steigt mit der Anzahl eingesetzter Horter.', 'Heals the user based on uses of Stockpile.': 'Heilt den Anwender abhängig von der Anzahl eingesetzter Horter.', "Target can't select the same move twice in a row.": 'Das Ziel kann nicht zweimal hintereinander dieselbe Attacke auswählen.', 'Power doubles if user is burn/poison/paralyzed.': 'Die Stärke verdoppelt sich, wenn der Anwender verbrannt, vergiftet oder paralysiert ist.', 'Fails if the user takes damage before it hits.': 'Schlägt fehl, wenn der Anwender vor dem Angriff Schaden erleidet.', "The foes' moves target the user on the turn used.": 'Attacken der Gegner werden in dieser Runde auf den Anwender umgelenkt.', 'Attack depends on terrain (default Tri Attack).': 'Die eingesetzte Attacke hängt vom Feld ab; standardmäßig wird Triplette eingesetzt.', "One adjacent ally's move power is 1.5x this turn.": 'Erhöht in dieser Runde die Stärke der Attacke eines angrenzenden Verbündeten auf das 1,5-Fache.', "User switches its held item with the target's.": 'Tauscht das gehaltene Item des Anwenders mit dem des Ziels.', "User replaces its Ability with the target's.": 'Ersetzt die Fähigkeit des Anwenders durch die Fähigkeit des Ziels.', "Next turn, 50% of the user's max HP is restored.": 'In der nächsten Runde werden 50% der maximalen KP des Anwenders wiederhergestellt.', 'Bounces back certain non-damaging moves.': 'Wirft bestimmte Status-Attacken auf den Anwender zurück.', 'Restores the item the user last used.': 'Stellt das zuletzt verbrauchte Item des Anwenders wieder her.', 'Power doubles if user is damaged by the target.': 'Die Stärke verdoppelt sich, wenn der Anwender zuvor vom Ziel Schaden erlitten hat.', 'Destroys screens, unless the target is immune.': 'Entfernt Lichtschild, Reflektor und ähnliche Schilde, sofern das Ziel nicht immun ist.', 'Puts the target to sleep after 1 turn.': 'Lässt das Ziel am Ende der nächsten Runde einschlafen.', '1.5x damage if foe holds an item. Removes item.': 'Verursacht 1,5-fachen Schaden, wenn das Ziel ein Item trägt, und entfernt dieses.', "Lowers the target's HP to the user's HP.": 'Senkt die KP des Ziels auf die aktuellen KP des Anwenders.', "Less power as user's HP decreases. Hits foe(s).": 'Die Stärke sinkt mit den KP des Anwenders. Trifft beide Gegner.', 'The user and the target trade Abilities.': 'Anwender und Ziel tauschen ihre Fähigkeiten.', 'No foe can use any move known by the user.': 'Gegner können keine Attacke einsetzen, die der Anwender ebenfalls beherrscht.', 'If the user faints, the attack used loses all its PP.': 'Wird der Anwender besiegt, verliert die verursachende Attacke alle AP.', 'Dives underwater turn 1, strikes turn 2.': 'Der Anwender taucht in Runde 1 unter und greift in Runde 2 an.', 'No additional effect. Hits adjacent foes.': 'Kein zusätzlicher Effekt. Trifft beide Gegner.', 'Power doubles and type varies in each weather.': 'Stärke verdoppelt sich und der Typ hängt vom aktuellen Wetter ab.', 'This move does not check accuracy.': 'Trifft garantiert.', 'Bounces turn 1. Hits turn 2. 30% paralyze.': 'Springt in Runde 1 hoch und greift in Runde 2 an. 30% Chance auf Paralyse.', '5 turns: no Ground immunities, 1.67x accuracy.': 'Für 5 Runden entfallen Boden-Immunitäten und die Genauigkeit wird auf das 1,67-Fache erhöht.', 'More power the slower the user than the target.': 'Je langsamer der Anwender im Vergleich zum Ziel ist, desto höher die Stärke.', 'User faints. Next hurt Pokemon is fully healed.': 'Der Anwender wird kampfunfähig. Das nächste eingewechselte verletzte Pokémon wird vollständig geheilt.', "Power doubles if the target's HP is 50% or less.": 'Die Stärke verdoppelt sich, wenn das Ziel höchstens 50% seiner KP hat.', "User steals and eats the target's Berry.": 'Der Anwender stiehlt und verzehrt die Beere des Ziels.', "For 4 turns, allies' Speed is doubled.": 'Verdoppelt 4 Runden lang die Initiative des eigenen Teams.', 'Raises a random stat of the user or an ally by 2.': 'Erhöht einen zufälligen Statuswert des Anwenders oder eines Verbündeten um 2 Stufen.', 'If hit by an attack, returns 1.5x damage.': 'Wurde der Anwender von einer Attacke getroffen, fügt er das 1,5-Fache des erlittenen Schadens zu.', 'Power doubles if the user moves after the target.': 'Die Stärke verdoppelt sich, wenn der Anwender nach dem Ziel handelt.', 'Power doubles if target was damaged this turn.': 'Die Stärke verdoppelt sich, wenn das Ziel in dieser Runde bereits Schaden erlitten hat.', "Flings the user's item at the target. Power varies.": 'Schleudert das gehaltene Item auf das Ziel. Die Stärke hängt vom Item ab.', "Transfers the user's status ailment to the target.": 'Überträgt das Statusproblem des Anwenders auf das Ziel.', "Switches user's Attack and Defense stats.": 'Vertauscht Angriff und Verteidigung des Anwenders.', "Nullifies the target's Ability.": 'Unterdrückt die Fähigkeit des Ziels.', 'Uses the last move used in the battle.': 'Setzt die zuletzt im Kampf eingesetzte Attacke ein.', 'Swaps Attack and Sp. Atk stat stages with target.': 'Tauscht die Veränderungen von Angriff und Sp.-Ang. mit dem Ziel.', 'Swaps Defense and Sp. Def changes with target.': 'Tauscht die Veränderungen von Verteidigung und Sp.-Vert. mit dem Ziel.', 'Fails unless each known move has been used.': 'Schlägt fehl, solange nicht jede bekannte Attacke des Anwenders mindestens einmal eingesetzt wurde.', "The target's Ability becomes Insomnia.": 'Ändert die Fähigkeit des Ziels zu Insomnia.', 'Usually goes first. Fails if target is not attacking.': 'Schlägt fehl, wenn das Ziel keine Schadensattacke einsetzt.', 'Poisons grounded foes on switch-in. Max 2 layers.': 'Vergiftet eingewechselte, geerdete Gegner. Kann bis zu 2 Schichten gelegt werden.', 'Swaps all stat changes with target.': 'Tauscht alle Statuswertveränderungen mit dem Ziel.', 'For 5 turns, the user has immunity to Ground.': 'Verleiht dem Anwender 5 Runden lang Immunität gegen Boden-Attacken.', '-1 evasion; ends user and target hazards/terrain.': 'Senkt den Ausweichwert um 1 Stufe und entfernt Gefahren sowie Felder auf beiden Seiten.', 'Goes last. For 5 turns, turn order is reversed.': 'Kehrt 5 Runden lang die Zugreihenfolge um.', 'Hurts foes on switch-in. Factors Rock weakness.': 'Schädigt Gegner beim Einwechseln abhängig von ihrer Gestein-Schwäche.', 'Type varies based on the held Plate.': 'Der Typ hängt von der gehaltenen Tafel ab.', 'User faints. Next hurt Pkmn is cured, max HP/PP.': 'Der Anwender wird kampfunfähig. Das nächste verletzte Pokémon wird geheilt und erhält volle KP und AP.', 'More power the more HP the target has left.': 'Je mehr KP das Ziel noch hat, desto höher die Stärke.', 'Darkrai: Causes the foe(s) to fall asleep.': 'Darkrai lässt die Gegner einschlafen.', 'Disappears turn 1. Hits turn 2. Breaks protection.': 'Verschwindet in Runde 1 und greift in Runde 2 an. Durchbricht Schutz-Attacken.', 'Protects allies from multi-target moves this turn.': 'Schützt Verbündete in dieser Runde vor Mehrziel-Attacken.', 'Averages Defense and Sp. Def stats with target.': 'Setzt Verteidigung und Sp.-Vert. von Anwender und Ziel jeweils auf ihren Mittelwert.', 'Averages Attack and Sp. Atk stats with target.': 'Setzt Angriff und Sp.-Ang. von Anwender und Ziel jeweils auf ihren Mittelwert.', 'For 5 turns, all Defense and Sp. Def stats switch.': 'Vertauscht 5 Runden lang bei allen Pokémon Verteidigung und Sp.-Vert.', 'Damages target based on Defense, not Sp. Def.': 'Berechnet den Schaden anhand der Verteidigung des Ziels statt seiner Sp.-Vert.', 'Power doubles if the target is poisoned.': 'Die Stärke verdoppelt sich, wenn das Ziel vergiftet ist.', "Raises the user's Speed by 2; user loses 100 kg.": 'Erhöht die Initiative des Anwenders um 2 Stufen und reduziert sein Gewicht um 100 kg.', 'For 5 turns, all held items have no effect.': 'Deaktiviert 5 Runden lang die Effekte aller gehaltenen Items.', "Removes the target's Ground immunity.": 'Entfernt die Boden-Immunität des Ziels.', 'More power the heavier the user than the target.': 'Je schwerer der Anwender im Vergleich zum Ziel ist, desto höher die Stärke.', 'More power the faster the user is than the target.': 'Je schneller der Anwender im Vergleich zum Ziel ist, desto höher die Stärke.', "Changes the target's type to Water.": 'Ändert den Typ des Ziels zu Wasser.', "Uses target's Attack stat in damage calculation.": 'Verwendet bei der Schadensberechnung den Angriff des Ziels.', "The target's Ability becomes Simple.": 'Ändert die Fähigkeit des Ziels zu Wankelmut.', "The target's Ability changes to match the user's.": 'Ändert die Fähigkeit des Ziels zur Fähigkeit des Anwenders.', 'The target makes its move right after the user.': 'Das Ziel führt seinen Zug unmittelbar nach dem Anwender aus.', 'Power doubles if others used Round this turn.': 'Die Stärke verdoppelt sich, wenn in dieser Runde bereits Kanon eingesetzt wurde.', 'Power increases when used on consecutive turns.': 'Die Stärke steigt bei aufeinanderfolgenden Einsätzen.', "Resets all of the target's stat stages to 0.": 'Setzt alle Statuswertveränderungen des Ziels auf 0 zurück.', "+ 20 power for each of the user's stat boosts.": 'Erhält +20 Stärke für jede positive Statuswertstufe des Anwenders.', 'Protects allies from priority attacks this turn.': 'Schützt Verbündete in dieser Runde vor Prioritätsattacken.', 'User and ally swap positions; using again can fail.': 'Anwender und Verbündeter tauschen ihre Positionen. Wiederholter Einsatz kann fehlschlagen.', 'Heals the target by 50% of its max HP.': 'Heilt das Ziel um 50% seiner maximalen KP.', 'Power doubles if the target has a status ailment.': 'Die Stärke verdoppelt sich, wenn das Ziel ein Statusproblem hat.', 'Destroys the foe(s) Berry/Gem.': 'Zerstört Beeren oder Juwelen der Gegner.', 'Forces the target to move last this turn.': 'Zwingt das Ziel, in dieser Runde zuletzt zu handeln.', 'Power doubles if the user has no held item.': 'Die Stärke verdoppelt sich, wenn der Anwender kein Item trägt.', 'User becomes the same type as the target.': 'Der Anwender nimmt den Typ des Ziels an.', 'Power doubles if an ally fainted last turn.': 'Die Stärke verdoppelt sich, wenn in der vorherigen Runde ein Verbündeter kampfunfähig wurde.', "Does damage equal to the user's HP. User faints.": 'Verursacht Schaden in Höhe der aktuellen KP des Anwenders. Der Anwender wird anschließend kampfunfähig.', 'Use with Grass or Fire Pledge for added effect.': 'Kann mit Pflanzensäulen oder Feuersäulen kombiniert werden, um einen zusätzlichen Effekt auszulösen.', 'Use with Grass or Water Pledge for added effect.': 'Kann mit Pflanzensäulen oder Wassersäulen kombiniert werden, um einen zusätzlichen Effekt auszulösen.', 'Use with Fire or Water Pledge for added effect.': 'Kann mit Feuersäulen oder Wassersäulen kombiniert werden, um einen zusätzlichen Effekt auszulösen.', "30% chance to confuse target. Can't miss in rain.": '30% Chance, das Ziel zu verwirren. Trifft bei Regen immer.', 'Type varies based on the held Drive.': 'Der Typ hängt vom gehaltenen Modul ab.', '10% chance to sleep foe(s). Meloetta transforms.': '10% Chance, Gegner einschlafen zu lassen. Meloetta wechselt seine Form.', 'Charges turn 1. Hits turn 2. 30% paralyze.': 'Lädt in Runde 1 auf und greift in Runde 2 an. 30% Chance auf Paralyse.', 'Charges turn 1. Hits turn 2. 30% burn.': 'Lädt in Runde 1 auf und greift in Runde 2 an. 30% Chance auf Verbrennung.', 'Power doubles if used after Fusion Bolt this turn.': 'Die Stärke verdoppelt sich, wenn in dieser Runde zuvor Kreuzdonner eingesetzt wurde.', 'Power doubles if used after Fusion Flare this turn.': 'Die Stärke verdoppelt sich, wenn in dieser Runde zuvor Kreuzflamme eingesetzt wurde.', 'Combines Flying in its type effectiveness.': 'Berücksichtigt zusätzlich den Flug-Typ bei der Typeneffektivität.', 'Protects allies from damaging attacks. Turn 1 only.': 'Schützt Verbündete vor Schadensattacken. Funktioniert nur in der ersten Runde nach dem Einwechseln.', 'Fails unless the user has eaten a Berry.': 'Schlägt fehl, wenn der Anwender noch keine Beere gegessen hat.', 'Lowers Speed of grounded foes by 1 on switch-in.': 'Senkt beim Einwechseln die Initiative geerdeter Gegner um 1 Stufe.', "Raises user's Attack by 3 if this KOes the target.": 'Erhöht den Angriff des Anwenders um 3 Stufen, wenn die Attacke das Ziel besiegt.', "Adds Ghost to the target's type(s).": 'Fügt dem Ziel den Geist-Typ hinzu.', "Adds Grass to the target's type(s).": 'Fügt dem Ziel den Pflanzen-Typ hinzu.', 'No additional effect. Hits adjacent Pokemon.': 'Kein zusätzlicher Effekt. Trifft alle angrenzenden Pokémon.', 'Super effective on Water.': 'Ist sehr effektiv gegen Wasser-Pokémon.', "Lowers target's Atk, Sp. Atk by 1. User switches.": 'Senkt Angriff und Sp.-Ang. des Ziels um 1 Stufe. Anschließend wechselt der Anwender aus.', "Inverts the target's stat stages.": 'Kehrt alle Statuswertveränderungen des Ziels um.', 'Protects allies from Status moves this turn.': 'Schützt Verbündete in dieser Runde vor Status-Attacken.', 'Raises Defense by 1 of all active Grass types.': 'Erhöht die Verteidigung aller aktiven Pflanzen-Pokémon um 1 Stufe.', "Changes the target's move to Electric this turn.": 'Ändert den Typ der Attacke des Ziels in dieser Runde zu Elektro.', 'Prevents all Pokemon from switching next turn.': 'Verhindert in der nächsten Runde, dass Pokémon auswechseln.', 'Protects from damaging attacks. Contact: -1 Atk.': 'Schützt vor Schadensattacken. Bei Kontakt sinkt der Angriff des Angreifers um 1 Stufe.', 'Usually goes first. Hits 2-5 times in one turn.': 'Trifft 2–5-mal.', 'Protects from moves. Contact: loses 1/8 max HP.': 'Schützt vor Attacken. Bei Kontakt verliert der Angreifer 1/8 seiner maximalen KP.', 'Lowers Atk/Sp. Atk/Speed of poisoned foes by 1.': 'Senkt Angriff, Sp.-Ang. und Initiative vergifteter Gegner um 1 Stufe.', 'Charges, then raises SpA, SpD, Spe by 2 turn 2.': 'Lädt eine Runde auf und erhöht in Runde 2 Sp.-Ang., Sp.-Vert. und Initiative um 2 Stufen.', 'Raises Def, Sp. Def of allies with Plus/Minus by 1.': 'Erhöht Verteidigung und Sp.-Vert. von Verbündeten mit Plus oder Minus um 1 Stufe.', 'Grounds adjacent foes. First hit neutral on Flying.': 'Erdet angrenzende Gegner. Der erste Treffer wirkt gegen Flug-Pokémon neutral.', 'Hits adjacent foes. Prevents them from switching.': 'Trifft beide Gegner und verhindert deren Wechsel.', "Hoopa-U: Lowers user's Def by 1; breaks protect.": 'Hoopa (Entfesselt): Senkt die Verteidigung des Anwenders um 1 Stufe und durchbricht Schutz-Attacken.', 'User restores 1/2 its max HP; 2/3 in Sandstorm.': 'Heilt 1/2 der maximalen KP des Anwenders, im Sandsturm 2/3.', 'Nearly always goes first. First turn out only.': 'Funktioniert nur in der ersten Runde nach dem Einwechseln.', 'Protects from moves. Contact: poison.': 'Schützt vor Attacken. Bei Kontakt wird der Angreifer vergiftet.', 'The target is cured of its burn.': 'Heilt die Verbrennung des Ziels.', "User heals HP=target's Atk stat. Lowers Atk by 1.": 'Heilt den Anwender um KP in Höhe des Angriffs des Ziels und senkt dessen Angriff um 1 Stufe.', "Until the end of the next turn, user's moves crit.": 'Bis zum Ende der nächsten Runde landen Attacken des Anwenders Volltreffer.', 'Raises Atk, Sp. Atk of allies with Plus/Minus by 1.': 'Erhöht Angriff und Sp.-Ang. von Verbündeten mit Plus oder Minus um 1 Stufe.', 'For 2 turns, the target cannot use sound moves.': 'Das Ziel kann 2 Runden lang keine Lärm-Attacken einsetzen.', 'If the target is an ally, heals 50% of its max HP.': 'Ist das Ziel ein Verbündeter, werden 50% seiner maximalen KP geheilt.', "User's Fire type becomes typeless; must be Fire.": 'Entfernt den Feuer-Typ des Anwenders. Funktioniert nur bei einem Feuer-Pokémon.', 'Swaps Speed stat with target.': 'Tauscht die Initiative des Anwenders mit der des Ziels.', "Cures target's status; heals user 1/2 max HP if so.": 'Heilt das Statusproblem des Ziels und stellt dabei 1/2 der maximalen KP des Anwenders wieder her.', "Type varies based on the user's primary type.": 'Der Typ hängt vom primären Typ des Anwenders ab.', 'Nullifies the foe(s) Ability if the foe(s) move first.': 'Unterdrückt die Fähigkeit der Gegner, wenn diese vor dem Anwender handeln.', 'The target immediately uses its last used move.': 'Das Ziel setzt sofort seine zuletzt eingesetzte Attacke erneut ein.', 'Burns on contact with the user before it moves.': 'Verbrennt Gegner, die den Anwender vor dessen Zug mit Kontakt treffen.', 'For 5 turns, damage to allies halved. Snow only.': 'Halbiert 5 Runden lang den Schaden gegen das eigene Team. Kann nur bei Schnee eingesetzt werden.', 'User must take physical damage before moving.': 'Der Anwender muss vor seinem Zug physischen Schaden erlitten haben.', "Power doubles if the user's last move failed.": 'Die Stärke verdoppelt sich, wenn die letzte Attacke des Anwenders fehlgeschlagen ist.', "Steals target's boosts before dealing damage.": 'Übernimmt vor der Schadensberechnung die positiven Statuswertveränderungen des Ziels.', 'Type varies based on the held Memory.': 'Der Typ hängt vom gehaltenen Speicher ab.', 'User loses 50% max HP. Hits adjacent Pokemon.': 'Der Anwender verliert 50% seiner maximalen KP. Trifft alle angrenzenden Pokémon.', 'Normal moves become Electric type this turn.': 'Normal-Attacken werden in dieser Runde zu Elektro-Attacken.', "Physical if user's Atk > Sp. Atk. Ignores Abilities.": 'Ist der Angriff des Anwenders höher als sein Sp.-Ang., wird die Attacke physisch. Ignoriert Fähigkeiten.', 'Protects user from moves & Max Moves this turn.': 'Schützt den Anwender in dieser Runde vor Attacken und Dynamax-Attacken.', 'Prevents both user and target from switching out.': 'Verhindert, dass Anwender und Ziel auswechseln.', 'Fails unless the user has a berry. User eats Berry, Def +2.': 'Schlägt fehl, wenn der Anwender keine Beere trägt. Verzehrt die Beere und erhöht die Verteidigung um 2 Stufen.', 'Raises all stats by 1 (not acc/eva). Traps user.': 'Erhöht alle Statuswerte außer Genauigkeit und Ausweichwert um 1 Stufe und hindert den Anwender am Wechsel.', "Changes the target's type to Psychic.": 'Ändert den Typ des Ziels zu Psycho.', 'All active Pokemon consume held Berries.': 'Alle aktiven Pokémon verzehren ihre gehaltenen Beeren.', 'Traps target, lowers Def and SpD by 1 each turn.': 'Hindert das Ziel am Wechsel und senkt jede Runde Verteidigung und Sp.-Vert. um 1 Stufe.', 'Power doubles if user moves before the target.': 'Die Stärke verdoppelt sich, wenn der Anwender vor dem Ziel handelt.', "Swaps user's field effects with the opposing side.": 'Tauscht die Feldeffekte auf der eigenen und gegnerischen Seite.', 'Base move affects power. Starts Sunny Day.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Sonne.', 'Base move affects power. Foes: -1 Sp. Atk.': 'Die Basisattacke bestimmt die Stärke. Senkt den Sp.-Ang. der Gegner um 1 Stufe.', 'Base move affects power. Starts Electric Terrain.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Elektrofeld.', 'Base move affects power. Foes: -1 Speed.': 'Die Basisattacke bestimmt die Stärke. Senkt die Initiative der Gegner um 1 Stufe.', 'Base move affects power. Allies: +1 Attack.': 'Die Basisattacke bestimmt die Stärke. Erhöht den Angriff der Verbündeten um 1 Stufe.', 'Base move affects power. Foes: -1 Defense.': 'Die Basisattacke bestimmt die Stärke. Senkt die Verteidigung der Gegner um 1 Stufe.', 'Base move affects power. Starts Hail.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Hagel.', 'Base move affects power. Allies: +1 Sp. Atk.': 'Die Basisattacke bestimmt die Stärke. Erhöht den Sp.-Ang. der Verbündeten um 1 Stufe.', 'Base move affects power. Starts Rain Dance.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Regen.', 'Base move affects power. Allies: +1 Speed.': 'Die Basisattacke bestimmt die Stärke. Erhöht die Initiative der Verbündeten um 1 Stufe.', 'Base move affects power. Starts Misty Terrain.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Nebelfeld.', 'Base move affects power. Foes: -1 Attack.': 'Die Basisattacke bestimmt die Stärke. Senkt den Angriff der Gegner um 1 Stufe.', 'Base move affects power. Starts Psychic Terrain.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Psychofeld.', 'Base move affects power. Starts Sandstorm.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Sandsturm.', 'Base move affects power. Allies: +1 Sp. Def.': 'Die Basisattacke bestimmt die Stärke. Erhöht die Sp.-Vert. der Verbündeten um 1 Stufe.', 'Base move affects power. Foes: -1 Sp. Def.': 'Die Basisattacke bestimmt die Stärke. Senkt die Sp.-Vert. der Gegner um 1 Stufe.', 'Base move affects power. Starts Grassy Terrain.': 'Die Basisattacke bestimmt die Stärke. Erzeugt Grasfeld.', 'Base move affects power. Allies: +1 Defense.': 'Die Basisattacke bestimmt die Stärke. Erhöht die Verteidigung der Verbündeten um 1 Stufe.', 'User loses 33% of its max HP. +1 to all stats.': 'Der Anwender verliert 33% seiner maximalen KP und erhöht alle Statuswerte um 1 Stufe.', "Uses user's Def stat as Atk in damage calculation.": 'Verwendet bei der Schadensberechnung die Verteidigung des Anwenders anstelle seines Angriffs.', 'Morpeko: Electric; Hangry: Dark; 100% +1 Spe.': 'Morpeko: Elektro; Kohldampf-Form: Unlicht. Erhöht die Initiative sicher um 1 Stufe.', 'No additional effect. Hits foe(s).': 'Kein zusätzlicher Effekt. Trifft beide Gegner.', 'Target: 100% -1 Def. During Gravity: 1.5x power.': 'Senkt die Verteidigung des Ziels sicher um 1 Stufe. Bei Erdanziehung beträgt die Stärke das 1,5-Fache.', 'Protects from damaging attacks. Contact: -2 Def.': 'Schützt vor Schadensattacken. Bei Kontakt sinkt die Verteidigung des Angreifers um 2 Stufen.', 'User loses 50% max HP.': 'Der Anwender verliert 50% seiner maximalen KP.', 'User on Psychic Terrain: 1.5x power, hits foes.': 'Im Psychofeld beträgt die Stärke das 1,5-Fache und die Attacke trifft beide Gegner.', 'Fails if there is no terrain active. Ends the terrain.': 'Schlägt fehl, wenn kein Feld aktiv ist, und beendet anschließend das Feld.', "Raises user's Sp. Atk by 1 on turn 1. Hits turn 2.": 'Erhöht in Runde 1 den Sp.-Ang. des Anwenders um 1 Stufe und greift in Runde 2 an.', '20% psn. Physical+contact if it would be stronger.': '20% Chance auf Vergiftung. Wird physisch und zu einer Kontakt-Attacke, wenn dies stärker wäre.', 'User faints. User on Misty Terrain: 1.5x power.': 'Der Anwender wird kampfunfähig. Im Nebelfeld beträgt die Stärke das 1,5-Fache.', 'User on Grassy Terrain: +1 priority.': 'Besitzt im Grasfeld +1 Priorität.', '2x power if target is grounded in Electric Terrain.': 'Doppelte Stärke gegen geerdete Ziele im Elektrofeld.', 'User on terrain: power doubles, type varies.': 'Ist ein Feld aktiv, verdoppelt sich die Stärke und der Typ hängt vom Feld ab.', '100% burns a target that had a stat rise this turn.': 'Verbrennt sicher ein Ziel, dessen Statuswerte in dieser Runde erhöht wurden.', '2x power if the user had a stat lowered this turn.': 'Doppelte Stärke, wenn ein Statuswert des Anwenders in dieser Runde gesenkt wurde.', 'Fails if the target has no held item.': 'Schlägt fehl, wenn das Ziel kein Item trägt.', "Removes adjacent Pokemon's held items.": 'Entfernt die gehaltenen Items angrenzender Pokémon.', 'User and allies: healed 1/4 max HP, status cured.': 'Heilt Anwender und Verbündete um 1/4 ihrer maximalen KP und entfernt Statusprobleme.', "Removes 3 PP from the target's last move.": 'Entfernt 3 AP von der zuletzt eingesetzten Attacke des Ziels.', '30% chance to sleep, poison, or paralyze target.': '30% Chance, das Ziel einschlafen zu lassen, zu vergiften oder zu paralysieren.', "Sets Stealth Rock on the target's side.": 'Legt Tarnsteine auf der gegnerischen Seite aus.', '50% psn. 2x power if target already poisoned.': '50% Chance auf Vergiftung. Doppelte Stärke gegen bereits vergiftete Ziele.', '30% burn. 2x power if target is already statused.': '30% Chance auf Verbrennung. Doppelte Stärke gegen Ziele mit Statusproblem.', 'Sets a layer of Spikes on the opposing side.': 'Legt eine Schicht Stachler auf der gegnerischen Seite aus.', "30% to lower foe(s) Speed by 1. Rain: can't miss.": '30% Chance, die Initiative der Gegner um 1 Stufe zu senken. Trifft bei Regen immer.', "20% chance to paralyze foe(s). Rain: can't miss.": '20% Chance, Gegner zu paralysieren. Trifft bei Regen immer.', "20% chance to burn foe(s). Can't miss in rain.": '20% Chance, Gegner zu verbrennen. Trifft bei Regen immer.', "Cures user's status, raises Sp. Atk, Sp. Def by 1.": 'Heilt Statusprobleme des Anwenders und erhöht Sp.-Ang. und Sp.-Vert. um 1 Stufe.', 'If Terastallized: Phys. if Atk > SpA, type = Tera.': 'Nach Terakristallisierung: physisch, wenn Angriff > Sp.-Ang.; Typ entspricht dem Tera-Typ.', 'Protects from damaging attacks. Contact: -1 Spe.': 'Schützt vor Schadensattacken. Bei Kontakt sinkt die Initiative des Angreifers um 1 Stufe.', '30% confusion. User loses 50% max HP if miss.': '30% Chance auf Verwirrung. Bei Verfehlen verliert der Anwender 50% seiner maximalen KP.', '+50 power for each time a party member fainted.': 'Erhält +50 Stärke für jedes kampfunfähige Teammitglied.', 'Curly|Droopy|Stretchy eaten: +1 Atk|Def|Spe.': 'Wird Nigiragi gefressen: Gebogene Form erhöht Angriff, Hängende Form Verteidigung, Gestreckte Form Initiative um 1 Stufe.', 'Ends the effects of terrain.': 'Beendet das aktive Feld.', 'User takes sure-hit 2x damage until its next turn.': 'Bis zum nächsten Zug des Anwenders treffen Attacken sicher und verursachen doppelten Schaden gegen ihn.', 'Revives a fainted Pokemon to 50% HP.': 'Belebt ein kampfunfähiges Pokémon mit 50% seiner maximalen KP wieder.', 'Deals 1/16 max HP each turn; 1/8 on Steel, Water.': 'Verursacht jede Runde 1/16 der maximalen KP Schaden, gegen Stahl- und Wasser-Pokémon 1/8.', 'Poisons foes, frees user from hazards/bind/leech.': 'Vergiftet Gegner und entfernt Gefahren, Fessel- sowie Egelsamen-Effekte vom Anwender.', "User and ally's Abilities become target's Ability.": 'Die Fähigkeiten von Anwender und Verbündetem werden zur Fähigkeit des Ziels.', "+2 Attack, Sp. Atk, Speed for 1/2 user's max HP.": 'Erhöht Angriff, Sp.-Ang. und Initiative um 2 Stufen und kostet 1/2 der maximalen KP des Anwenders.', "Destroys screens. Type depends on user's form.": 'Zerstört Schilde. Der Typ hängt von der Form des Anwenders ab.', 'During Electric Terrain: 1.5x power.': 'Im Elektrofeld beträgt die Stärke das 1,5-Fache.', 'Deals 1.3333x damage with supereffective hits.': 'Sehr effektive Treffer verursachen das 1,3333-Fache des normalen Schadens.', 'User takes 1/2 its max HP to pass a substitute.': 'Der Anwender verliert 1/2 seiner maximalen KP, erzeugt einen Delegator und übergibt ihn beim Wechsel.', 'Starts Snow. User switches out.': 'Erzeugt Schnee. Anschließend wechselt der Anwender aus.', 'User +1 Atk, Spe. Clears all substitutes/hazards.': 'Erhöht Angriff und Initiative des Anwenders um 1 Stufe und entfernt Delegatoren sowie Gefahren.', 'Bypasses protection without breaking it.': 'Umgeht Schutz-Attacken, ohne deren Effekt aufzuheben.', '+50 BP/hit on user. Max 6 hits. Resets on switch-out.': 'Erhält +50 Stärke für jeden Treffer, den der Anwender erlitten hat, bis maximal 6 Treffer. Wird beim Wechsel zurückgesetzt.', "User's Electric type: typeless; must be Electric.": 'Entfernt den Elektro-Typ des Anwenders. Funktioniert nur bei einem Elektro-Pokémon.', "Cannot be selected the turn after it's used.": 'Kann in der Runde nach dem Einsatz nicht ausgewählt werden.', "Target's Speed is lowered by 1 stage for 3 turns.": 'Senkt die Initiative des Ziels 3 Runden lang um 1 Stufe.', "High critical hit ratio. Type depends on user's form.": 'Erhöhte Volltrefferquote. Der Typ hängt von der Form des Anwenders ab.', 'Raises Sp. Atk by 1, hits turn 2. Rain: no charge.': 'Erhöht den Sp.-Ang. um 1 Stufe und greift in Runde 2 an. Bei Regen entfällt die Aufladerunde.', 'Terapagos-Stellar: Stellar type, hits both foes.': 'Terapagos in Stellarform: Typ Stellar und trifft beide Gegner.', "Has a 30% chance this move's power is doubled.": '30% Chance, dass sich die Stärke der Attacke verdoppelt.', 'Protects from damaging attacks. Contact: burn.': 'Schützt vor Schadensattacken. Bei Kontakt wird der Angreifer verbrannt.', 'Ally: Crit ratio +1, or +2 if ally is Dragon type.': 'Erhöht die Volltrefferquote eines Verbündeten um 1 Stufe, bei Drachen-Pokémon um 2 Stufen.', '100% confuse target that had a stat rise this turn.': 'Verwirrt sicher ein Ziel, dessen Statuswerte in dieser Runde erhöht wurden.', 'For 2 turns, the target is prevented from healing.': 'Verhindert 2 Runden lang, dass das Ziel KP wiederherstellt.', '100% flinch. Fails unless target using priority attack.': 'Lässt das Ziel sicher zurückschrecken. Schlägt fehl, wenn das Ziel keine Prioritätsattacke einsetzt.', 'No additional effect.': 'Kein zusätzlicher Effekt.', '10% chance to burn the target.': '10% Chance, das Ziel zu verbrennen.', '10% chance to freeze the target.': '10% Chance, das Ziel einzufrieren.', '10% chance to paralyze the target.': '10% Chance, das Ziel zu paralysieren.', 'OHKOs the target. Fails if user is a lower level.': 'Besiegt das Ziel mit einem Treffer. Schlägt fehl, wenn der Anwender ein niedrigeres Level hat.', "Raises the user's Attack by 2.": 'Erhöht den Angriff des Anwenders um 2 Stufen.', 'Forces the target to switch to a random ally.': 'Zwingt das Ziel zum Wechsel zu einem zufälligen Teammitglied.', 'Traps and damages the target for 4-5 turns.': 'Hindert das Ziel 4–5 Runden am Wechsel und fügt ihm dabei jede Runde Schaden zu.', '30% chance to make the target flinch.': '30% Chance, das Ziel zurückschrecken zu lassen.', 'Hits 2 times in one turn.': 'Trifft 2-mal.', "Lowers the target's accuracy by 1.": 'Senkt die Genauigkeit des Ziels um 1 Stufe.', 'Hits 2-5 times in one turn.': 'Trifft 2–5-mal.', '30% chance to paralyze the target.': '30% Chance, das Ziel zu paralysieren.', 'Has 1/4 recoil.': 'Rückstoß: 1/4 des verursachten Schadens.', 'Has 33% recoil.': 'Rückstoß: 33% des verursachten Schadens.', 'Lowers the foe(s) Defense by 1.': 'Senkt die Verteidigung der Gegner um 1 Stufe.', '30% chance to poison the target.': '30% Chance, das Ziel zu vergiften.', 'Lowers the foe(s) Attack by 1.': 'Senkt den Angriff der Gegner um 1 Stufe.', 'Causes the target to fall asleep.': 'Lässt das Ziel einschlafen.', 'Causes the target to become confused.': 'Verwirrt das Ziel.', '10% chance to lower the foe(s) Sp. Def by 1.': '10% Chance, die Sp.-Vert. der Gegner um 1 Stufe zu senken.', '10% chance to confuse the target.': '10% Chance, das Ziel zu verwirren.', "10% chance to lower the target's Speed by 1.": '10% Chance, die Initiative des Ziels um 1 Stufe zu senken.', "10% chance to lower the target's Attack by 1.": '10% Chance, den Angriff des Ziels um 1 Stufe zu senken.', "Does damage equal to the user's level.": 'Verursacht Schaden in Höhe des Levels des Anwenders.', 'User recovers 50% of the damage dealt.': 'Heilt den Anwender um 50% des verursachten Schadens.', 'High critical hit ratio. Hits adjacent foes.': 'Erhöhte Volltrefferquote. Trifft beide Gegner.', 'Poisons the target.': 'Vergiftet das Ziel.', 'Paralyzes the target.': 'Paralysiert das Ziel.', 'Lowers the foe(s) Speed by 2.': 'Senkt die Initiative der Gegner um 2 Stufen.', "Badly poisons the target. Poison types can't miss.": 'Vergiftet das Ziel schwer. Bei Einsatz durch ein Gift-Pokémon trifft die Attacke sicher.', "10% chance to lower the target's Sp. Def by 1.": '10% Chance, die Sp.-Vert. des Ziels um 1 Stufe zu senken.', "Raises the user's Speed by 2.": 'Erhöht die Initiative des Anwenders um 2 Stufen.', "Lowers the target's Defense by 2.": 'Senkt die Verteidigung des Ziels um 2 Stufen.', "Raises the user's evasiveness by 1.": 'Erhöht den Ausweichwert des Anwenders um 1 Stufe.', 'Heals the user by 50% of its max HP.': 'Heilt den Anwender um 50% seiner maximalen KP.', "Raises the user's Defense by 1.": 'Erhöht die Verteidigung des Anwenders um 1 Stufe.', "Raises the user's evasiveness by 2.": 'Erhöht den Ausweichwert des Anwenders um 2 Stufen.', 'Confuses the target.': 'Verwirrt das Ziel.', 'Hits adjacent Pokemon. The user faints.': 'Trifft alle angrenzenden Pokémon. Der Anwender wird anschließend kampfunfähig.', '40% chance to poison the target.': '40% Chance, das Ziel zu vergiften.', '20% chance to make the target flinch.': '20% Chance, das Ziel zurückschrecken zu lassen.', "Raises the user's Sp. Def by 2.": 'Erhöht die Sp.-Vert. des Anwenders um 2 Stufen.', 'Poisons the foe(s).': 'Vergiftet die Gegner.', "Raises the user's Defense by 2.": 'Erhöht die Verteidigung des Anwenders um 2 Stufen.', 'High critical hit ratio.': 'Erhöhte Volltrefferquote.', '30% chance to make the foe(s) flinch.': '30% Chance, Gegner zurückschrecken zu lassen.', '10% chance to burn the target. Thaws user.': '10% Chance, das Ziel zu verbrennen. Taut den Anwender auf.', "Lowers the target's Speed by 2.": 'Senkt die Initiative des Ziels um 2 Stufen.', '10% chance to freeze the foe(s).': '10% Chance, Gegner einzufrieren.', "100% chance to lower the target's accuracy by 1.": 'Senkt die Genauigkeit des Ziels sicher um 1 Stufe.', "50% chance to lower the target's accuracy by 1.": '50% Chance, die Genauigkeit des Ziels um 1 Stufe zu senken.', '100% chance to paralyze the target.': 'Paralysiert das Ziel sicher.', '100% chance to lower the foe(s) Speed by 1.': 'Senkt die Initiative der Gegner sicher um 1 Stufe.', 'For 5 turns, a sandstorm rages. Rock: 1.5x SpD.': 'Erzeugt 5 Runden lang Sandsturm. Gestein-Pokémon erhalten 1,5-fache Sp.-Vert.', "Lowers the target's Attack by 2.": 'Senkt den Angriff des Ziels um 2 Stufen.', "Raises the target's Attack by 2 and confuses it.": 'Erhöht den Angriff des Ziels um 2 Stufen und verwirrt es.', "10% chance to raise the user's Defense by 1.": '10% Chance, die Verteidigung des Anwenders um 1 Stufe zu erhöhen.', '50% chance to burn the target. Thaws user.': '50% Chance, das Ziel zu verbrennen. Taut den Anwender auf.', '100% chance to confuse the target.': 'Verwirrt das Ziel sicher.', 'Target repeats its last move for its next 3 turns.': 'Zwingt das Ziel, seine zuletzt eingesetzte Attacke 3 Runden lang zu wiederholen.', 'Lowers the foe(s) evasiveness by 2.': 'Senkt den Ausweichwert der Gegner um 2 Stufen.', "30% chance to lower the target's Defense by 1.": '30% Chance, die Verteidigung des Ziels um 1 Stufe zu senken.', "10% chance to raise the user's Attack by 1.": '10% Chance, den Angriff des Anwenders um 1 Stufe zu erhöhen.', '20% chance to make the foe(s) flinch.': '20% Chance, Gegner zurückschrecken zu lassen.', 'For 5 turns, heavy rain powers Water moves.': 'Erzeugt 5 Runden lang Regen und verstärkt Wasser-Attacken.', 'For 5 turns, intense sunlight powers Fire moves.': 'Erzeugt 5 Runden lang Sonne und verstärkt Feuer-Attacken.', "20% chance to lower the target's Defense by 1.": '20% Chance, die Verteidigung des Ziels um 1 Stufe zu senken.', '10% chance to raise all stats by 1 (not acc/eva).': '10% Chance, alle Statuswerte außer Genauigkeit und Ausweichwert um 1 Stufe zu erhöhen.', "20% chance to lower the target's Sp. Def by 1.": '20% Chance, die Sp.-Vert. des Ziels um 1 Stufe zu senken.', "50% chance to lower the target's Defense by 1.": '50% Chance, die Verteidigung des Ziels um 1 Stufe zu senken.', '10% chance to burn the foe(s).': '10% Chance, Gegner zu verbrennen.', 'For 5 turns, hail crashes down.': 'Erzeugt 5 Runden lang Hagel.', "Raises the target's Sp. Atk by 1 and confuses it.": 'Erhöht den Sp.-Ang. des Ziels um 1 Stufe und verwirrt es.', 'Burns the target.': 'Verbrennt das Ziel.', "Lowers target's Attack, Sp. Atk by 2. User faints.": 'Senkt Angriff und Sp.-Ang. des Ziels um 2 Stufen. Der Anwender wird anschließend kampfunfähig.', "+1 SpD, user's next Electric move 2x power.": 'Erhöht die Sp.-Vert. um 1 Stufe. Die nächste Elektro-Attacke des Anwenders erhält doppelte Stärke.', "Target can't use status moves its next 3 turns.": 'Das Ziel kann 3 Runden lang keine Status-Attacken einsetzen.', 'Traps/grounds user; heals 1/16 max HP per turn.': 'Hindert den Anwender am Wechsel, erdet ihn und heilt jede Runde 1/16 seiner maximalen KP.', "Lowers the user's Attack and Defense by 1.": 'Senkt Angriff und Verteidigung des Anwenders um 1 Stufe.', "Raises the user's Sp. Atk by 3.": 'Erhöht den Sp.-Ang. des Anwenders um 3 Stufen.', "50% chance to lower the target's Sp. Def by 1.": '50% Chance, die Sp.-Vert. des Ziels um 1 Stufe zu senken.', "50% chance to lower the target's Sp. Atk by 1.": '50% Chance, den Sp.-Ang. des Ziels um 1 Stufe zu senken.', 'Confuses adjacent Pokemon.': 'Verwirrt alle angrenzenden Pokémon.', 'High critical hit ratio. 10% chance to burn.': 'Erhöhte Volltrefferquote. 10% Chance, das Ziel zu verbrennen.', '50% chance to badly poison the target.': '50% Chance, das Ziel schwer zu vergiften.', "20% chance to raise the user's Attack by 1.": '20% Chance, den Angriff des Anwenders um 1 Stufe zu erhöhen.', "Lowers the target's Sp. Def by 2.": 'Senkt die Sp.-Vert. des Ziels um 2 Stufen.', "Lowers the user's Sp. Atk by 2.": 'Senkt den Sp.-Ang. des Anwenders um 2 Stufen.', "100% chance to lower the target's Speed by 1.": 'Senkt die Initiative des Ziels sicher um 1 Stufe.', "Lowers the target's Attack and Defense by 1.": 'Senkt Angriff und Verteidigung des Ziels um 1 Stufe.', "Raises the user's Defense and Sp. Def by 1.": 'Erhöht Verteidigung und Sp.-Vert. des Anwenders um 1 Stufe.', '10% chance to make the target flinch.': '10% Chance, das Ziel zurückschrecken zu lassen.', "OHKOs non-Ice targets. Fails if user's lower level.": 'Besiegt Nicht-Eis-Ziele mit einem Treffer. Schlägt fehl, wenn der Anwender ein niedrigeres Level hat.', '30% chance to lower the foe(s) accuracy by 1.': '30% Chance, die Genauigkeit der Gegner um 1 Stufe zu senken.', "Raises the user's and ally's Attack by 1.": 'Erhöht den Angriff des Anwenders und seines Verbündeten um 1 Stufe.', "Raises the user's Attack and Defense by 1.": 'Erhöht Angriff und Verteidigung des Anwenders um 1 Stufe.', 'High critical hit ratio. 10% chance to poison.': 'Erhöhte Volltrefferquote. 10% Chance, das Ziel zu vergiften.', 'Has 33% recoil. 10% chance to paralyze target.': 'Rückstoß: 33% des verursachten Schadens. 10% Chance, das Ziel zu paralysieren.', "Raises the user's Sp. Atk and Sp. Def by 1.": 'Erhöht Sp.-Ang. und Sp.-Vert. des Anwenders um 1 Stufe.', "Raises the user's Attack and Speed by 1.": 'Erhöht Angriff und Initiative des Anwenders um 1 Stufe.', '20% chance to confuse the target.': '20% Chance, das Ziel zu verwirren.', "Heals 50% HP. Flying-type removed 'til turn ends.": 'Heilt 50% der maximalen KP. Entfernt den Flug-Typ bis zum Ende der Runde.', "Lowers the user's Speed by 1.": 'Senkt die Initiative des Anwenders um 1 Stufe.', 'Nullifies Detect, Protect, and Quick/Wide Guard.': 'Hebt Scanner, Schutzschild sowie Rundumschutz und Rapidschutz auf.', 'User switches out after damaging the target.': 'Der Anwender wechselt nach dem Angriff aus.', "Lowers the user's Defense and Sp. Def by 1.": 'Senkt Verteidigung und Sp.-Vert. des Anwenders um 1 Stufe.', 'User recovers 1/16 max HP per turn.': 'Heilt den Anwender jede Runde um 1/16 seiner maximalen KP.', 'Has 33% recoil. 10% chance to burn. Thaws user.': 'Rückstoß: 33% des verursachten Schadens. 10% Chance auf Verbrennung. Taut den Anwender auf.', "Raises the user's Sp. Atk by 2.": 'Erhöht den Sp.-Ang. des Anwenders um 2 Stufen.', '10% chance to paralyze. 10% chance to flinch.': '10% Chance auf Paralyse und 10% Chance auf Zurückschrecken.', '10% chance to freeze. 10% chance to flinch.': '10% Chance auf Einfrieren und 10% Chance auf Zurückschrecken.', '10% chance to burn. 10% chance to flinch.': '10% Chance auf Verbrennung und 10% Chance auf Zurückschrecken.', '30% chance to paralyze adjacent Pokemon.': '30% Chance, angrenzende Pokémon zu paralysieren.', '30% chance to burn adjacent Pokemon.': '30% Chance, angrenzende Pokémon zu verbrennen.', "70% chance to raise the user's Sp. Atk by 1.": '70% Chance, den Sp.-Ang. des Anwenders um 1 Stufe zu erhöhen.', 'Has 1/2 recoil.': 'Rückstoß: 50% des verursachten Schadens.', "40% chance to lower the target's Sp. Def by 2.": '40% Chance, die Sp.-Vert. des Ziels um 2 Stufen zu senken.', "Raises the user's Attack and accuracy by 1.": 'Erhöht Angriff und Genauigkeit des Anwenders um 1 Stufe.', 'Always results in a critical hit.': 'Landet immer einen Volltreffer.', '10% chance to poison adjacent Pokemon.': '10% Chance, angrenzende Pokémon zu vergiften.', "Raises the user's Sp. Atk, Sp. Def, Speed by 1.": 'Erhöht Sp.-Ang., Sp.-Vert. und Initiative des Anwenders um 1 Stufe.', "100% chance to raise the user's Speed by 1.": 'Erhöht die Initiative des Anwenders sicher um 1 Stufe.', "Raises user's Attack, Defense, accuracy by 1.": 'Erhöht Angriff, Verteidigung und Genauigkeit des Anwenders um 1 Stufe.', "100% chance to lower the target's Sp. Def by 2.": 'Senkt die Sp.-Vert. des Ziels sicher um 2 Stufen.', '30% chance to burn the target. Thaws target.': '30% Chance, das Ziel zu verbrennen. Taut das Ziel auf.', 'Lowers Def, SpD by 1; raises Atk, SpA, Spe by 2.': 'Senkt Verteidigung und Sp.-Vert. des Anwenders um 1 Stufe und erhöht Angriff, Sp.-Ang. und Initiative um 2 Stufen.', "Raises the user's Speed by 2 and Attack by 1.": 'Erhöht Initiative um 2 Stufen und Angriff um 1 Stufe.', '100% chance to burn the target.': 'Verbrennt das Ziel sicher.', '100% chance to lower the foe(s) Sp. Atk by 1.': 'Senkt den Sp.-Ang. der Gegner sicher um 1 Stufe.', '100% chance lower adjacent Pkmn Speed by 1.': 'Senkt die Initiative angrenzender Pokémon sicher um 1 Stufe.', "Raises the user's Attack and Sp. Atk by 1.": 'Erhöht Angriff und Sp.-Ang. des Anwenders um 1 Stufe.', "Ignores the target's stat stage changes.": 'Ignoriert Statuswertveränderungen des Ziels bei der Schadensberechnung.', "Raises the user's Defense by 3.": 'Erhöht die Verteidigung des Anwenders um 3 Stufen.', "40% chance to lower the target's accuracy by 1.": '40% Chance, die Genauigkeit des Ziels um 1 Stufe zu senken.', '20% chance to paralyze the target.': '20% Chance, das Ziel zu paralysieren.', '20% chance to burn the target.': '20% Chance, das Ziel zu verbrennen.', "50% chance to raise the user's Sp. Atk by 1.": '50% Chance, den Sp.-Ang. des Anwenders um 1 Stufe zu erhöhen.', "Lowers the user's Defense, Sp. Def, Speed by 1.": 'Senkt Verteidigung, Sp.-Vert. und Initiative des Anwenders um 1 Stufe.', "Lowers the target's Attack and Sp. Atk by 1.": 'Senkt Angriff und Sp.-Ang. des Ziels um 1 Stufe.', 'User recovers 75% of the damage dealt.': 'Heilt den Anwender um 75% des verursachten Schadens.', '5 turns. Grounded: +Grass power, +1/16 max HP.': '5 Runden lang: Geerdete Pokémon erhalten stärkere Pflanzen-Attacken und heilen jede Runde 1/16 ihrer maximalen KP.', "5 turns. Can't status,-Dragon power vs grounded.": '5 Runden lang: Geerdete Pokémon können keine neuen Statusprobleme erhalten; Drachen-Attacken gegen sie werden abgeschwächt.', "10% chance to lower the target's Sp. Atk by 1.": '10% Chance, den Sp.-Ang. des Ziels um 1 Stufe zu senken.', "Lowers the target's Attack by 1.": 'Senkt den Angriff des Ziels um 1 Stufe.', "Lowers the target's Sp. Atk by 1.": 'Senkt den Sp.-Ang. des Ziels um 1 Stufe.', "50% chance to raise user's Defense by 2.": '50% Chance, die Verteidigung des Anwenders um 2 Stufen zu erhöhen.', "Breaks the target's protection for this turn.": 'Durchbricht den Schutz des Ziels für diese Runde.', "100% chance to lower the target's Sp. Atk by 1.": 'Senkt den Sp.-Ang. des Ziels sicher um 1 Stufe.', "Raises an ally's Sp. Def by 1.": 'Erhöht die Sp.-Vert. eines Verbündeten um 1 Stufe.', "Lowers the target's Sp. Atk by 2.": 'Senkt den Sp.-Ang. des Ziels um 2 Stufen.', "5 turns. Grounded: +Electric power, can't sleep.": '5 Runden lang: Geerdete Pokémon erhalten stärkere Elektro-Attacken und können nicht einschlafen.', "100% chance to raise the user's Attack by 1.": 'Erhöht den Angriff des Anwenders sicher um 1 Stufe.', "Lowers the target's Speed by 2 and poisons it.": 'Senkt die Initiative des Ziels um 2 Stufen und vergiftet es.', '5 turns. Grounded: +Psychic power, priority-safe.': '5 Runden lang: Geerdete Pokémon erhalten stärkere Psycho-Attacken und sind vor gegnerischen Prioritätsattacken geschützt.', "100% chance to lower the target's Attack by 1.": 'Senkt den Angriff des Ziels sicher um 1 Stufe.', "100% chance to lower the target's Defense by 1.": 'Senkt die Verteidigung des Ziels sicher um 1 Stufe.', "Lowers the user's Defense by 1.": 'Senkt die Verteidigung des Anwenders um 1 Stufe.', 'Ignores the Abilities of other Pokemon.': 'Ignoriert die Fähigkeiten anderer Pokémon.', 'Hits twice. 30% chance to make the target flinch.': 'Trifft 2-mal. 30% Chance, das Ziel zurückschrecken zu lassen.', 'High critical hit ratio. Cannot be redirected.': 'Erhöhte Volltrefferquote. Kann nicht umgelenkt werden.', 'Target gets -1 Spe and becomes weaker to Fire.': 'Senkt die Initiative des Ziels um 1 Stufe und macht es anfälliger für Feuer-Attacken.', 'Hits twice. Doubles: Tries to hit each foe once.': 'Trifft 2-mal. Im Doppelkampf wird nach Möglichkeit jeder Gegner einmal getroffen.', "Raises the target's Attack and Sp. Atk by 2.": 'Erhöht Angriff und Sp.-Ang. des Ziels um 2 Stufen.', '100% chance to lower the foe(s) Attack by 1.': 'Senkt den Angriff der Gegner sicher um 1 Stufe.', "100% chance to lower the target's Sp. Def by 1.": 'Senkt die Sp.-Vert. des Ziels sicher um 1 Stufe.', 'Heals the user and its allies by 1/4 their max HP.': 'Heilt Anwender und Verbündete um 1/4 ihrer maximalen KP.', 'Hits 2-5 times. User: -1 Def, +1 Spe after last hit.': 'Trifft 2–5-mal. Nach dem letzten Treffer sinkt die Verteidigung des Anwenders um 1 Stufe und seine Initiative steigt um 1 Stufe.', "100% chance to lower target's Sp. Atk by 1.": 'Senkt den Sp.-Ang. des Ziels sicher um 1 Stufe.', "Raises an ally's Attack and Defense by 1.": 'Erhöht Angriff und Verteidigung eines Verbündeten um 1 Stufe.', 'Always results in a critical hit. Hits 3 times.': 'Landet immer Volltreffer und trifft 3-mal.', "100% chance to raise the user's Defense by 1.": 'Erhöht die Verteidigung des Anwenders sicher um 1 Stufe.', '30% chance to lower the foe(s) Attack by 1.': '30% Chance, den Angriff der Gegner um 1 Stufe zu senken.', "100% chance to raise the user's Sp. Atk by 1.": 'Erhöht den Sp.-Ang. des Anwenders sicher um 1 Stufe.', "Raises the user's Attack, Defense, Speed by 1.": 'Erhöht Angriff, Verteidigung und Initiative des Anwenders um 1 Stufe.', '100% chance to raise user Speed by 1. High crit.': 'Erhöht die Initiative des Anwenders sicher um 1 Stufe. Erhöhte Volltrefferquote.', 'High crit. Target: 50% -1 Defense, 30% flinch.': 'Erhöhte Volltrefferquote. 50% Chance auf −1 Verteidigung und 30% Chance auf Zurückschrecken beim Ziel.', "Raises target's Atk by 2 and lowers its Def by 2.": 'Erhöht den Angriff des Ziels um 2 Stufen und senkt seine Verteidigung um 2 Stufen.', "Lowers the user's Speed by 2.": 'Senkt die Initiative des Anwenders um 2 Stufen.', 'Hits 10 times. Each hit can miss.': 'Trifft 10-mal. Jeder Treffer kann einzeln verfehlen.', 'Hits 3 times.': 'Trifft 3-mal.', 'Always results in a critical hit; no accuracy check.': 'Landet immer einen Volltreffer und trifft sicher.', "Lowers the user's Sp. Atk by 2. Hits foe(s).": 'Senkt den Sp.-Ang. des Anwenders um 2 Stufen und trifft beide Gegner.', 'During Sunny Day: 1.5x damage instead of half.': 'Bei Sonne verursacht die Attacke 1,5-fachen Schaden statt halbierten Schaden.', 'For 5 turns, snow falls. Ice: 1.5x Def.': 'Erzeugt 5 Runden lang Schnee. Eis-Pokémon erhalten 1,5-fache Verteidigung.', '20% burn. Recovers 50% dmg dealt. Thaws foe(s).': '20% Chance auf Verbrennung. Heilt 50% des verursachten Schadens und taut getroffene Ziele auf.', 'Hits twice. This move does not check accuracy.': 'Trifft 2-mal und trifft garantiert.'}


NODE_EXPORT_SCRIPT = r"""
const path = require('path');

const packageDirectory = process.argv[1];
const {Dex} = require(path.join(packageDirectory, 'dist', 'sim', 'dex'));
const championsMoveModule = require(
  path.join(packageDirectory, 'dist', 'data', 'mods', 'champions', 'moves')
);
const championsOverrides = new Set(
  Object.keys(championsMoveModule.Moves || {})
);

const valueSources = [
  {key: 'champions', mod: 'champions'},
  {key: 'scarlet-violet', mod: 'gen9'},
  {key: 'sword-shield', mod: 'gen8'},
  {key: 'bdsp', mod: 'gen8bdsp'},
];

function copyObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(([, entry]) => typeof entry !== 'function')
  );
}

function normalizeSecondary(effect) {
  return {
    chance: effect.chance ?? 100,
    status: effect.status ?? null,
    volatile_status: effect.volatileStatus ?? null,
    stat_changes: copyObject(effect.boosts),
    self_stat_changes: copyObject(effect.self && effect.self.boosts),
    has_custom_logic: Object.values(effect).some(
      value => typeof value === 'function'
    ),
  };
}

function normalizeFraction(value) {
  return Array.isArray(value) ? value : null;
}

function displayedPP(move, valueSource) {
  if (valueSource.key === 'champions') {
    const cappedPP = Math.min(move.pp, 20);
    return move.noPPBoosts ? cappedPP : (cappedPP / 5 + 1) * 4;
  }

  return move.pp;
}

function normalizeMove(move, valueSource) {
  const secondaryEffects = (
    move.secondaries || (move.secondary ? [move.secondary] : [])
  ).map(normalizeSecondary);

  const callbackFields = Object.entries(move)
    .filter(([, value]) => typeof value === 'function')
    .map(([key]) => key)
    .sort();

  return {
    move_id: move.num,
    api_name: move.id,
    name_en: move.name,
    name_de: null,
    name_de_is_fallback: false,
    type: move.type.toLowerCase(),
    category: move.category.toLowerCase(),
    power: move.basePower > 0 ? move.basePower : null,
    accuracy: move.accuracy === true ? null : move.accuracy,
    always_hits: move.accuracy === true,
    pp: move.pp,
    max_pp: move.noPPBoosts ? move.pp : Math.floor(move.pp * 1.6),
    pp_ups_allowed: !move.noPPBoosts,
    pp_by_source: {
      [valueSource.key]: displayedPP(move, valueSource),
    },
    priority: move.priority,
    target: move.target,
    properties: Object.entries(move.flags || {})
      .filter(([, enabled]) => Boolean(enabled))
      .map(([flag]) => flag)
      .sort(),
    is_spread_move: ['allAdjacent', 'allAdjacentFoes'].includes(move.target),
    champions_modified: (
      valueSource.key === 'champions' && championsOverrides.has(move.id)
    ),
    values_source: valueSource.key,
    effects: {
      summary_en: move.shortDesc || '',
      description_en: move.desc || move.shortDesc || '',
      status: move.status ?? null,
      volatile_status: move.volatileStatus ?? null,
      stat_changes: copyObject(move.boosts),
      self_stat_changes: copyObject(
        (move.self && move.self.boosts) ||
        (move.selfBoost && move.selfBoost.boosts)
      ),
      secondary_effects: secondaryEffects,
      drain: normalizeFraction(move.drain),
      recoil: normalizeFraction(move.recoil),
      healing: normalizeFraction(move.heal),
      multi_hit: move.multihit ?? null,
      checks_accuracy_per_hit: Boolean(move.multiaccuracy),
      fixed_damage: (
        typeof move.damage === 'number' || typeof move.damage === 'string'
      ) ? move.damage : null,
      one_hit_ko: move.ohko ?? false,
      critical_hit_ratio: move.critRatio ?? 1,
      always_critical: Boolean(move.willCrit),
      self_switch: move.selfSwitch ?? false,
      force_switch: Boolean(move.forceSwitch),
      self_destruct: move.selfdestruct ?? null,
      breaks_protect: Boolean(move.breaksProtect),
      ignores_ability: Boolean(move.ignoreAbility),
      ignores_defense: Boolean(move.ignoreDefensive),
      ignores_evasion: Boolean(move.ignoreEvasion),
      thaws_target: Boolean(move.thawsTarget),
      weather: move.weather ?? null,
      terrain: move.terrain ?? null,
      pseudo_weather: move.pseudoWeather ?? null,
      side_condition: move.sideCondition ?? null,
      slot_condition: move.slotCondition ?? null,
      dynamic_power: (
        typeof move.basePowerCallback === 'function' ||
        typeof move.onBasePower === 'function'
      ),
      dynamic_damage: typeof move.damageCallback === 'function',
      has_custom_logic: callbackFields.length > 0,
      callback_fields: callbackFields,
    },
  };
}

const movesByNumber = new Map();

for (const valueSource of valueSources) {
  const dex = Dex.mod(valueSource.mod);

  for (const move of dex.moves.all()) {
    if (
      !move.exists || move.isNonstandard || move.num <= 0 || move.num === 1000
    ) continue;

    const existing = movesByNumber.get(move.num);
    if (existing) {
      if (existing.api_name !== move.id) {
        throw new Error(
          `Move ID ${move.num} is both ${existing.api_name} and ${move.id}`
        );
      }

      existing.pp_by_source[valueSource.key] = displayedPP(
        move,
        valueSource
      );
      continue;
    }

    movesByNumber.set(move.num, normalizeMove(move, valueSource));
  }
}

const moves = [...movesByNumber.values()].sort(
  (left, right) => left.move_id - right.move_id
);

process.stdout.write(JSON.stringify(moves));
"""


def get_bytes(url: str) -> bytes:
    """Download bytes with retries for temporary network failures."""
    request = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(MAX_REQUEST_ATTEMPTS):
        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                return response.read()
        except HTTPError as error:
            should_retry = (
                error.code in RETRYABLE_HTTP_STATUS_CODES
                and attempt < MAX_REQUEST_ATTEMPTS - 1
            )
            if not should_retry:
                raise
        except (URLError, TimeoutError):
            if attempt >= MAX_REQUEST_ATTEMPTS - 1:
                raise

        time.sleep(0.5 * (2 ** attempt))

    raise RuntimeError(f"Could not download {url}")


@lru_cache(maxsize=None)
def get_json(url: str) -> dict[str, Any]:
    """Load and cache one JSON resource."""
    return json.loads(get_bytes(url).decode("utf-8"))


def get_localized_name(
    entries: list[dict[str, Any]],
    language: str,
) -> str:
    """Return one language from a PokéAPI names list."""
    for entry in entries:
        if entry.get("language", {}).get("name") == language:
            return entry.get("name", "")
    return ""


def require_node() -> str:
    """Return the Node.js executable or explain the missing dependency."""
    node_executable = shutil.which("node")
    if node_executable is None:
        raise RuntimeError(
            "Node.js was not found. Install Node.js before running the "
            "move importer; Showdown's own Dex loader requires it."
        )
    return node_executable


def download_showdown_package() -> tuple[bytes, str]:
    """Download the latest stable Pokémon Showdown npm package."""
    print("Loading Pokémon Showdown package metadata...")
    metadata = get_json(SHOWDOWN_PACKAGE_METADATA_URL)
    version = metadata["version"]
    tarball_url = metadata["dist"]["tarball"]

    print(f"Downloading Pokémon Showdown {version}...")
    return get_bytes(tarball_url), version


def extract_showdown_dist(
    tarball: bytes,
    destination: Path,
) -> Path:
    """Safely extract only Showdown's compiled runtime files."""
    destination = destination.resolve()

    with tarfile.open(
        fileobj=io.BytesIO(tarball),
        mode="r:gz",
    ) as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.name.startswith("package/dist/")
        ]

        if not members:
            raise RuntimeError(
                "The Showdown package does not contain compiled data."
            )

        for member in members:
            if member.issym() or member.islnk():
                raise RuntimeError(
                    f"Refusing link in Showdown package: {member.name}"
                )

            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination)
            except ValueError as error:
                raise RuntimeError(
                    f"Unsafe path in Showdown package: {member.name}"
                ) from error

        archive.extractall(
            destination,
            members=members,
            filter="data",
        )

    return destination / "package"


def export_moves(
    showdown_package: Path,
    node_executable: str,
) -> list[dict[str, Any]]:
    """Return the prioritized union of moves from all selected games."""
    try:
        result = subprocess.run(
            [
                node_executable,
                "-e",
                NODE_EXPORT_SCRIPT,
                str(showdown_package),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or "No Node.js error output."
        raise RuntimeError(
            f"Showdown move export failed:\n{details}"
        ) from error

    try:
        moves = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Showdown returned invalid move JSON."
        ) from error

    if not isinstance(moves, list):
        raise RuntimeError("Showdown did not return a move list.")
    return moves


def add_german_name(
    move: dict[str, Any],
    skip_localization: bool,
) -> bool:
    """Add the official German name and report whether fallback was used."""
    if skip_localization:
        move["name_de"] = move["name_en"]
        move["name_de_is_fallback"] = True
        return True

    name_de = ""

    try:
        move_data = get_json(
            f"{POKEAPI_BASE_URL}/move/{move['move_id']}"
        )
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(
            f"  Warning: no PokéAPI localization for "
            f"{move['api_name']}: {error}"
        )
    else:
        name_de = get_localized_name(move_data.get("names", []), "de")

    if not name_de:
        name_de = GERMAN_MOVE_NAME_SUPPLEMENTS.get(move["move_id"], "")

    fallback_used = not bool(name_de)
    move["name_de"] = name_de or move["name_en"]
    move["name_de_is_fallback"] = fallback_used

    if fallback_used:
        print(
            f"  Warning: German-name fallback for "
            f"{move['move_id']} {move['api_name']} "
            f"({move['name_en']})"
        )

    return fallback_used


def add_german_summary(move: dict[str, Any]) -> bool:
    """Add ``summary_de`` and report whether English fallback was necessary."""
    effects = move.get("effects")
    if not isinstance(effects, dict):
        raise ValueError(
            f"Missing effects for {move.get('api_name', 'unknown move')}"
        )

    summary_en = str(effects.get("summary_en") or "").strip()
    summary_de = SUMMARY_DE_TRANSLATIONS.get(summary_en)

    fallback_used = summary_de is None and bool(summary_en)

    if summary_de is None:
        summary_de = summary_en

    effects["summary_de"] = summary_de
    effects["summary_de_is_fallback"] = fallback_used

    if fallback_used:
        print(
            "  Warning: German-summary fallback for "
            f"{move['api_name']}: {summary_en!r}"
        )

    return fallback_used


def validate_moves(moves: list[dict[str, Any]]) -> None:
    """Reject duplicate or incomplete move records before writing JSON."""
    move_ids: set[int] = set()
    api_names: set[str] = set()
    allowed_categories = {"physical", "special", "status"}

    if not moves:
        raise ValueError("The move list is empty.")

    for move in moves:
        move_id = move["move_id"]
        api_name = move["api_name"]

        if move_id in move_ids:
            raise ValueError(f"Duplicate move ID: {move_id}")
        if api_name in api_names:
            raise ValueError(f"Duplicate move API name: {api_name}")
        if move["category"] not in allowed_categories:
            raise ValueError(
                f"Invalid category for {api_name}: {move['category']}"
            )
        if not move["name_en"] or not move["name_de"]:
            raise ValueError(f"Missing name for {api_name}")
        if not move["type"]:
            raise ValueError(f"Missing type for {api_name}")
        if not isinstance(move["priority"], int):
            raise ValueError(f"Invalid priority for {api_name}")
        if not isinstance(move["pp"], int) or move["pp"] < 1:
            raise ValueError(f"Invalid PP for {api_name}")

        pp_by_source = move.get("pp_by_source")
        if not isinstance(pp_by_source, dict) or not pp_by_source:
            raise ValueError(f"Missing source-specific PP for {api_name}")
        if move["values_source"] not in pp_by_source:
            raise ValueError(
                f"Missing PP for primary source of {api_name}"
            )
        for pp_source, source_pp in pp_by_source.items():
            if pp_source not in VALUE_SOURCE_KEYS:
                raise ValueError(
                    f"Invalid PP source for {api_name}: {pp_source}"
                )
            if (
                not isinstance(source_pp, (int, float))
                or source_pp < 1
                or not float(source_pp).is_integer()
            ):
                raise ValueError(
                    f"Invalid source PP for {api_name}: "
                    f"{pp_source}={source_pp}"
                )
        if len(move["properties"]) != len(set(move["properties"])):
            raise ValueError(f"Duplicate properties for {api_name}")
        if move.get("values_source") not in VALUE_SOURCE_KEYS:
            raise ValueError(
                f"Invalid values source for {api_name}: "
                f"{move.get('values_source')}"
            )

        source = move.get("source", {})
        expected_mod = VALUE_SOURCE_MODS[move["values_source"]]

        if source.get("database") != "pokemon-showdown":
            raise ValueError(f"Invalid source database for {api_name}")
        if not isinstance(source.get("version"), str):
            raise ValueError(f"Missing Showdown version for {api_name}")
        if source.get("mod") != expected_mod:
            raise ValueError(
                f"Invalid source mod for {api_name}: {source.get('mod')}"
            )
        if move["champions_modified"] and (
            move["values_source"] != "champions"
        ):
            raise ValueError(
                f"Non-Champions move marked as modified: {api_name}"
            )

        effects = move.get("effects")
        if not isinstance(effects, dict):
            raise ValueError(f"Missing effects for {api_name}")
        if not isinstance(effects.get("summary_en"), str):
            raise ValueError(f"Missing English summary for {api_name}")
        if not isinstance(effects.get("summary_de"), str):
            raise ValueError(f"Missing German summary for {api_name}")
        if not isinstance(
            effects.get("summary_de_is_fallback"),
            bool,
        ):
            raise ValueError(
                f"Missing German-summary fallback flag for {api_name}"
            )

        move_ids.add(move_id)
        api_names.add(api_name)


def write_json_atomically(
    data: list[dict[str, Any]],
    output_file: Path,
) -> None:
    """Write complete JSON first, then replace the target in one step."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_name(
        f"{output_file.stem}.tmp{output_file.suffix}"
    )

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")

    temporary_file.replace(output_file)


def import_moves(
    limit: int | None = None,
    skip_localization: bool = False,
) -> tuple[
    Path,
    int,
    dict[str, int],
    int,
    int,
    int,
    str,
]:
    """Build, localize, validate and write the prioritized move list."""
    if limit is not None and limit < 1:
        raise ValueError("--limit must be at least 1.")

    node_executable = require_node()
    tarball, showdown_version = download_showdown_package()

    with tempfile.TemporaryDirectory(
        prefix="cordys-showdown-"
    ) as temporary_directory:
        showdown_package = extract_showdown_dist(
            tarball,
            Path(temporary_directory),
        )
        moves = export_moves(
            showdown_package,
            node_executable,
        )

    if limit is not None:
        moves = moves[:limit]

    german_name_fallback_count = 0
    german_summary_fallback_count = 0
    move_total = len(moves)

    for position, move in enumerate(moves, start=1):
        print(
            f"Localizing move {position}/{move_total}: "
            f"{move['api_name']}"
        )

        german_name_fallback_count += add_german_name(
            move,
            skip_localization=skip_localization,
        )
        german_summary_fallback_count += add_german_summary(move)

        move["source"] = {
            "database": "pokemon-showdown",
            "version": showdown_version,
            "mod": VALUE_SOURCE_MODS[move["values_source"]],
        }

    validate_moves(moves)

    output_file = PREVIEW_OUTPUT_FILE if limit is not None else OUTPUT_FILE
    write_json_atomically(moves, output_file)

    modified_count = sum(move["champions_modified"] for move in moves)
    source_counts = {
        source["key"]: sum(
            move["values_source"] == source["key"]
            for move in moves
        )
        for source in MOVE_VALUE_SOURCES
    }

    return (
        output_file,
        move_total,
        source_counts,
        modified_count,
        german_name_fallback_count,
        german_summary_fallback_count,
        showdown_version,
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import the prioritized Champions, Scarlet/Violet, "
            "Sword/Shield and BDSP move union from Pokémon Showdown, "
            "plus German names and German short effect descriptions."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        help=(
            "Import only the first N moves and write "
            "moves_preview.json."
        ),
    )
    parser.add_argument(
        "--skip-localization",
        action="store_true",
        help=(
            "Do not contact PokéAPI; use English move names as temporary "
            "German fallbacks. German effect summaries are still generated."
        ),
    )
    return parser.parse_args()


def main() -> None:
    print("Cordy's Lab move importer v3")
    arguments = parse_arguments()

    (
        output_file,
        move_count,
        source_counts,
        modified_count,
        german_name_fallback_count,
        german_summary_fallback_count,
        showdown_version,
    ) = import_moves(
        limit=arguments.limit,
        skip_localization=arguments.skip_localization,
    )

    print()
    print(
        f"Done! Imported {move_count} moves from "
        f"Pokémon Showdown {showdown_version}."
    )
    for source in MOVE_VALUE_SOURCES:
        print(
            f"Values from {source['label']}: "
            f"{source_counts[source['key']]}"
        )

    print(f"Champions-modified moves: {modified_count}")
    print(f"German-name fallbacks: {german_name_fallback_count}")
    print(f"German-summary fallbacks: {german_summary_fallback_count}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()