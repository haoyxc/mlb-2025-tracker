"""
Fetch MLB season cache files and player progression cache files.

Usage:
    python fetch_data.py
    python fetch_data.py 2024
    python fetch_data.py --years 2021 2022 2023 2024 2025 --players
"""
import argparse
import json
from pathlib import Path

import requests

MLB_TEAM_IDS = {
    'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111, 'CHC': 112,
    'CHW': 145, 'CIN': 113, 'CLE': 114, 'COL': 115, 'DET': 116,
    'HOU': 117, 'KCR': 118, 'LAA': 108, 'LAD': 119, 'MIA': 146,
    'MIL': 158, 'MIN': 142, 'NYM': 121, 'NYY': 147, 'OAK': 133,
    'PHI': 143, 'PIT': 134, 'SDP': 135, 'SEA': 136, 'SFG': 137,
    'STL': 138, 'TBR': 139, 'TEX': 140, 'TOR': 141, 'WSN': 120,
}

PLAYER_SEASONS = [2023, 2024, 2025]
PLAYER_TARGETS = {
    'david-peterson': {
        'player_id': 656849,
        'name': 'David Peterson',
        'kind': 'pitcher',
        'group': 'pitching',
        'metric': 'era',
        'metric_label': 'ERA',
    },
    'corey-seager': {
        'player_id': 608369,
        'name': 'Corey Seager',
        'kind': 'batter',
        'group': 'hitting',
        'metric': 'batting_average',
        'metric_label': 'AVG',
    },
}


def request_json(session, url, params, timeout=20):
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, sort_keys=True, separators=(',', ':')) + '\n'
    )


def fetch_season(year, session=None):
    session = session or requests.Session()
    all_teams = {}
    for team, team_id in MLB_TEAM_IDS.items():
        try:
            raw = request_json(
                session,
                "https://statsapi.mlb.com/api/v1/schedule",
                {
                    "sportId": 1,
                    "teamId": team_id,
                    "season": year,
                    "gameType": "R",
                    "startDate": f"{year}-03-01",
                    "endDate": f"{year}-10-15",
                },
            )

            games = []
            seen_pks = set()
            for date_entry in raw.get('dates', []):
                for game in date_entry.get('games', []):
                    if game.get('status', {}).get('detailedState') not in ('Final', 'Completed Early'):
                        continue
                    game_pk = game.get('gamePk')
                    if game_pk in seen_pks:
                        continue
                    seen_pks.add(game_pk)

                    away = game['teams']['away']
                    home = game['teams']['home']
                    is_home = home['team']['id'] == team_id
                    if is_home:
                        won = home.get('isWinner', False)
                        opponent = away['team']['name']
                    else:
                        won = away.get('isWinner', False)
                        opponent = home['team']['name']

                    games.append({
                        'date': date_entry['date'],
                        'opp': opponent,
                        'won': bool(won),
                        'wl': 'W' if won else 'L',
                    })

            if not games:
                print(f"  {team}: no games found")
                continue

            wins = sum(1 for game in games if game['won'])
            losses = len(games) - wins
            print(f"  {team}: {len(games)}g ({wins}-{losses})")
            all_teams[team] = games

        except Exception as exc:
            print(f"  {team}: SKIP - {exc}")

    return all_teams


def get_playoff_teams(year, session=None):
    session = session or requests.Session()
    try:
        raw = request_json(
            session,
            "https://statsapi.mlb.com/api/v1/standings",
            {
                "leagueId": "103,104",
                "season": year,
                "standingsTypes": "regularSeason",
            },
            timeout=15,
        )
        playoff_ids = set()
        for record in raw.get('records', []):
            for team_record in record.get('teamRecords', []):
                if team_record.get('clinchIndicator', '') in ('y', 'z', 'x', 'w'):
                    playoff_ids.add(team_record['team']['id'])

        id_to_abbr = {team_id: abbr for abbr, team_id in MLB_TEAM_IDS.items()}
        return sorted(id_to_abbr[team_id] for team_id in playoff_ids if team_id in id_to_abbr)
    except Exception as exc:
        print(f"  Could not fetch playoff teams: {exc}")
        return []


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def outs_from_innings(value):
    if value in (None, '', '-.--'):
        return 0
    text = str(value)
    if '.' not in text:
        return as_int(text) * 3
    whole, frac = text.split('.', 1)
    return as_int(whole) * 3 + as_int(frac[:1])


def player_sort_key(row):
    return (
        str(row.get('date', '')),
        str(row.get('game_time') or ''),
        as_int(row.get('game_pk')),
    )


def order_player_game_rows(rows):
    return sorted(rows, key=player_sort_key)


def format_average(value):
    if value is None:
        return 'N/A'
    text = f"{value:.3f}"
    return text[1:] if text.startswith('0') else text


def calculate_pitcher_progression(rows, season):
    ordered = order_player_game_rows(rows)
    cumulative_outs = 0
    cumulative_earned_runs = 0
    previous_metric_value = None
    previous_display_value = 'N/A'
    output = []
    for index, row in enumerate(ordered, start=1):
        outs = as_int(row.get('outs'))
        earned_runs = as_int(row.get('earned_runs'))
        cumulative_outs += outs
        cumulative_earned_runs += earned_runs
        metric_value = None
        display_value = 'N/A'
        if outs == 0:
            metric_value = previous_metric_value
            display_value = previous_display_value
        elif cumulative_outs:
            metric_value = cumulative_earned_runs * 27 / cumulative_outs
            display_value = f"{metric_value:.2f}"
        previous_metric_value = metric_value
        previous_display_value = display_value

        output.append({
            'season': int(season),
            'game_number': index,
            'date': row['date'],
            'game_pk': as_int(row.get('game_pk')),
            'opponent': row.get('opponent', ''),
            'home_away': row.get('home_away', ''),
            'outs': outs,
            'earned_runs': earned_runs,
            'cum_outs': cumulative_outs,
            'cum_earned_runs': cumulative_earned_runs,
            'metric_value': metric_value,
            'display_value': display_value,
        })
    return output


def calculate_batter_progression(rows, season):
    ordered = order_player_game_rows(rows)
    cumulative_at_bats = 0
    cumulative_hits = 0
    output = []
    for index, row in enumerate(ordered, start=1):
        at_bats = as_int(row.get('at_bats'))
        hits = as_int(row.get('hits'))
        cumulative_at_bats += at_bats
        cumulative_hits += hits
        metric_value = None
        if cumulative_at_bats:
            metric_value = cumulative_hits / cumulative_at_bats

        output.append({
            'season': int(season),
            'game_number': index,
            'date': row['date'],
            'game_pk': as_int(row.get('game_pk')),
            'opponent': row.get('opponent', ''),
            'home_away': row.get('home_away', ''),
            'at_bats': at_bats,
            'hits': hits,
            'cum_at_bats': cumulative_at_bats,
            'cum_hits': cumulative_hits,
            'metric_value': metric_value,
            'display_value': format_average(metric_value),
        })
    return output


def fetch_player_game_rows(session, player_id, group, season):
    raw = request_json(
        session,
        f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
        {
            "stats": "gameLog",
            "group": group,
            "season": season,
            "sportIds": 1,
            "gameType": "R",
        },
    )
    stats = raw.get('stats', [])
    splits = stats[0].get('splits', []) if stats else []
    rows = []
    for split in splits:
        stat = split.get('stat', {})
        game = split.get('game', {})
        row = {
            'date': split.get('date', ''),
            'game_time': game.get('gameDate', ''),
            'game_pk': game.get('gamePk', 0),
            'opponent': split.get('opponent', {}).get('name', ''),
            'home_away': 'home' if split.get('isHome') else 'away',
        }
        if group == 'pitching':
            row.update({
                'outs': as_int(stat.get('outs'), outs_from_innings(stat.get('inningsPitched'))),
                'earned_runs': as_int(stat.get('earnedRuns')),
            })
        else:
            row.update({
                'at_bats': as_int(stat.get('atBats')),
                'hits': as_int(stat.get('hits')),
            })
        rows.append(row)
    return rows


def fetch_player_progressions(session=None):
    session = session or requests.Session()
    players = {}
    for slug, info in PLAYER_TARGETS.items():
        print(f"\nFetching {info['name']} game logs...")
        season_map = {}
        for season in PLAYER_SEASONS:
            rows = fetch_player_game_rows(session, info['player_id'], info['group'], season)
            if info['kind'] == 'pitcher':
                season_rows = calculate_pitcher_progression(rows, season)
            else:
                season_rows = calculate_batter_progression(rows, season)
            season_map[str(season)] = season_rows
            print(f"  {season}: {len(season_rows)} games")

        players[slug] = {
            'player_id': info['player_id'],
            'name': info['name'],
            'kind': info['kind'],
            'metric': info['metric'],
            'metric_label': info['metric_label'],
            'seasons': season_map,
        }

    return {
        'schema_version': 1,
        'seasons': PLAYER_SEASONS,
        'players': players,
    }


def build_arg_parser():
    parser = argparse.ArgumentParser(description='Fetch cached MLB tracker data.')
    parser.add_argument('year', nargs='?', type=int, help='Single season to fetch.')
    parser.add_argument('--years', nargs='+', type=int, help='One or more seasons to fetch.')
    parser.add_argument('--players', action='store_true', help='Fetch player progression cache.')
    return parser


def main():
    args = build_arg_parser().parse_args()
    years = args.years if args.years else [args.year or 2025]
    session = requests.Session()

    for year in years:
        print(f"Fetching {year} season data...")
        season = fetch_season(year, session=session)

        print(f"\nFetching {year} playoff teams...")
        playoffs = get_playoff_teams(year, session=session)
        print(f"  Playoff teams: {playoffs}")

        output = {
            'year': year,
            'playoff_teams': playoffs,
            'teams': season,
        }
        filename = f'data_{year}.json'
        write_json(filename, output)
        print(f"Saved to {filename} ({len(season)} teams)\n")

    if args.players:
        progressions = fetch_player_progressions(session=session)
        write_json('player_progressions.json', progressions)
        print("\nSaved to player_progressions.json")


if __name__ == '__main__':
    main()
