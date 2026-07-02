"""
Build static HTML pages from cached MLB JSON files.

Run locally to regenerate docs/index.html, docs/pitcher-era.html, and
docs/batter-average.html for GitHub Pages.
"""
import json
from pathlib import Path


REQUIRED_YEARS = [2021, 2022, 2023, 2024, 2025]
PLAYER_SEASONS = [2023, 2024, 2025]
PLAYER_PAGES = {
    'david-peterson': ('docs/pitcher-era.html', 'Pitcher ERA', 'David Peterson ERA'),
    'corey-seager': ('docs/batter-average.html', 'Batter AVG', 'Corey Seager Batting Average'),
}

ALL_TEAMS = [
    'ARI', 'ATL', 'BAL', 'BOS', 'CHC', 'CHW', 'CIN', 'CLE', 'COL', 'DET',
    'HOU', 'KCR', 'LAA', 'LAD', 'MIA', 'MIL', 'MIN', 'NYM', 'NYY', 'OAK',
    'PHI', 'PIT', 'SDP', 'SEA', 'SFG', 'STL', 'TBR', 'TEX', 'TOR', 'WSN',
]

TEAM_META = {
    'ARI': {'name': 'Arizona Diamondbacks', 'abbr': 'ARI', 'color': '#A71930', 'div': 'NL West'},
    'ATL': {'name': 'Atlanta Braves', 'abbr': 'ATL', 'color': '#CE1141', 'div': 'NL East'},
    'BAL': {'name': 'Baltimore Orioles', 'abbr': 'BAL', 'color': '#DF4601', 'div': 'AL East'},
    'BOS': {'name': 'Boston Red Sox', 'abbr': 'BOS', 'color': '#BD3039', 'div': 'AL East'},
    'CHC': {'name': 'Chicago Cubs', 'abbr': 'CHC', 'color': '#0E3386', 'div': 'NL Central'},
    'CHW': {'name': 'Chicago White Sox', 'abbr': 'CHW', 'color': '#27251F', 'div': 'AL Central'},
    'CIN': {'name': 'Cincinnati Reds', 'abbr': 'CIN', 'color': '#C6011F', 'div': 'NL Central'},
    'CLE': {'name': 'Cleveland Guardians', 'abbr': 'CLE', 'color': '#00385D', 'div': 'AL Central'},
    'COL': {'name': 'Colorado Rockies', 'abbr': 'COL', 'color': '#333366', 'div': 'NL West'},
    'DET': {'name': 'Detroit Tigers', 'abbr': 'DET', 'color': '#0C2340', 'div': 'AL Central'},
    'HOU': {'name': 'Houston Astros', 'abbr': 'HOU', 'color': '#EB6E1F', 'div': 'AL West'},
    'KCR': {'name': 'Kansas City Royals', 'abbr': 'KCR', 'color': '#004687', 'div': 'AL Central'},
    'LAA': {'name': 'Los Angeles Angels', 'abbr': 'LAA', 'color': '#BA0021', 'div': 'AL West'},
    'LAD': {'name': 'Los Angeles Dodgers', 'abbr': 'LAD', 'color': '#005A9C', 'div': 'NL West'},
    'MIA': {'name': 'Miami Marlins', 'abbr': 'MIA', 'color': '#00A3E0', 'div': 'NL East'},
    'MIL': {'name': 'Milwaukee Brewers', 'abbr': 'MIL', 'color': '#FFC52F', 'div': 'NL Central'},
    'MIN': {'name': 'Minnesota Twins', 'abbr': 'MIN', 'color': '#002B5C', 'div': 'AL Central'},
    'NYM': {'name': 'New York Mets', 'abbr': 'NYM', 'color': '#002D72', 'div': 'NL East'},
    'NYY': {'name': 'New York Yankees', 'abbr': 'NYY', 'color': '#003087', 'div': 'AL East'},
    'OAK': {'name': 'Oakland Athletics', 'abbr': 'OAK', 'color': '#003831', 'div': 'AL West'},
    'PHI': {'name': 'Philadelphia Phillies', 'abbr': 'PHI', 'color': '#E81828', 'div': 'NL East'},
    'PIT': {'name': 'Pittsburgh Pirates', 'abbr': 'PIT', 'color': '#FDB827', 'div': 'NL Central'},
    'SDP': {'name': 'San Diego Padres', 'abbr': 'SDP', 'color': '#2F241D', 'div': 'NL West'},
    'SEA': {'name': 'Seattle Mariners', 'abbr': 'SEA', 'color': '#0C2C56', 'div': 'AL West'},
    'SFG': {'name': 'San Francisco Giants', 'abbr': 'SFG', 'color': '#FD5A1E', 'div': 'NL West'},
    'STL': {'name': 'St. Louis Cardinals', 'abbr': 'STL', 'color': '#C41E3A', 'div': 'NL Central'},
    'TBR': {'name': 'Tampa Bay Rays', 'abbr': 'TBR', 'color': '#092C5C', 'div': 'AL East'},
    'TEX': {'name': 'Texas Rangers', 'abbr': 'TEX', 'color': '#003278', 'div': 'AL West'},
    'TOR': {'name': 'Toronto Blue Jays', 'abbr': 'TOR', 'color': '#134A8E', 'div': 'AL East'},
    'WSN': {'name': 'Washington Nationals', 'abbr': 'WSN', 'color': '#AB0003', 'div': 'NL East'},
}

DIVISIONS = ['AL East', 'AL Central', 'AL West', 'NL East', 'NL Central', 'NL West']


def dump_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).replace('</', '<\\/')


def load_json(path):
    return json.loads(Path(path).read_text())


def validate_team_cache(raw, year):
    if raw.get('year') != year:
        raise ValueError(f'data_{year}.json has year {raw.get("year")}')
    if not isinstance(raw.get('playoff_teams'), list):
        raise ValueError(f'data_{year}.json missing playoff_teams list')
    teams = raw.get('teams')
    if not isinstance(teams, dict):
        raise ValueError(f'data_{year}.json missing teams object')
    missing = [team for team in ALL_TEAMS if team not in teams]
    if missing:
        raise ValueError(f'data_{year}.json missing teams: {", ".join(missing)}')
    for team, games in teams.items():
        if team not in TEAM_META:
            raise ValueError(f'data_{year}.json has unknown team {team}')
        if not isinstance(games, list) or not games:
            raise ValueError(f'data_{year}.json has no games for {team}')
        for game in games:
            if not {'date', 'opp', 'won', 'wl'} <= set(game):
                raise ValueError(f'data_{year}.json has malformed {team} game row')


def load_team_caches():
    seasons = {}
    for year in REQUIRED_YEARS:
        path = Path(f'data_{year}.json')
        if not path.exists():
            raise FileNotFoundError(f'{path} is missing. Run fetch_data.py for required years.')
        raw = load_json(path)
        validate_team_cache(raw, year)
        seasons[str(year)] = {
            'year': raw['year'],
            'playoff_teams': raw['playoff_teams'],
            'teams': raw['teams'],
        }
    return seasons


def validate_player_cache(raw):
    if raw.get('schema_version') != 1:
        raise ValueError('player_progressions.json schema_version must be 1')
    if raw.get('seasons') != PLAYER_SEASONS:
        raise ValueError('player_progressions.json must contain seasons 2023, 2024, and 2025')
    players = raw.get('players')
    if not isinstance(players, dict):
        raise ValueError('player_progressions.json missing players object')

    for slug, required_kind in [('david-peterson', 'pitcher'), ('corey-seager', 'batter')]:
        player = players.get(slug)
        if not player:
            raise ValueError(f'player_progressions.json missing {slug}')
        if player.get('kind') != required_kind:
            raise ValueError(f'player_progressions.json has wrong kind for {slug}')
        for season in PLAYER_SEASONS:
            rows = player.get('seasons', {}).get(str(season))
            if not isinstance(rows, list):
                raise ValueError(f'player_progressions.json missing {slug} {season}')
            for row in rows:
                common = {
                    'season', 'game_number', 'date', 'game_pk', 'opponent',
                    'home_away', 'metric_value', 'display_value',
                }
                if not common <= set(row):
                    raise ValueError(f'player_progressions.json has malformed {slug} {season} row')
                if required_kind == 'pitcher':
                    required = {'outs', 'earned_runs', 'cum_outs', 'cum_earned_runs'}
                else:
                    required = {'at_bats', 'hits', 'cum_at_bats', 'cum_hits'}
                if not required <= set(row):
                    raise ValueError(f'player_progressions.json has malformed {slug} {season} row')


def load_player_cache():
    path = Path('player_progressions.json')
    if not path.exists():
        raise FileNotFoundError('player_progressions.json is missing. Run fetch_data.py --players.')
    raw = load_json(path)
    validate_player_cache(raw)
    return raw


def common_css():
    return '''
        :root {
            --bg: #08080a; --bg-card: #0e0e12;
            --border: rgba(200,175,120,0.08); --gold: #c8af78;
            --gold-dim: rgba(200,175,120,0.3); --gold-faint: rgba(200,175,120,0.08);
            --text: #d0c8b8; --text-dim: #5a5548; --text-faint: #2a2825;
            --serif: 'Newsreader', Georgia, serif;
            --mono: 'Courier Prime', 'Courier New', monospace;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg); color: var(--text);
            font-family: var(--mono); -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }
        body::before {
            content: ''; position: fixed; inset: 0; z-index: 9999;
            pointer-events: none; opacity: 0.025;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }
        .container { max-width: 1440px; margin: 0 auto; padding: 50px 40px 80px; overflow-x: hidden; }
        .page-nav { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 36px; }
        .nav-link, .mode-btn, .season-select {
            font-family: var(--mono); font-size: 11px; letter-spacing: 0;
            text-transform: uppercase; padding: 8px 18px; background: transparent;
            color: var(--text-dim); border: 1px solid var(--border); cursor: pointer;
            text-decoration: none; transition: all 0.25s ease;
        }
        .season-select { min-width: 112px; color: var(--text); background: var(--bg-card); }
        .nav-link:hover, .mode-btn:hover, .season-select:hover { color: var(--gold); border-color: var(--gold-dim); }
        .nav-link.active, .mode-btn.active { color: var(--gold); border-color: var(--gold); background: var(--gold-faint); }
        .header { margin-bottom: 52px; position: relative; }
        .header::after { content: ''; display: block; width: 60px; height: 1px; background: var(--gold); margin-top: 30px; opacity: 0.4; }
        .eyebrow { font-size: 11px; letter-spacing: 0; text-transform: uppercase; color: var(--gold); opacity: 0.6; margin-bottom: 14px; }
        .title { font-family: var(--serif); font-size: 60px; font-weight: 300; line-height: 1.05; color: var(--text); letter-spacing: 0; margin-bottom: 16px; }
        .title em { font-style: italic; color: var(--gold); }
        .subtitle { font-family: var(--serif); font-size: 17px; font-weight: 300; line-height: 1.6; color: var(--text-dim); max-width: 640px; font-style: italic; }
        .controls-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
        .controls-bar .label { color: var(--text-dim); font-size: 10px; letter-spacing: 0; margin-right: 8px; text-transform: uppercase; }
        .main-grid { display: grid; grid-template-columns: 1fr 240px; gap: 40px; align-items: start; margin-top: 24px; }
        .chart-container {
            background: var(--bg-card); border: 1px solid var(--border);
            padding: 20px 10px 10px; position: relative;
        }
        .chart-container::before {
            content: 'WIN PERCENTAGE OVER THE SEASON'; position: absolute; top: 8px; left: 20px;
            font-size: 9px; letter-spacing: 0; color: var(--text-dim); opacity: 0.4;
        }
        .player-chart-container::before { content: 'SEASON PROGRESSION'; }
        .sidebar { position: sticky; top: 40px; }
        .sidebar-title { font-size: 10px; letter-spacing: 0; text-transform: uppercase; color: var(--gold); opacity: 0.5; margin-bottom: 20px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
        .division-block { margin-bottom: 20px; }
        .division-label { font-size: 9px; letter-spacing: 0; text-transform: uppercase; color: var(--text-dim); opacity: 0.5; margin-bottom: 6px; }
        .standing-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 12px; line-height: 1; }
        .standing-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
        .standing-abbr { width: 30px; font-weight: 700; font-size: 11px; color: var(--text); opacity: 0.7; }
        .standing-record { flex: 1; color: var(--text-dim); font-size: 11px; }
        .standing-pct { color: var(--text-dim); font-size: 11px; width: 36px; text-align: right; }
        .standing-playoff { font-size: 8px; font-weight: 700; letter-spacing: 0; color: var(--gold); opacity: 0.7; width: 30px; text-align: right; margin-left: 4px; }
        .footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; gap: 16px; }
        .footer-text { font-size: 10px; letter-spacing: 0; color: var(--text-dim); opacity: 0.4; }
        .js-plotly-plot .plotly .modebar { opacity: 0.3; }
        .js-plotly-plot .plotly .modebar:hover { opacity: 0.7; }
        @media (max-width: 1000px) {
            .main-grid { grid-template-columns: 1fr; }
            .sidebar { position: static; }
        }
        @media (max-width: 600px) {
            .container { padding: 24px 16px 40px; }
            .page-nav { margin-bottom: 28px; }
            .header { margin-bottom: 30px; }
            .title { font-size: 34px; margin-bottom: 10px; }
            .subtitle { font-size: 14px; }
            .controls-bar { gap: 4px; margin-bottom: 8px; }
            .controls-bar .label { font-size: 9px; margin-right: 4px; }
            .mode-btn, .nav-link, .season-select { font-size: 9px; padding: 6px 10px; }
            .chart-container { padding: 10px 2px 2px; }
            .chart-container::before { font-size: 7px; top: 3px; left: 8px; }
            .footer { flex-direction: column; gap: 4px; }
            .footer-text { font-size: 9px; }
        }
    '''


INDEX_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Season Tracker</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,700;1,6..72,300;1,6..72,400&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>COMMON_CSS_PLACEHOLDER</style>
</head>
<body>
<div class="container">
    <nav class="page-nav">
        <a href="index.html" class="nav-link active">Team Tracker</a>
        <a href="pitcher-era.html" class="nav-link">Pitcher ERA</a>
        <a href="batter-average.html" class="nav-link">Batter AVG</a>
    </nav>

    <div class="header">
        <div class="eyebrow">MAJOR LEAGUE BASEBALL</div>
        <h1 class="title" id="title"></h1>
        <p class="subtitle" id="subtitle"></p>
    </div>

    <div class="controls-bar">
        <span class="label">SEASON</span>
        <select class="season-select" id="season-select" onchange="setSeason(this)">SEASON_OPTIONS_PLACEHOLDER</select>
    </div>
    <div class="controls-bar">
        <span class="label">VIEW</span>
        <button class="mode-btn active" data-view="smooth" onclick="setView(this)">SMOOTHED</button>
        <button class="mode-btn" data-view="raw" onclick="setView(this)">RAW</button>
        <button class="mode-btn" data-view="facet" onclick="setView(this)">BY DIVISION</button>
    </div>
    <div class="controls-bar" id="filter-bar">
        <span class="label">FILTER</span>
        <button class="mode-btn active" data-filter="all" onclick="setFilter(this)">ALL TEAMS</button>
        <button class="mode-btn" data-filter="playoffs" onclick="setFilter(this)">PLAYOFF TEAMS</button>
        <button class="mode-btn" data-filter="AL East" onclick="setFilter(this)">AL EAST</button>
        <button class="mode-btn" data-filter="AL Central" onclick="setFilter(this)">AL CENTRAL</button>
        <button class="mode-btn" data-filter="AL West" onclick="setFilter(this)">AL WEST</button>
        <button class="mode-btn" data-filter="NL East" onclick="setFilter(this)">NL EAST</button>
        <button class="mode-btn" data-filter="NL Central" onclick="setFilter(this)">NL CENTRAL</button>
        <button class="mode-btn" data-filter="NL West" onclick="setFilter(this)">NL WEST</button>
    </div>

    <div class="main-grid">
        <div class="chart-container"><div id="chart"></div></div>
        <div class="sidebar" id="standings"></div>
    </div>

    <div class="footer">
        <span class="footer-text">DATA: MLB STATS API CACHE</span>
        <span class="footer-text" id="footer-season"></span>
    </div>
</div>

<script>
const SEASON_DATA = SEASON_DATA_PLACEHOLDER;
const TEAM_META = TEAM_META_PLACEHOLDER;
const ALL_TEAMS = ALL_TEAMS_PLACEHOLDER;
const DIVISIONS = DIVISIONS_PLACEHOLDER;
const SMOOTH_WINDOW = 15;

let currentYear = String(Math.max(...Object.keys(SEASON_DATA).map(Number)));
let currentView = 'smooth';
let currentFilter = 'all';

function brighten(hex) {
    let red = parseInt(hex.slice(1, 3), 16);
    let green = parseInt(hex.slice(3, 5), 16);
    let blue = parseInt(hex.slice(5, 7), 16);
    if (red + green + blue < 120) {
        red = Math.min(255, red + 80);
        green = Math.min(255, green + 80);
        blue = Math.min(255, blue + 80);
    }
    return '#' + [red, green, blue].map(v => v.toString(16).padStart(2, '0')).join('');
}

function rolling(values) {
    return values.map((_, index) => {
        const start = Math.max(0, index - SMOOTH_WINDOW + 1);
        const window = values.slice(start, index + 1);
        return window.reduce((sum, value) => sum + value, 0) / window.length;
    });
}

function cumulativeGames(games) {
    let wins = 0;
    return games.map((game, index) => {
        const gameNum = index + 1;
        if (game.won) wins += 1;
        const losses = gameNum - wins;
        return {
            game_num: gameNum,
            date: game.date,
            opp: game.opp,
            wl: game.wl,
            won: game.won,
            cum_wins: wins,
            cum_losses: losses,
            win_pct: wins / gameNum * 100
        };
    });
}

function hoverText(meta, points) {
    return points.map(point =>
        `${meta.name}<br>Game ${point.game_num} | ${point.win_pct.toFixed(1)}%<br>` +
        `${point.cum_wins}W ${point.cum_losses}L<br>${point.date}<br>vs ${point.opp} ${point.wl}`
    );
}

function baseLayout(height) {
    return {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {family: 'Courier Prime, monospace', color: '#8a8070'},
        hovermode: 'closest',
        dragmode: 'zoom',
        height: height,
        margin: {t: 10, b: 40, l: 60, r: 20},
        xaxis: {
            range: [0, 165], showgrid: false, zeroline: false,
            title: {text: 'GAME', font: {size: 10, color: 'rgba(200,175,120,0.3)'}},
            tickfont: {size: 10, color: 'rgba(200,175,120,0.25)'}, dtick: 40
        },
        yaxis: {
            range: [0, 100], showgrid: true, gridcolor: 'rgba(200,175,120,0.04)',
            zeroline: false,
            title: {text: 'WIN %', font: {size: 10, color: 'rgba(200,175,120,0.3)'}},
            ticksuffix: '%', tickfont: {size: 10, color: 'rgba(200,175,120,0.25)'}, dtick: 10
        },
        legend: {
            font: {size: 10, family: 'Courier Prime, monospace', color: '#6a6050'},
            bgcolor: 'rgba(0,0,0,0)', borderwidth: 0, itemsizing: 'constant', tracegroupgap: 2
        },
        shapes: [{
            type: 'line', x0: 1, x1: 165, y0: 50, y1: 50,
            line: {color: 'rgba(200,175,120,0.15)', width: 1, dash: 'dot'}
        }],
        annotations: [{
            x: 166, y: 50, text: '.500', showarrow: false, xanchor: 'left',
            font: {color: 'rgba(200,175,120,0.3)', size: 11, family: 'Courier Prime, monospace'}
        }]
    };
}

function selectedTeams() {
    const teams = SEASON_DATA[currentYear].teams;
    const available = ALL_TEAMS.filter(team => teams[team]);
    if (DIVISIONS.includes(currentFilter)) {
        return available.filter(team => TEAM_META[team].div === currentFilter);
    }
    return available;
}

function buildCombined() {
    const data = [];
    const teams = SEASON_DATA[currentYear].teams;
    const playoffTeams = new Set(SEASON_DATA[currentYear].playoff_teams);
    const isSmooth = currentView === 'smooth';
    const mode = currentFilter === 'playoffs' ? 'playoffs' : (DIVISIONS.includes(currentFilter) ? 'division' : 'all');

    selectedTeams().forEach(team => {
        const meta = TEAM_META[team];
        const points = cumulativeGames(teams[team]);
        const smoothValues = rolling(points.map(point => point.win_pct));
        const isPlayoff = playoffTeams.has(team);
        const final = points[points.length - 1];
        const dimmed = mode === 'playoffs' && !isPlayoff;
        let opacity = 0.7;
        let width = 1.8;
        if (dimmed) {
            opacity = 0.08; width = 1;
        } else if (mode === 'playoffs' && isPlayoff) {
            opacity = 1.0; width = 2.5;
        } else if (mode === 'division') {
            opacity = 0.9; width = 2.2;
        }
        const color = brighten(meta.color);
        const label = `${meta.abbr}  ${final.cum_wins}-${final.cum_losses}${isPlayoff ? '  POST' : ''}`;
        const x = points.map(point => point.game_num);

        if (isSmooth) {
            data.push({
                x: x,
                y: points.map(point => point.win_pct),
                name: label,
                mode: 'lines',
                showlegend: false,
                line: {color: color, width: 0.5},
                opacity: opacity * 0.2,
                hoverinfo: 'skip'
            });
        }

        data.push({
            x: x,
            y: isSmooth ? smoothValues : points.map(point => point.win_pct),
            name: label,
            mode: 'lines',
            line: {color: color, width: width + (isSmooth ? 0.5 : 0)},
            opacity: opacity,
            text: dimmed ? null : hoverText(meta, points),
            hoverinfo: dimmed ? 'skip' : 'text',
            showlegend: !dimmed
        });
    });

    return {data: data, layout: baseLayout(680)};
}

function axisName(prefix, index) {
    return index === 1 ? prefix : prefix + index;
}

function layoutAxisName(prefix, index) {
    return index === 1 ? prefix + 'axis' : prefix + 'axis' + index;
}

function buildFacet() {
    const data = [];
    const teams = SEASON_DATA[currentYear].teams;
    const playoffTeams = new Set(SEASON_DATA[currentYear].playoff_teams);
    const layout = baseLayout(700);
    layout.margin = {t: 40, b: 30, l: 50, r: 40};
    layout.showlegend = false;
    layout.grid = {rows: 2, columns: 3, pattern: 'independent'};
    layout.shapes = [];
    layout.annotations = [];

    DIVISIONS.forEach((division, divIndex) => {
        const index = divIndex + 1;
        const xRef = axisName('x', index);
        const yRef = axisName('y', index);
        const xAxisKey = layoutAxisName('x', index);
        const yAxisKey = layoutAxisName('y', index);
        layout[xAxisKey] = {
            range: [0, 170], showgrid: false, zeroline: false,
            tickfont: {size: 9, color: 'rgba(200,175,120,0.2)'}, dtick: 40
        };
        layout[yAxisKey] = {
            range: [0, 100], showgrid: true, gridcolor: 'rgba(200,175,120,0.04)',
            zeroline: false, ticksuffix: '%',
            tickfont: {size: 9, color: 'rgba(200,175,120,0.2)'}, dtick: 10
        };
        layout.shapes.push({
            type: 'line', xref: xRef, yref: yRef, x0: 1, x1: 165, y0: 50, y1: 50,
            line: {color: 'rgba(200,175,120,0.12)', width: 1, dash: 'dot'}
        });
        layout.annotations.push({
            text: division, xref: 'paper', yref: 'paper',
            x: (divIndex % 3) / 3 + 0.15, y: divIndex < 3 ? 1.03 : 0.48,
            showarrow: false,
            font: {size: 11, color: 'rgba(200,175,120,0.5)', family: 'Courier Prime, monospace'}
        });

        ALL_TEAMS
            .filter(team => teams[team] && TEAM_META[team].div === division)
            .sort((a, b) => {
                const aPoints = cumulativeGames(teams[a]);
                const bPoints = cumulativeGames(teams[b]);
                return bPoints[bPoints.length - 1].win_pct - aPoints[aPoints.length - 1].win_pct;
            })
            .forEach(team => {
                const meta = TEAM_META[team];
                const points = cumulativeGames(teams[team]);
                const smoothValues = rolling(points.map(point => point.win_pct));
                const isPlayoff = playoffTeams.has(team);
                const final = points[points.length - 1];
                const color = brighten(meta.color);
                const axisProps = index === 1 ? {} : {xaxis: xRef, yaxis: yRef};
                data.push({
                    ...axisProps,
                    x: points.map(point => point.game_num),
                    y: points.map(point => point.win_pct),
                    mode: 'lines',
                    showlegend: false,
                    line: {color: color, width: 0.5},
                    opacity: 0.15,
                    hoverinfo: 'skip'
                });
                data.push({
                    ...axisProps,
                    x: points.map(point => point.game_num),
                    y: smoothValues,
                    name: `${meta.abbr} ${final.cum_wins}-${final.cum_losses}${isPlayoff ? ' *' : ''}`,
                    mode: 'lines',
                    line: {color: color, width: 2.5},
                    opacity: isPlayoff ? 0.95 : 0.7,
                    text: hoverText(meta, points),
                    hoverinfo: 'text'
                });
                layout.annotations.push({
                    xref: xRef, yref: yRef, x: 161, y: smoothValues[smoothValues.length - 1],
                    text: ` ${meta.abbr}`, showarrow: false, xanchor: 'left',
                    font: {size: 9, color: color, family: 'Courier Prime, monospace'},
                    opacity: 0.8
                });
            });
    });
    return {data: data, layout: layout};
}

function pctText(value) {
    return '.' + String(Math.floor(value * 1000)).padStart(3, '0');
}

function renderStandings() {
    const teams = SEASON_DATA[currentYear].teams;
    const playoffTeams = new Set(SEASON_DATA[currentYear].playoff_teams);
    const standings = ALL_TEAMS
        .filter(team => teams[team])
        .map(team => {
            const points = cumulativeGames(teams[team]);
            const final = points[points.length - 1];
            return {
                team: team,
                w: final.cum_wins,
                l: final.cum_losses,
                pct: final.cum_wins / points.length,
                div: TEAM_META[team].div,
                color: TEAM_META[team].color,
                playoff: playoffTeams.has(team)
            };
        });
    let html = `<div class="sidebar-title">${currentYear} FINAL STANDINGS</div>`;
    DIVISIONS.forEach(division => {
        html += `<div class="division-block"><div class="division-label">${division}</div>`;
        standings
            .filter(team => team.div === division)
            .sort((a, b) => b.pct - a.pct)
            .forEach(team => {
                html += `<div class="standing-row">` +
                    `<span class="standing-dot" style="background:${team.color}"></span>` +
                    `<span class="standing-abbr">${team.team}</span>` +
                    `<span class="standing-record">${team.w}-${team.l}</span>` +
                    `<span class="standing-pct">${pctText(team.pct)}</span>` +
                    `${team.playoff ? '<span class="standing-playoff">POST</span>' : ''}` +
                    `</div>`;
            });
        html += '</div>';
    });
    document.getElementById('standings').innerHTML = html;
}

function renderHeader() {
    document.getElementById('title').innerHTML = `<em>${currentYear}</em> Win Rates Over Time`;
    document.getElementById('subtitle').textContent =
        `Every team's win percentage, game by game across the full ${currentYear} season.`;
    document.getElementById('footer-season').textContent = `${currentYear} REGULAR SEASON`;
}

function renderChart() {
    const built = currentView === 'facet' ? buildFacet() : buildCombined();
    const isMobile = window.innerWidth < 600;
    if (isMobile) {
        built.layout.height = currentView === 'facet' ? 620 : 350;
        built.layout.margin = {t: 10, b: 30, l: 40, r: 10};
        if (built.layout.yaxis) built.layout.yaxis.title = null;
        if (built.layout.xaxis) built.layout.xaxis.title = null;
    } else if (window.innerWidth < 1000) {
        built.layout.height = currentView === 'facet' ? 680 : 500;
        built.layout.margin = {t: 20, b: 35, l: 50, r: 15};
    }
    Plotly.react('chart', built.data, built.layout, {
        displayModeBar: !isMobile,
        responsive: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    });
}

function setSeason(select) {
    currentYear = select.value;
    renderHeader();
    renderStandings();
    renderChart();
}

function setView(btn) {
    document.querySelectorAll('[data-view]').forEach(button => button.classList.remove('active'));
    btn.classList.add('active');
    currentView = btn.dataset.view;
    document.getElementById('filter-bar').style.display = currentView === 'facet' ? 'none' : 'flex';
    renderChart();
}

function setFilter(btn) {
    document.querySelectorAll('[data-filter]').forEach(button => button.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderChart();
}

document.getElementById('season-select').value = currentYear;
renderHeader();
renderStandings();
renderChart();
window.addEventListener('resize', () => {
    clearTimeout(window._resizeTimer);
    window._resizeTimer = setTimeout(renderChart, 200);
});
</script>
</body>
</html>'''


PLAYER_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PAGE_TITLE_PLACEHOLDER</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,700;1,6..72,300;1,6..72,400&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>COMMON_CSS_PLACEHOLDER</style>
</head>
<body>
<div class="container">
    <nav class="page-nav">
        <a href="index.html" class="nav-link">Team Tracker</a>
        <a href="pitcher-era.html" class="nav-link PITCHER_ACTIVE_PLACEHOLDER">Pitcher ERA</a>
        <a href="batter-average.html" class="nav-link BATTER_ACTIVE_PLACEHOLDER">Batter AVG</a>
    </nav>

    <div class="header">
        <div class="eyebrow">PLAYER PROGRESSION</div>
        <h1 class="title" id="player-title"></h1>
        <p class="subtitle" id="player-subtitle"></p>
    </div>

    <div class="chart-container player-chart-container"><div id="chart"></div></div>

    <div class="footer">
        <span class="footer-text">DATA: MLB STATS API CACHE</span>
        <span class="footer-text">2023-2025 REGULAR SEASONS</span>
    </div>
</div>

<script>
const PLAYER_CACHE = PLAYER_CACHE_PLACEHOLDER;
const PLAYER_KEY = 'PLAYER_KEY_PLACEHOLDER';
const PLAYER_COLORS = {'2023':'#c8af78','2024':'#7ab6d6','2025':'#d97a62'};
const player = PLAYER_CACHE.players[PLAYER_KEY];

function hoverRow(row) {
    let detail;
    if (player.kind === 'pitcher') {
        detail = `Outs: ${row.outs} | ER: ${row.earned_runs}<br>` +
            `Cumulative: ${row.cum_outs} outs, ${row.cum_earned_runs} ER`;
    } else {
        detail = `AB: ${row.at_bats} | H: ${row.hits}<br>` +
            `Cumulative: ${row.cum_at_bats} AB, ${row.cum_hits} H`;
    }
    return `${player.name}<br>${row.season} game ${row.game_number}<br>` +
        `${row.date} vs ${row.opponent} (${row.home_away})<br>` +
        `${detail}<br>${player.metric_label}: ${row.display_value}`;
}

function renderHeader() {
    const titleMetric = player.kind === 'pitcher' ? 'ERA' : 'Batting Average';
    document.getElementById('player-title').innerHTML = `${player.name}<br><em>${titleMetric}</em>`;
    document.getElementById('player-subtitle').textContent =
        `${player.name} game-by-game ${titleMetric.toLowerCase()} progression for ${PLAYER_CACHE.seasons.join(', ')}.`;
}

function renderChart() {
    const traces = PLAYER_CACHE.seasons.map(season => {
        const key = String(season);
        const rows = player.seasons[key] || [];
        return {
            x: rows.map(row => row.game_number),
            y: rows.map(row => row.metric_value),
            name: key,
            mode: 'lines+markers',
            line: {color: PLAYER_COLORS[key] || '#c8af78', width: 2.5},
            marker: {size: 4},
            text: rows.map(hoverRow),
            hoverinfo: 'text',
            connectgaps: false
        };
    });
    const values = traces.flatMap(trace => trace.y).filter(value => value !== null);
    const yaxis = {
        showgrid: true,
        gridcolor: 'rgba(200,175,120,0.05)',
        zeroline: false,
        title: {text: player.metric_label, font: {size: 10, color: 'rgba(200,175,120,0.35)'}},
        tickfont: {size: 10, color: 'rgba(200,175,120,0.25)'},
        rangemode: 'tozero'
    };
    if (player.metric === 'batting_average') {
        const maxValue = Math.max(0.4, ...(values.length ? values : [0.4]));
        yaxis.tickformat = '.3f';
        yaxis.range = [0, maxValue * 1.08];
    }
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {family: 'Courier Prime, monospace', color: '#8a8070'},
        hovermode: 'closest',
        dragmode: 'zoom',
        height: window.innerWidth < 600 ? 380 : 640,
        margin: window.innerWidth < 600 ? {t: 34, b: 35, l: 44, r: 10} : {t: 40, b: 40, l: 60, r: 20},
        xaxis: {
            showgrid: false,
            zeroline: false,
            title: {text: 'GAME', font: {size: 10, color: 'rgba(200,175,120,0.35)'}},
            tickfont: {size: 10, color: 'rgba(200,175,120,0.25)'},
            dtick: 20
        },
        yaxis: yaxis,
        legend: {
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1,
            font: {size: 10, family: 'Courier Prime, monospace', color: '#6a6050'},
            bgcolor: 'rgba(0,0,0,0)',
            borderwidth: 0
        }
    };
    Plotly.react('chart', traces, layout, {
        displayModeBar: window.innerWidth >= 600,
        responsive: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    });
}

renderHeader();
renderChart();
window.addEventListener('resize', () => {
    clearTimeout(window._resizeTimer);
    window._resizeTimer = setTimeout(renderChart, 200);
});
</script>
</body>
</html>'''


def build_index(seasons):
    options = ''.join(f'<option value="{year}">{year}</option>' for year in REQUIRED_YEARS)
    html = INDEX_TEMPLATE
    html = html.replace('COMMON_CSS_PLACEHOLDER', common_css())
    html = html.replace('SEASON_OPTIONS_PLACEHOLDER', options)
    html = html.replace('SEASON_DATA_PLACEHOLDER', dump_json(seasons))
    html = html.replace('TEAM_META_PLACEHOLDER', dump_json(TEAM_META))
    html = html.replace('ALL_TEAMS_PLACEHOLDER', dump_json(ALL_TEAMS))
    html = html.replace('DIVISIONS_PLACEHOLDER', dump_json(DIVISIONS))
    return html


def build_player_page(player_cache, player_key, page_title):
    html = PLAYER_TEMPLATE
    html = html.replace('COMMON_CSS_PLACEHOLDER', common_css())
    html = html.replace('PAGE_TITLE_PLACEHOLDER', page_title)
    html = html.replace('PLAYER_CACHE_PLACEHOLDER', dump_json(player_cache))
    html = html.replace('PLAYER_KEY_PLACEHOLDER', player_key)
    html = html.replace(
        'PITCHER_ACTIVE_PLACEHOLDER',
        'active' if player_key == 'david-peterson' else '',
    )
    html = html.replace(
        'BATTER_ACTIVE_PLACEHOLDER',
        'active' if player_key == 'corey-seager' else '',
    )
    return html


def main():
    print('Loading cached seasons...')
    seasons = load_team_caches()
    print(f'Loaded seasons: {", ".join(seasons)}')

    print('Loading player progressions...')
    player_cache = load_player_cache()

    docs = Path('docs')
    docs.mkdir(exist_ok=True)

    print('Building docs/index.html...')
    index_html = build_index(seasons)
    (docs / 'index.html').write_text(index_html)
    print(f'Built docs/index.html ({len(index_html) // 1024} KB)')

    for player_key, (path, _, title) in PLAYER_PAGES.items():
        print(f'Building {path}...')
        html = build_player_page(player_cache, player_key, title)
        Path(path).write_text(html)
        print(f'Built {path} ({len(html) // 1024} KB)')

    print('Done!')


if __name__ == '__main__':
    main()
