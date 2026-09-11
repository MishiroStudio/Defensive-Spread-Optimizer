import type { TeamMember } from "./team-builder-data";

export interface RosterPosition {
  area: "team" | "bench";
  index: number;
}

export interface RosterState {
  team: Array<TeamMember | null>;
  bench: TeamMember[];
}

export function moveRosterMember(
  currentTeam: Array<TeamMember | null>,
  currentBench: TeamMember[],
  source: RosterPosition,
  target: RosterPosition,
): RosterState {
  const team = [...currentTeam];
  const bench = [...currentBench];
  if (source.area === target.area && source.index === target.index) return { team, bench };

  if (source.area === "team" && target.area === "team") {
    if (!team[source.index] || target.index < 0 || target.index >= team.length) return { team, bench };
    [team[source.index], team[target.index]] = [team[target.index], team[source.index]];
    return { team, bench };
  }

  if (source.area === "bench" && target.area === "bench") {
    if (source.index < 0 || source.index >= bench.length || target.index < 0 || target.index > bench.length) return { team, bench };
    const [member] = bench.splice(source.index, 1);
    bench.splice(Math.min(target.index, bench.length), 0, member);
    return { team, bench };
  }

  if (source.area === "team") {
    const member = team[source.index];
    if (!member || target.index < 0 || target.index > bench.length) return { team, bench };
    if (target.index < bench.length) {
      [team[source.index], bench[target.index]] = [bench[target.index], member];
    } else {
      team[source.index] = null;
      bench.push(member);
    }
    return { team, bench };
  }

  if (source.index < 0 || source.index >= bench.length || target.index < 0 || target.index >= team.length) return { team, bench };
  const [member] = bench.splice(source.index, 1);
  const replaced = team[target.index];
  team[target.index] = member;
  if (replaced) bench.splice(Math.min(source.index, bench.length), 0, replaced);
  return { team, bench };
}

