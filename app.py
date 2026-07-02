import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, callback, clientside_callback, dcc, html
import warnings

warnings.filterwarnings('ignore')


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

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
SMOOTH_WINDOW = 15
PLAYER_ROUTES = {
    '/pitcher-era': 'david-peterson',
    '/batter-average': 'corey-seager',
}
PLAYER_COLORS = {
    '2023': '#c8af78',
    '2024': '#7ab6d6',
    '2025': '#d97a62',
}


# ---------------------------------------------------------------------------
# Cache loading
# ---------------------------------------------------------------------------

def validate_team_cache(raw, year):
    if raw.get('year') != year:
        raise ValueError(f"data_{year}.json has year {raw.get('year')}")
    if not isinstance(raw.get('playoff_teams'), list):
        raise ValueError(f"data_{year}.json missing playoff_teams list")
    teams = raw.get('teams')
    if not isinstance(teams, dict):
        raise ValueError(f"data_{year}.json missing teams object")
    for team, games in teams.items():
        if team not in TEAM_META or not isinstance(games, list):
            raise ValueError(f"data_{year}.json has invalid team {team}")
        for game in games:
            if not {'date', 'opp', 'won', 'wl'} <= set(game):
                raise ValueError(f"data_{year}.json has malformed {team} game row")


def discover_cached_years():
    years = []
    for path in Path('.').glob('data_*.json'):
        match = re.fullmatch(r'data_(\d{4})\.json', path.name)
        if not match:
            continue
        year = int(match.group(1))
        try:
            raw = json.loads(path.read_text())
            validate_team_cache(raw, year)
        except Exception:
            continue
        years.append(year)
    return sorted(set(years))


VALID_YEARS = discover_cached_years()
if not VALID_YEARS:
    raise SystemExit("No valid cached season files found. Run .venv/bin/python fetch_data.py first.")

try:
    requested_year = int(sys.argv[1])
except (IndexError, ValueError):
    requested_year = None
DEFAULT_YEAR = requested_year if requested_year in VALID_YEARS else VALID_YEARS[-1]


@lru_cache(maxsize=None)
def load_team_cache(year):
    path = Path(f'data_{year}.json')
    raw = json.loads(path.read_text())
    validate_team_cache(raw, year)

    season_data = {}
    for team in ALL_TEAMS:
        games = raw['teams'].get(team, [])
        if not games:
            continue
        df = pd.DataFrame(games)
        df['game_num'] = range(1, len(df) + 1)
        df['is_win'] = df['won'].astype(int)
        df['cum_wins'] = df['is_win'].cumsum()
        df['cum_losses'] = df['game_num'] - df['cum_wins']
        df['win_pct'] = (df['cum_wins'] / df['game_num']) * 100
        df['win_pct_smooth'] = df['win_pct'].rolling(
            SMOOTH_WINDOW, min_periods=1, center=False
        ).mean()
        df['team'] = team
        df['Opp'] = df['opp']
        df['Date'] = df['date']
        df['W/L'] = df['wl']
        season_data[team] = df

    return season_data, set(raw['playoff_teams'])


@lru_cache(maxsize=1)
def load_player_progressions():
    path = Path('player_progressions.json')
    if not path.exists():
        raise FileNotFoundError("player_progressions.json is missing. Run fetch_data.py --players.")
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def brighten(hex_color):
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    if red + green + blue < 120:
        red, green, blue = min(255, red + 80), min(255, green + 80), min(255, blue + 80)
    return f'#{red:02x}{green:02x}{blue:02x}'


def add_reference_lines(fig):
    fig.add_shape(
        type='line', x0=1, x1=165, y0=50, y1=50,
        line=dict(color='rgba(200,175,120,0.15)', width=1, dash='dot'),
    )
    fig.add_annotation(
        x=166, y=50, text='.500', showarrow=False, xanchor='left',
        font=dict(color='rgba(200,175,120,0.3)', size=11, family='Courier Prime, monospace'),
    )


CHART_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Courier Prime, monospace', color='#8a8070'),
    hovermode='closest',
    dragmode='zoom',
)


def axis_style(show_title=True):
    return dict(
        xaxis=dict(
            range=[0, 165], showgrid=False, zeroline=False,
            title=dict(text='GAME', font=dict(size=10, color='rgba(200,175,120,0.3)')) if show_title else None,
            tickfont=dict(size=10, color='rgba(200,175,120,0.25)'), dtick=40,
        ),
        yaxis=dict(
            range=[0, 100], showgrid=True, gridcolor='rgba(200,175,120,0.04)',
            zeroline=False,
            title=dict(text='WIN %', font=dict(size=10, color='rgba(200,175,120,0.3)')) if show_title else None,
            ticksuffix='%', tickfont=dict(size=10, color='rgba(200,175,120,0.25)'), dtick=10,
        ),
    )


def make_hover_text(meta, df):
    return [
        f"{meta['name']}<br>"
        f"Game {game_num} | {win_pct:.1f}%<br>"
        f"{int(cum_wins)}W {int(cum_losses)}L<br>"
        f"{date}<br>"
        f"vs {opponent} {wl}"
        for game_num, win_pct, cum_wins, cum_losses, date, opponent, wl in zip(
            df['game_num'], df['win_pct'], df['cum_wins'], df['cum_losses'],
            df['Date'], df['Opp'], df['W/L'],
        )
    ]


def available_teams_for_year(year):
    season_data, _ = load_team_cache(int(year))
    return [team for team in ALL_TEAMS if team in season_data]


def build_combined(year, selected_teams, mode, smooth=False):
    season_data, playoff_teams = load_team_cache(int(year))
    fig = go.Figure()
    add_reference_lines(fig)
    y_col = 'win_pct_smooth' if smooth else 'win_pct'

    for team in selected_teams:
        if team not in season_data:
            continue
        df = season_data[team]
        meta = TEAM_META[team]
        is_playoff = team in playoff_teams
        final_wins = int(df['cum_wins'].iloc[-1])
        final_losses = int(df['cum_losses'].iloc[-1])
        dimmed = mode == 'playoffs' and not is_playoff

        if dimmed:
            opacity, width = 0.08, 1
        elif mode == 'playoffs' and is_playoff:
            opacity, width = 1.0, 2.5
        elif mode == 'division':
            opacity, width = 0.9, 2.2
        else:
            opacity, width = 0.7, 1.8

        team_color = brighten(meta['color'])
        suffix = '  POST' if is_playoff else ''
        label = f'{meta["abbr"]}  {final_wins}-{final_losses}{suffix}'

        if smooth:
            fig.add_trace(go.Scatter(
                x=df['game_num'].values,
                y=df['win_pct'].values,
                name=label,
                mode='lines',
                showlegend=False,
                line=dict(color=team_color, width=0.5),
                opacity=opacity * 0.2,
                hoverinfo='skip',
            ))

        fig.add_trace(go.Scatter(
            x=df['game_num'].values,
            y=df[y_col].values,
            name=label,
            mode='lines',
            line=dict(color=team_color, width=width + (0.5 if smooth else 0)),
            opacity=opacity,
            text=make_hover_text(meta, df) if not dimmed else None,
            hoverinfo='text' if not dimmed else 'skip',
            showlegend=not dimmed,
        ))

    fig.update_layout(
        **CHART_LAYOUT,
        height=680,
        **axis_style(),
        legend=dict(
            font=dict(size=10, family='Courier Prime, monospace', color='#6a6050'),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0,
            itemsizing='constant',
            tracegroupgap=2,
        ),
        margin=dict(t=10, b=40, l=60, r=20),
    )
    return fig


from plotly.subplots import make_subplots


def build_faceted(year):
    season_data, playoff_teams = load_team_cache(int(year))
    available_teams = available_teams_for_year(year)
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[division for division in DIVISIONS],
        horizontal_spacing=0.06,
        vertical_spacing=0.10,
    )

    for index, division in enumerate(DIVISIONS):
        row, col = (index // 3) + 1, (index % 3) + 1
        division_teams = sorted(
            [team for team in available_teams if TEAM_META[team]['div'] == division],
            key=lambda team: season_data[team]['win_pct'].iloc[-1],
            reverse=True,
        )

        fig.add_shape(
            type='line', x0=1, x1=165, y0=50, y1=50,
            line=dict(color='rgba(200,175,120,0.12)', width=1, dash='dot'),
            row=row, col=col,
        )

        for team in division_teams:
            df = season_data[team]
            meta = TEAM_META[team]
            is_playoff = team in playoff_teams
            final_wins = int(df['cum_wins'].iloc[-1])
            final_losses = int(df['cum_losses'].iloc[-1])
            team_color = brighten(meta['color'])
            suffix = ' *' if is_playoff else ''
            label = f'{meta["abbr"]} {final_wins}-{final_losses}{suffix}'

            fig.add_trace(go.Scatter(
                x=df['game_num'].values,
                y=df['win_pct'].values,
                mode='lines',
                showlegend=False,
                line=dict(color=team_color, width=0.5),
                opacity=0.15,
                hoverinfo='skip',
            ), row=row, col=col)

            fig.add_trace(go.Scatter(
                x=df['game_num'].values,
                y=df['win_pct_smooth'].values,
                name=label,
                mode='lines',
                line=dict(color=team_color, width=2.5),
                opacity=0.95 if is_playoff else 0.7,
                text=make_hover_text(meta, df),
                hoverinfo='text',
                legendgroup=division,
            ), row=row, col=col)

            fig.add_annotation(
                x=161,
                y=df['win_pct_smooth'].iloc[-1],
                text=f' {meta["abbr"]}',
                showarrow=False,
                xanchor='left',
                font=dict(size=9, color=team_color, family='Courier Prime, monospace'),
                opacity=0.8,
                row=row,
                col=col,
            )

    fig.update_layout(
        **CHART_LAYOUT,
        height=700,
        showlegend=False,
        margin=dict(t=40, b=30, l=50, r=40),
    )

    for index in range(1, 7):
        x_key = f'xaxis{index}' if index > 1 else 'xaxis'
        y_key = f'yaxis{index}' if index > 1 else 'yaxis'
        fig.update_layout(**{
            x_key: dict(
                range=[0, 170], showgrid=False, zeroline=False,
                tickfont=dict(size=9, color='rgba(200,175,120,0.2)'), dtick=40,
            ),
            y_key: dict(
                range=[0, 100], showgrid=True, gridcolor='rgba(200,175,120,0.04)',
                zeroline=False, ticksuffix='%', tickfont=dict(size=9, color='rgba(200,175,120,0.2)'),
                dtick=10,
            ),
        })

    for annotation in fig.layout.annotations:
        annotation.font = dict(size=11, color='rgba(200,175,120,0.5)', family='Courier Prime, monospace')

    return fig


def selected_teams(year, filter_mode):
    available = available_teams_for_year(year)
    if filter_mode in DIVISIONS:
        return [team for team in available if TEAM_META[team]['div'] == filter_mode], 'division'
    return available, 'playoffs' if filter_mode == 'playoffs' else 'all'


def build_team_figure(year, filter_mode, style):
    if style == 'facet':
        return build_faceted(year)
    teams, mode = selected_teams(year, filter_mode)
    return build_combined(year, teams, mode, smooth=(style == 'smooth'))


def build_standings(year):
    season_data, playoff_teams = load_team_cache(int(year))
    standings = []
    for team, df in season_data.items():
        wins = int(df['cum_wins'].iloc[-1])
        losses = int(df['cum_losses'].iloc[-1])
        standings.append({
            'team': team,
            'color': TEAM_META[team]['color'],
            'div': TEAM_META[team]['div'],
            'w': wins,
            'l': losses,
            'pct': wins / (wins + losses),
            'playoff': team in playoff_teams,
        })
    standings.sort(key=lambda item: item['pct'], reverse=True)
    return standings


def division_block(year, division_name):
    standings = build_standings(year)
    teams_in_division = sorted(
        [team for team in standings if team['div'] == division_name],
        key=lambda item: item['pct'],
        reverse=True,
    )
    return html.Div(className='division-block', children=[
        html.Div(division_name, className='division-label'),
        *[html.Div(className='standing-row', children=[
            html.Span(className='standing-dot', style={'backgroundColor': standing['color']}),
            html.Span(standing['team'], className='standing-abbr'),
            html.Span(f'{standing["w"]}-{standing["l"]}', className='standing-record'),
            html.Span(f'.{int(standing["pct"] * 1000):03d}', className='standing-pct'),
            html.Span('POST', className='standing-playoff') if standing['playoff'] else None,
        ]) for standing in teams_in_division],
    ])


def standings_sidebar(year):
    return [
        html.Div(f'{year} FINAL STANDINGS', className='sidebar-title'),
        *[division_block(year, division) for division in DIVISIONS],
    ]


def player_hover_rows(player, rows):
    hover_text = []
    for row in rows:
        if player['kind'] == 'pitcher':
            details = (
                f"Outs: {row['outs']} | ER: {row['earned_runs']}<br>"
                f"Cumulative: {row['cum_outs']} outs, {row['cum_earned_runs']} ER"
            )
        else:
            details = (
                f"AB: {row['at_bats']} | H: {row['hits']}<br>"
                f"Cumulative: {row['cum_at_bats']} AB, {row['cum_hits']} H"
            )
        hover_text.append(
            f"{player['name']}<br>"
            f"{row['season']} game {row['game_number']}<br>"
            f"{row['date']} vs {row['opponent']} ({row['home_away']})<br>"
            f"{details}<br>"
            f"{player['metric_label']}: {row['display_value']}"
        )
    return hover_text


def build_player_figure(player_key):
    cache = load_player_progressions()
    player = cache['players'][player_key]
    fig = go.Figure()
    values = []

    for season in cache.get('seasons', [2023, 2024, 2025]):
        season_key = str(season)
        rows = player['seasons'].get(season_key, [])
        x_values = [row['game_number'] for row in rows]
        y_values = [row['metric_value'] for row in rows]
        values.extend(value for value in y_values if value is not None)
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            name=season_key,
            mode='lines+markers',
            line=dict(color=PLAYER_COLORS.get(season_key, '#c8af78'), width=2.5),
            marker=dict(size=4),
            text=player_hover_rows(player, rows),
            hoverinfo='text',
            connectgaps=False,
        ))

    y_axis = dict(
        showgrid=True,
        gridcolor='rgba(200,175,120,0.05)',
        zeroline=False,
        title=dict(text=player['metric_label'], font=dict(size=10, color='rgba(200,175,120,0.35)')),
        tickfont=dict(size=10, color='rgba(200,175,120,0.25)'),
        rangemode='tozero',
    )
    if player['metric'] == 'batting_average':
        y_axis['tickformat'] = '.3f'
        y_axis['range'] = [0, max(0.4, max(values) * 1.08 if values else 0.4)]

    fig.update_layout(
        **CHART_LAYOUT,
        height=640,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            title=dict(text='GAME', font=dict(size=10, color='rgba(200,175,120,0.35)')),
            tickfont=dict(size=10, color='rgba(200,175,120,0.25)'),
            dtick=20,
        ),
        yaxis=y_axis,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=10, family='Courier Prime, monospace', color='#6a6050'),
            bgcolor='rgba(0,0,0,0)',
            borderwidth=0,
        ),
        margin=dict(t=40, b=40, l=60, r=20),
    )
    return fig


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = f"{DEFAULT_YEAR} MLB Season Tracker"

app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,700;1,6..72,300;1,6..72,400&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #08080a;
            --bg-card: #0e0e12;
            --border: rgba(200,175,120,0.08);
            --gold: #c8af78;
            --gold-dim: rgba(200,175,120,0.3);
            --gold-faint: rgba(200,175,120,0.08);
            --text: #d0c8b8;
            --text-dim: #5a5548;
            --text-faint: #2a2825;
            --serif: 'Newsreader', Georgia, serif;
            --mono: 'Courier Prime', 'Courier New', monospace;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--mono);
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }
        body::before {
            content: '';
            position: fixed;
            inset: 0;
            z-index: 9999;
            pointer-events: none;
            opacity: 0.025;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        }
        .app-container {
            max-width: 1440px;
            margin: 0 auto;
            padding: 50px 40px 80px;
        }
        .page-nav {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 36px;
        }
        .nav-link, .mode-btn {
            font-family: var(--mono);
            font-size: 11px;
            letter-spacing: 0;
            text-transform: uppercase;
            padding: 8px 18px;
            background: transparent;
            color: var(--text-dim);
            border: 1px solid var(--border);
            cursor: pointer;
            text-decoration: none;
            transition: all 0.25s ease;
        }
        .nav-link:hover, .mode-btn:hover {
            color: var(--gold);
            border-color: var(--gold-dim);
        }
        .nav-link.active, .mode-btn.active {
            color: var(--gold);
            border-color: var(--gold);
            background: var(--gold-faint);
        }
        .header {
            margin-bottom: 52px;
            position: relative;
        }
        .header::after {
            content: '';
            display: block;
            width: 60px;
            height: 1px;
            background: var(--gold);
            margin-top: 30px;
            opacity: 0.4;
        }
        .eyebrow {
            font-family: var(--mono);
            font-size: 11px;
            letter-spacing: 0;
            text-transform: uppercase;
            color: var(--gold);
            opacity: 0.6;
            margin-bottom: 14px;
        }
        .title {
            font-family: var(--serif);
            font-size: 60px;
            font-weight: 300;
            line-height: 1.05;
            color: var(--text);
            letter-spacing: 0;
            margin-bottom: 16px;
        }
        .title em {
            font-style: italic;
            color: var(--gold);
        }
        .subtitle {
            font-family: var(--serif);
            font-size: 17px;
            font-weight: 300;
            line-height: 1.6;
            color: var(--text-dim);
            max-width: 640px;
            font-style: italic;
        }
        .controls-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .controls-bar .label {
            color: var(--text-dim);
            font-size: 10px;
            letter-spacing: 0;
            margin-right: 8px;
            text-transform: uppercase;
        }
        .season-select {
            min-width: 130px;
            font-size: 12px;
        }
        .season-select .Select-control,
        .season-select .Select-menu-outer,
        .season-select .Select-value,
        .season-select .Select-input,
        .season-select .Select-placeholder,
        .season-select .Select-menu {
            background: var(--bg-card) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
            font-family: var(--mono);
        }
        .season-select .Select-value-label,
        .season-select .Select-option {
            color: var(--text) !important;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 240px;
            gap: 40px;
            align-items: start;
            margin-top: 24px;
        }
        .chart-container {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 20px 10px 10px;
            position: relative;
        }
        .chart-container::before {
            content: 'WIN PERCENTAGE OVER THE SEASON';
            position: absolute;
            top: 8px;
            left: 20px;
            font-size: 9px;
            letter-spacing: 0;
            color: var(--text-dim);
            opacity: 0.4;
        }
        .player-chart-container::before {
            content: 'SEASON PROGRESSION';
        }
        .sidebar {
            position: sticky;
            top: 40px;
        }
        .sidebar-title {
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 0;
            text-transform: uppercase;
            color: var(--gold);
            opacity: 0.5;
            margin-bottom: 20px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }
        .division-block {
            margin-bottom: 20px;
        }
        .division-label {
            font-size: 9px;
            letter-spacing: 0;
            text-transform: uppercase;
            color: var(--text-dim);
            opacity: 0.5;
            margin-bottom: 6px;
        }
        .standing-row {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 3px 0;
            font-size: 12px;
            line-height: 1;
        }
        .standing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .standing-abbr {
            width: 30px;
            font-weight: 700;
            font-size: 11px;
            color: var(--text);
            opacity: 0.7;
        }
        .standing-record {
            flex: 1;
            color: var(--text-dim);
            font-size: 11px;
        }
        .standing-pct {
            color: var(--text-dim);
            font-size: 11px;
            width: 36px;
            text-align: right;
        }
        .standing-playoff {
            font-size: 8px;
            font-weight: 700;
            letter-spacing: 0;
            color: var(--gold);
            opacity: 0.7;
            width: 30px;
            text-align: right;
        }
        .footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 16px;
        }
        .footer-text {
            font-size: 10px;
            letter-spacing: 0;
            color: var(--text-dim);
            opacity: 0.4;
        }
        .js-plotly-plot .plotly .modebar { opacity: 0.3; }
        .js-plotly-plot .plotly .modebar:hover { opacity: 0.7; }
        @media (max-width: 1000px) {
            .main-grid { grid-template-columns: 1fr; }
            .sidebar { position: static; }
        }
        @media (max-width: 600px) {
            .app-container { padding: 24px 16px 40px; }
            .page-nav { margin-bottom: 28px; }
            .header { margin-bottom: 30px; }
            .title { font-size: 34px; margin-bottom: 10px; }
            .subtitle { font-size: 14px; }
            .controls-bar { gap: 4px; margin-bottom: 8px; }
            .controls-bar .label { font-size: 9px; margin-right: 4px; }
            .mode-btn, .nav-link { font-size: 9px; padding: 6px 10px; }
            .chart-container { padding: 10px 2px 2px; }
            .chart-container::before { font-size: 7px; top: 3px; left: 8px; }
            .footer { flex-direction: column; gap: 4px; }
            .footer-text { font-size: 9px; }
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''


def nav_links(active_path):
    links = [
        ('/', 'Team Tracker'),
        ('/pitcher-era', 'Pitcher ERA'),
        ('/batter-average', 'Batter AVG'),
    ]
    return html.Nav(className='page-nav', children=[
        dcc.Link(label, href=path, className='nav-link active' if path == active_path else 'nav-link')
        for path, label in links
    ])


def team_page():
    return html.Div(className='app-container', children=[
        nav_links('/'),
        dcc.Store(id='filter-mode', data='all'),
        dcc.Store(id='chart-style', data='smooth'),

        html.Div(className='header', children=[
            html.Div('MAJOR LEAGUE BASEBALL', className='eyebrow'),
            html.H1([html.Em(str(DEFAULT_YEAR)), ' Win Rates Over Time'], id='team-title', className='title'),
            html.P(
                f"Every team's win percentage, game by game across the full {DEFAULT_YEAR} season.",
                id='team-subtitle',
                className='subtitle',
            ),
        ]),

        html.Div(className='controls-bar', children=[
            html.Span('SEASON', className='label'),
            dcc.Dropdown(
                id='season-select',
                options=[{'label': str(year), 'value': year} for year in VALID_YEARS],
                value=DEFAULT_YEAR,
                clearable=False,
                searchable=False,
                className='season-select',
            ),
        ]),

        html.Div(className='controls-bar', style={'marginBottom': '12px'}, children=[
            html.Span('VIEW', className='label'),
            html.Button('SMOOTHED', id='btn-smooth', className='mode-btn active', n_clicks=0),
            html.Button('RAW', id='btn-raw', className='mode-btn', n_clicks=0),
            html.Button('BY DIVISION', id='btn-facet', className='mode-btn', n_clicks=0),
        ]),

        html.Div(className='controls-bar', children=[
            html.Span('FILTER', className='label'),
            html.Button('ALL TEAMS', id='btn-all', className='mode-btn active', n_clicks=0),
            html.Button('PLAYOFF TEAMS', id='btn-playoffs', className='mode-btn', n_clicks=0),
            html.Button('AL EAST', id='btn-ale', className='mode-btn', n_clicks=0),
            html.Button('AL CENTRAL', id='btn-alc', className='mode-btn', n_clicks=0),
            html.Button('AL WEST', id='btn-alw', className='mode-btn', n_clicks=0),
            html.Button('NL EAST', id='btn-nle', className='mode-btn', n_clicks=0),
            html.Button('NL CENTRAL', id='btn-nlc', className='mode-btn', n_clicks=0),
            html.Button('NL WEST', id='btn-nlw', className='mode-btn', n_clicks=0),
        ]),

        html.Div(className='main-grid', children=[
            html.Div(className='chart-container', children=[
                dcc.Graph(
                    id='main-chart',
                    config={
                        'displayModeBar': True,
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                        'responsive': True,
                    },
                ),
            ]),
            html.Div(id='standings-sidebar', className='sidebar', children=standings_sidebar(DEFAULT_YEAR)),
        ]),

        html.Div(className='footer', children=[
            html.Span('DATA: MLB STATS API CACHE', className='footer-text'),
            html.Span(
                f'{DEFAULT_YEAR} REGULAR SEASON',
                id='season-footer',
                className='footer-text',
            ),
        ]),
    ])


def player_page(player_key, pathname):
    cache = load_player_progressions()
    player = cache['players'][player_key]
    title_metric = 'ERA' if player['kind'] == 'pitcher' else 'Batting Average'
    subtitle = (
        f"{player['name']} game-by-game {title_metric.lower()} progression for "
        f"{', '.join(str(season) for season in cache['seasons'])}."
    )
    return html.Div(className='app-container', children=[
        nav_links(pathname),
        html.Div(className='header', children=[
            html.Div('PLAYER PROGRESSION', className='eyebrow'),
            html.H1([player['name'], html.Br(), html.Em(title_metric)], className='title'),
            html.P(subtitle, className='subtitle'),
        ]),
        html.Div(className='chart-container player-chart-container', children=[
            dcc.Graph(
                id='player-chart',
                figure=build_player_figure(player_key),
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'responsive': True,
                },
            ),
        ]),
        html.Div(className='footer', children=[
            html.Span('DATA: MLB STATS API CACHE', className='footer-text'),
            html.Span('2023-2025 REGULAR SEASONS', className='footer-text'),
        ]),
    ])


app.layout = html.Div([
    dcc.Location(id='url'),
    html.Div(id='page-content'),
])


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

DIVISION_BTN_MAP = {
    'btn-ale': 'AL East', 'btn-alc': 'AL Central', 'btn-alw': 'AL West',
    'btn-nle': 'NL East', 'btn-nlc': 'NL Central', 'btn-nlw': 'NL West',
}


@callback(Output('page-content', 'children'), Input('url', 'pathname'))
def route_page(pathname):
    if pathname in PLAYER_ROUTES:
        return player_page(PLAYER_ROUTES[pathname], pathname)
    return team_page()


@callback(
    Output('filter-mode', 'data'),
    Input('btn-all', 'n_clicks'),
    Input('btn-playoffs', 'n_clicks'),
    Input('btn-ale', 'n_clicks'),
    Input('btn-alc', 'n_clicks'),
    Input('btn-alw', 'n_clicks'),
    Input('btn-nle', 'n_clicks'),
    Input('btn-nlc', 'n_clicks'),
    Input('btn-nlw', 'n_clicks'),
    prevent_initial_call=True,
)
def update_filter(*args):
    from dash import ctx
    triggered_id = ctx.triggered_id
    if triggered_id == 'btn-playoffs':
        return 'playoffs'
    if triggered_id in DIVISION_BTN_MAP:
        return DIVISION_BTN_MAP[triggered_id]
    return 'all'


@callback(
    Output('chart-style', 'data'),
    Input('btn-smooth', 'n_clicks'),
    Input('btn-raw', 'n_clicks'),
    Input('btn-facet', 'n_clicks'),
    prevent_initial_call=True,
)
def update_style(*args):
    from dash import ctx
    return {'btn-smooth': 'smooth', 'btn-raw': 'raw', 'btn-facet': 'facet'}.get(
        ctx.triggered_id, 'smooth'
    )


@callback(
    Output('main-chart', 'figure'),
    Output('team-title', 'children'),
    Output('team-subtitle', 'children'),
    Output('standings-sidebar', 'children'),
    Output('season-footer', 'children'),
    Input('filter-mode', 'data'),
    Input('chart-style', 'data'),
    Input('season-select', 'value'),
)
def update_team_page(filter_mode, style, year):
    year = int(year or DEFAULT_YEAR)
    figure = build_team_figure(year, filter_mode or 'all', style or 'smooth')
    title = [html.Em(str(year)), ' Win Rates Over Time']
    subtitle = f"Every team's win percentage, game by game across the full {year} season."
    footer = f'{year} REGULAR SEASON'
    return figure, title, subtitle, standings_sidebar(year), footer


clientside_callback(
    """
    function(n1,n2,n3,n4,n5,n6,n7,n8) {
        const ctx = dash_clientside.callback_context;
        if (!ctx.triggered.length) return dash_clientside.no_update;
        const btnId = ctx.triggered[0].prop_id.split('.')[0];
        ['btn-all','btn-playoffs','btn-ale','btn-alc','btn-alw','btn-nle','btn-nlc','btn-nlw'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle('active', id === btnId);
        });
        return dash_clientside.no_update;
    }
    """,
    Output('btn-all', 'className'),
    Input('btn-all', 'n_clicks'), Input('btn-playoffs', 'n_clicks'),
    Input('btn-ale', 'n_clicks'), Input('btn-alc', 'n_clicks'),
    Input('btn-alw', 'n_clicks'), Input('btn-nle', 'n_clicks'),
    Input('btn-nlc', 'n_clicks'), Input('btn-nlw', 'n_clicks'),
    prevent_initial_call=True,
)


clientside_callback(
    """
    function(n1,n2,n3) {
        const ctx = dash_clientside.callback_context;
        if (!ctx.triggered.length) return dash_clientside.no_update;
        const btnId = ctx.triggered[0].prop_id.split('.')[0];
        ['btn-smooth','btn-raw','btn-facet'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.toggle('active', id === btnId);
        });
        return dash_clientside.no_update;
    }
    """,
    Output('btn-smooth', 'className'),
    Input('btn-smooth', 'n_clicks'), Input('btn-raw', 'n_clicks'),
    Input('btn-facet', 'n_clicks'),
    prevent_initial_call=True,
)


if __name__ == '__main__':
    app.run(debug=False, port=8050)
