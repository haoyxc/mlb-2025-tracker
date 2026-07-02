import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fetch_data import calculate_batter_progression, calculate_pitcher_progression


REQUIRED_YEARS = [2021, 2022, 2023, 2024, 2025]
REQUIRED_SEASONS = [2023, 2024, 2025]
REQUIRED_PLAYERS = {
    'david-peterson': {
        'player_id': 656849,
        'name': 'David Peterson',
        'kind': 'pitcher',
        'metric': 'era',
        'metric_label': 'ERA',
        'row_keys': {
            'season', 'game_number', 'date', 'game_pk', 'opponent',
            'home_away', 'outs', 'earned_runs', 'cum_outs',
            'cum_earned_runs', 'metric_value', 'display_value',
        },
    },
    'corey-seager': {
        'player_id': 608369,
        'name': 'Corey Seager',
        'kind': 'batter',
        'metric': 'batting_average',
        'metric_label': 'AVG',
        'row_keys': {
            'season', 'game_number', 'date', 'game_pk', 'opponent',
            'home_away', 'at_bats', 'hits', 'cum_at_bats',
            'cum_hits', 'metric_value', 'display_value',
        },
    },
}
TEAM_GAME_KEYS = {'date', 'opp', 'won', 'wl'}


def load_json(path):
    return json.loads((ROOT / path).read_text())


class ProgressionCalculationTests(unittest.TestCase):
    def test_cumulative_era_uses_cumulative_earned_runs_and_outs(self):
        rows = [
            {
                'date': '2025-04-01', 'game_time': '2025-04-01T18:00:00Z',
                'game_pk': 3, 'opponent': 'Atlanta Braves', 'home_away': 'home',
                'outs': 6, 'earned_runs': 2,
            },
            {
                'date': '2025-04-07', 'game_time': '2025-04-07T18:00:00Z',
                'game_pk': 8, 'opponent': 'Miami Marlins', 'home_away': 'away',
                'outs': 3, 'earned_runs': 0,
            },
            {
                'date': '2025-04-12', 'game_time': '2025-04-12T18:00:00Z',
                'game_pk': 14, 'opponent': 'Washington Nationals', 'home_away': 'home',
                'outs': 9, 'earned_runs': 1,
            },
        ]

        progression = calculate_pitcher_progression(rows, 2025)

        self.assertEqual([row['cum_outs'] for row in progression], [6, 9, 18])
        self.assertEqual([row['cum_earned_runs'] for row in progression], [2, 2, 3])
        self.assertAlmostEqual(progression[0]['metric_value'], 9.0)
        self.assertAlmostEqual(progression[1]['metric_value'], 6.0)
        self.assertAlmostEqual(progression[2]['metric_value'], 4.5)
        self.assertEqual([row['display_value'] for row in progression], ['9.00', '6.00', '4.50'])

    def test_cumulative_average_uses_cumulative_hits_and_at_bats(self):
        rows = [
            {
                'date': '2025-04-01', 'game_time': '2025-04-01T18:00:00Z',
                'game_pk': 11, 'opponent': 'Boston Red Sox', 'home_away': 'home',
                'at_bats': 4, 'hits': 2,
            },
            {
                'date': '2025-04-02', 'game_time': '2025-04-02T18:00:00Z',
                'game_pk': 12, 'opponent': 'Boston Red Sox', 'home_away': 'home',
                'at_bats': 3, 'hits': 0,
            },
            {
                'date': '2025-04-03', 'game_time': '2025-04-03T18:00:00Z',
                'game_pk': 13, 'opponent': 'Boston Red Sox', 'home_away': 'home',
                'at_bats': 5, 'hits': 3,
            },
        ]

        progression = calculate_batter_progression(rows, 2025)

        self.assertEqual([row['cum_at_bats'] for row in progression], [4, 7, 12])
        self.assertEqual([row['cum_hits'] for row in progression], [2, 2, 5])
        self.assertAlmostEqual(progression[0]['metric_value'], 0.5)
        self.assertAlmostEqual(progression[1]['metric_value'], 2 / 7)
        self.assertAlmostEqual(progression[2]['metric_value'], 5 / 12)
        self.assertEqual([row['display_value'] for row in progression], ['.500', '.286', '.417'])

    def test_pitcher_zero_out_rows_start_na_then_carry_forward(self):
        rows = [
            {
                'date': '2025-04-01', 'game_time': '2025-04-01T18:00:00Z',
                'game_pk': 21, 'opponent': 'Philadelphia Phillies', 'home_away': 'away',
                'outs': 0, 'earned_runs': 1,
            },
            {
                'date': '2025-04-06', 'game_time': '2025-04-06T18:00:00Z',
                'game_pk': 22, 'opponent': 'Philadelphia Phillies', 'home_away': 'away',
                'outs': 6, 'earned_runs': 1,
            },
            {
                'date': '2025-04-11', 'game_time': '2025-04-11T18:00:00Z',
                'game_pk': 23, 'opponent': 'Philadelphia Phillies', 'home_away': 'home',
                'outs': 0, 'earned_runs': 2,
            },
            {
                'date': '2025-04-16', 'game_time': '2025-04-16T18:00:00Z',
                'game_pk': 24, 'opponent': 'Philadelphia Phillies', 'home_away': 'home',
                'outs': 3, 'earned_runs': 0,
            },
        ]

        progression = calculate_pitcher_progression(rows, 2025)

        self.assertIsNone(progression[0]['metric_value'])
        self.assertEqual(progression[0]['display_value'], 'N/A')
        self.assertAlmostEqual(progression[1]['metric_value'], 9.0)
        self.assertEqual(progression[1]['display_value'], '9.00')
        self.assertAlmostEqual(progression[2]['metric_value'], progression[1]['metric_value'])
        self.assertEqual(progression[2]['display_value'], progression[1]['display_value'])
        self.assertEqual(progression[2]['cum_earned_runs'], 4)
        self.assertAlmostEqual(progression[3]['metric_value'], 12.0)
        self.assertEqual(progression[3]['display_value'], '12.00')

    def test_batter_zero_at_bat_rows_start_na_then_carry_forward(self):
        rows = [
            {
                'date': '2025-04-01', 'game_time': '2025-04-01T18:00:00Z',
                'game_pk': 31, 'opponent': 'New York Yankees', 'home_away': 'away',
                'at_bats': 0, 'hits': 0,
            },
            {
                'date': '2025-04-02', 'game_time': '2025-04-02T18:00:00Z',
                'game_pk': 32, 'opponent': 'New York Yankees', 'home_away': 'away',
                'at_bats': 4, 'hits': 2,
            },
            {
                'date': '2025-04-03', 'game_time': '2025-04-03T18:00:00Z',
                'game_pk': 33, 'opponent': 'New York Yankees', 'home_away': 'home',
                'at_bats': 0, 'hits': 0,
            },
        ]

        progression = calculate_batter_progression(rows, 2025)

        self.assertIsNone(progression[0]['metric_value'])
        self.assertEqual(progression[0]['display_value'], 'N/A')
        self.assertAlmostEqual(progression[1]['metric_value'], 0.5)
        self.assertEqual(progression[1]['display_value'], '.500')
        self.assertAlmostEqual(progression[2]['metric_value'], progression[1]['metric_value'])
        self.assertEqual(progression[2]['display_value'], progression[1]['display_value'])

    def test_ordering_and_game_number_reset_per_season(self):
        rows = [
            {
                'date': '2024-04-02', 'game_time': '2024-04-02T18:00:00Z',
                'game_pk': 50, 'opponent': 'Los Angeles Dodgers', 'home_away': 'away',
                'at_bats': 4, 'hits': 1,
            },
            {
                'date': '2024-04-01', 'game_time': '2024-04-01T20:00:00Z',
                'game_pk': 20, 'opponent': 'Los Angeles Dodgers', 'home_away': 'home',
                'at_bats': 4, 'hits': 2,
            },
            {
                'date': '2024-04-01', 'game_time': '2024-04-01T20:00:00Z',
                'game_pk': 10, 'opponent': 'Los Angeles Dodgers', 'home_away': 'home',
                'at_bats': 3, 'hits': 1,
            },
        ]

        progression_2024 = calculate_batter_progression(rows, 2024)
        progression_2025 = calculate_batter_progression(rows[:1], 2025)

        self.assertEqual([row['game_pk'] for row in progression_2024], [10, 20, 50])
        self.assertEqual([row['game_number'] for row in progression_2024], [1, 2, 3])
        self.assertEqual([row['season'] for row in progression_2024], [2024, 2024, 2024])
        self.assertEqual(progression_2025[0]['game_number'], 1)
        self.assertEqual(progression_2025[0]['season'], 2025)


class CacheShapeTests(unittest.TestCase):
    def test_data_year_json_cache_shape(self):
        for year in REQUIRED_YEARS:
            with self.subTest(year=year):
                raw = load_json(f'data_{year}.json')

                self.assertEqual(raw.get('year'), year)
                self.assertIsInstance(raw.get('playoff_teams'), list)
                self.assertTrue(all(isinstance(team, str) for team in raw['playoff_teams']))
                self.assertIsInstance(raw.get('teams'), dict)
                self.assertEqual(len(raw['teams']), 30)

                for team, games in raw['teams'].items():
                    self.assertIsInstance(team, str)
                    self.assertIsInstance(games, list)
                    self.assertGreater(len(games), 0)
                    for game in games:
                        self.assertLessEqual(TEAM_GAME_KEYS, set(game))
                        self.assertIsInstance(game['date'], str)
                        self.assertIsInstance(game['opp'], str)
                        self.assertIsInstance(game['won'], bool)
                        self.assertIn(game['wl'], {'W', 'L'})

    def test_player_progressions_json_schema_required_players_seasons_and_rows(self):
        raw = load_json('player_progressions.json')

        self.assertEqual(raw.get('schema_version'), 1)
        self.assertEqual(raw.get('seasons'), REQUIRED_SEASONS)
        self.assertIsInstance(raw.get('players'), dict)
        self.assertLessEqual(set(REQUIRED_PLAYERS), set(raw['players']))

        for slug, expected in REQUIRED_PLAYERS.items():
            with self.subTest(player=slug):
                player = raw['players'][slug]
                for key in ['player_id', 'name', 'kind', 'metric', 'metric_label', 'seasons']:
                    self.assertIn(key, player)
                self.assertEqual(player['player_id'], expected['player_id'])
                self.assertEqual(player['name'], expected['name'])
                self.assertEqual(player['kind'], expected['kind'])
                self.assertEqual(player['metric'], expected['metric'])
                self.assertEqual(player['metric_label'], expected['metric_label'])

                for season in REQUIRED_SEASONS:
                    rows = player['seasons'].get(str(season))
                    self.assertIsInstance(rows, list)
                    self.assertGreater(len(rows), 0)
                    self.assertEqual(
                        [row['game_number'] for row in rows],
                        list(range(1, len(rows) + 1)),
                    )
                    self.assertEqual(len({row['game_pk'] for row in rows}), len(rows))

                    for row in rows:
                        self.assertLessEqual(expected['row_keys'], set(row))
                        self.assertEqual(row['season'], season)
                        self.assertIsInstance(row['date'], str)
                        self.assertIsInstance(row['game_pk'], int)
                        self.assertIsInstance(row['game_number'], int)
                        self.assertIn(row['home_away'], {'home', 'away'})
                        self.assertTrue(
                            row['metric_value'] is None or isinstance(row['metric_value'], (int, float))
                        )
                        self.assertIsInstance(row['display_value'], str)

    def test_cached_player_cumulative_metrics_match_rows(self):
        raw = load_json('player_progressions.json')

        for slug, expected in REQUIRED_PLAYERS.items():
            player = raw['players'][slug]
            for season in REQUIRED_SEASONS:
                with self.subTest(player=slug, season=season):
                    rows = player['seasons'][str(season)]
                    if expected['kind'] == 'pitcher':
                        self.assert_pitcher_rows_match_cumulative_metrics(rows)
                    else:
                        self.assert_batter_rows_match_cumulative_metrics(rows)

    def assert_pitcher_rows_match_cumulative_metrics(self, rows):
        cumulative_outs = 0
        cumulative_earned_runs = 0
        previous_metric = None
        previous_display = 'N/A'
        for row in rows:
            cumulative_outs += row['outs']
            cumulative_earned_runs += row['earned_runs']
            self.assertEqual(row['cum_outs'], cumulative_outs)
            self.assertEqual(row['cum_earned_runs'], cumulative_earned_runs)
            if row['outs'] == 0:
                expected_metric = previous_metric
                expected_display = previous_display
            elif cumulative_outs:
                expected_metric = cumulative_earned_runs * 27 / cumulative_outs
                expected_display = f"{expected_metric:.2f}"
            else:
                expected_metric = None
                expected_display = 'N/A'
            self.assert_metric_equal(row['metric_value'], expected_metric)
            self.assertEqual(row['display_value'], expected_display)
            previous_metric = row['metric_value']
            previous_display = row['display_value']

    def assert_batter_rows_match_cumulative_metrics(self, rows):
        cumulative_at_bats = 0
        cumulative_hits = 0
        for row in rows:
            cumulative_at_bats += row['at_bats']
            cumulative_hits += row['hits']
            self.assertEqual(row['cum_at_bats'], cumulative_at_bats)
            self.assertEqual(row['cum_hits'], cumulative_hits)
            if cumulative_at_bats:
                expected_metric = cumulative_hits / cumulative_at_bats
                expected_display = f"{expected_metric:.3f}"
                if expected_display.startswith('0'):
                    expected_display = expected_display[1:]
            else:
                expected_metric = None
                expected_display = 'N/A'
            self.assert_metric_equal(row['metric_value'], expected_metric)
            self.assertEqual(row['display_value'], expected_display)

    def assert_metric_equal(self, actual, expected):
        if expected is None:
            self.assertIsNone(actual)
        else:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))


if __name__ == '__main__':
    unittest.main()
