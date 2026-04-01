"""
Fetch a full MLB season's game-by-game data and save to JSON.

Usage:
    python fetch_data.py          # defaults to 2025
    python fetch_data.py 2024     # fetch a different season
"""
import json
import sys
import requests

MLB_TEAM_IDS = {
    'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111, 'CHC': 112,
    'CHW': 145, 'CIN': 113, 'CLE': 114, 'COL': 115, 'DET': 116,
    'HOU': 117, 'KCR': 118, 'LAA': 108, 'LAD': 119, 'MIA': 146,
    'MIL': 158, 'MIN': 142, 'NYM': 121, 'NYY': 147, 'OAK': 133,
    'PHI': 143, 'PIT': 134, 'SDP': 135, 'SEA': 136, 'SFG': 137,
    'STL': 138, 'TBR': 139, 'TEX': 140, 'TOR': 141, 'WSN': 120,
}

def fetch_season(year):
    all_teams = {}
    for team, team_id in MLB_TEAM_IDS.items():
        try:
            r = requests.get("https://statsapi.mlb.com/api/v1/schedule", params={
                "sportId": 1, "teamId": team_id, "season": year, "gameType": "R",
                "startDate": f"{year}-03-01", "endDate": f"{year}-10-15",
            }, timeout=20)

            games = []
            seen_pks = set()
            for de in r.json().get('dates', []):
                for g in de['games']:
                    if g['status']['detailedState'] not in ('Final', 'Completed Early'):
                        continue
                    pk = g['gamePk']
                    if pk in seen_pks:
                        continue
                    seen_pks.add(pk)

                    away, home = g['teams']['away'], g['teams']['home']
                    is_home = home['team']['id'] == team_id
                    if is_home:
                        won = home.get('isWinner', False)
                        opp_name = away['team']['name']
                    else:
                        won = away.get('isWinner', False)
                        opp_name = home['team']['name']

                    games.append({
                        'date': de['date'],
                        'opp': opp_name,
                        'won': won,
                        'wl': 'W' if won else 'L',
                    })

            if not games:
                print(f"  {team}: no games found")
                continue

            w = sum(1 for g in games if g['won'])
            l = len(games) - w
            print(f"  {team}: {len(games)}g ({w}-{l})")
            all_teams[team] = games

        except Exception as e:
            print(f"  {team}: SKIP - {e}")

    return all_teams


def get_playoff_teams(year):
    """Get playoff teams from standings API (clinch indicators)."""
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/standings",
                         params={"leagueId": "103,104", "season": year,
                                 "standingsTypes": "regularSeason"},
                         timeout=15)
        playoff_ids = set()
        for record in r.json()['records']:
            for tr in record['teamRecords']:
                if tr.get('clinchIndicator', '') in ('y', 'z', 'x', 'w'):
                    playoff_ids.add(tr['team']['id'])

        # Map back to abbreviations
        id_to_abbr = {v: k for k, v in MLB_TEAM_IDS.items()}
        return sorted([id_to_abbr[tid] for tid in playoff_ids if tid in id_to_abbr])
    except Exception as e:
        print(f"  Could not fetch playoff teams: {e}")
        return []


if __name__ == '__main__':
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025

    print(f"Fetching {year} season data...")
    season = fetch_season(year)

    print(f"\nFetching {year} playoff teams...")
    playoffs = get_playoff_teams(year)
    print(f"  Playoff teams: {playoffs}")

    output = {
        'year': year,
        'playoff_teams': playoffs,
        'teams': season,
    }

    filename = f'data_{year}.json'
    with open(filename, 'w') as f:
        json.dump(output, f)

    print(f"\nSaved to {filename} ({len(season)} teams)")
