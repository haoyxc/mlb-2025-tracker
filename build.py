"""
Build static HTML site from the Dash app's data and charts.
Run this locally or in GitHub Actions to generate docs/index.html,
then deploy to GitHub Pages from the docs/ folder.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import os
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Config (copied from app.py)
# ---------------------------------------------------------------------------

ALL_TEAMS = [
    'ARI','ATL','BAL','BOS','CHC','CHW','CIN','CLE','COL','DET',
    'HOU','KCR','LAA','LAD','MIA','MIL','MIN','NYM','NYY','OAK',
    'PHI','PIT','SDP','SEA','SFG','STL','TBR','TEX','TOR','WSN',
]

TEAM_META = {
    'ARI': {'name': 'Arizona Diamondbacks',    'abbr': 'ARI', 'color': '#A71930', 'div': 'NL West'},
    'ATL': {'name': 'Atlanta Braves',          'abbr': 'ATL', 'color': '#CE1141', 'div': 'NL East'},
    'BAL': {'name': 'Baltimore Orioles',       'abbr': 'BAL', 'color': '#DF4601', 'div': 'AL East'},
    'BOS': {'name': 'Boston Red Sox',          'abbr': 'BOS', 'color': '#BD3039', 'div': 'AL East'},
    'CHC': {'name': 'Chicago Cubs',            'abbr': 'CHC', 'color': '#0E3386', 'div': 'NL Central'},
    'CHW': {'name': 'Chicago White Sox',       'abbr': 'CHW', 'color': '#27251F', 'div': 'AL Central'},
    'CIN': {'name': 'Cincinnati Reds',         'abbr': 'CIN', 'color': '#C6011F', 'div': 'NL Central'},
    'CLE': {'name': 'Cleveland Guardians',     'abbr': 'CLE', 'color': '#00385D', 'div': 'AL Central'},
    'COL': {'name': 'Colorado Rockies',        'abbr': 'COL', 'color': '#333366', 'div': 'NL West'},
    'DET': {'name': 'Detroit Tigers',          'abbr': 'DET', 'color': '#0C2340', 'div': 'AL Central'},
    'HOU': {'name': 'Houston Astros',          'abbr': 'HOU', 'color': '#EB6E1F', 'div': 'AL West'},
    'KCR': {'name': 'Kansas City Royals',      'abbr': 'KCR', 'color': '#004687', 'div': 'AL Central'},
    'LAA': {'name': 'Los Angeles Angels',      'abbr': 'LAA', 'color': '#BA0021', 'div': 'AL West'},
    'LAD': {'name': 'Los Angeles Dodgers',     'abbr': 'LAD', 'color': '#005A9C', 'div': 'NL West'},
    'MIA': {'name': 'Miami Marlins',           'abbr': 'MIA', 'color': '#00A3E0', 'div': 'NL East'},
    'MIL': {'name': 'Milwaukee Brewers',       'abbr': 'MIL', 'color': '#FFC52F', 'div': 'NL Central'},
    'MIN': {'name': 'Minnesota Twins',         'abbr': 'MIN', 'color': '#002B5C', 'div': 'AL Central'},
    'NYM': {'name': 'New York Mets',           'abbr': 'NYM', 'color': '#002D72', 'div': 'NL East'},
    'NYY': {'name': 'New York Yankees',        'abbr': 'NYY', 'color': '#003087', 'div': 'AL East'},
    'OAK': {'name': 'Oakland Athletics',       'abbr': 'OAK', 'color': '#003831', 'div': 'AL West'},
    'PHI': {'name': 'Philadelphia Phillies',   'abbr': 'PHI', 'color': '#E81828', 'div': 'NL East'},
    'PIT': {'name': 'Pittsburgh Pirates',      'abbr': 'PIT', 'color': '#FDB827', 'div': 'NL Central'},
    'SDP': {'name': 'San Diego Padres',        'abbr': 'SDP', 'color': '#2F241D', 'div': 'NL West'},
    'SEA': {'name': 'Seattle Mariners',        'abbr': 'SEA', 'color': '#0C2C56', 'div': 'AL West'},
    'SFG': {'name': 'San Francisco Giants',    'abbr': 'SFG', 'color': '#FD5A1E', 'div': 'NL West'},
    'STL': {'name': 'St. Louis Cardinals',     'abbr': 'STL', 'color': '#C41E3A', 'div': 'NL Central'},
    'TBR': {'name': 'Tampa Bay Rays',          'abbr': 'TBR', 'color': '#092C5C', 'div': 'AL East'},
    'TEX': {'name': 'Texas Rangers',           'abbr': 'TEX', 'color': '#003278', 'div': 'AL West'},
    'TOR': {'name': 'Toronto Blue Jays',       'abbr': 'TOR', 'color': '#134A8E', 'div': 'AL East'},
    'WSN': {'name': 'Washington Nationals',    'abbr': 'WSN', 'color': '#AB0003', 'div': 'NL East'},
}

PLAYOFF_TEAMS_2025 = {
    'NYY', 'CLE', 'SEA', 'TOR', 'BOS', 'DET',
    'PHI', 'MIL', 'LAD', 'CHC', 'SDP', 'CIN',
}

DIVISIONS = ['AL East', 'AL Central', 'AL West', 'NL East', 'NL Central', 'NL West']

MLB_TEAM_IDS = {
    'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111, 'CHC': 112,
    'CHW': 145, 'CIN': 113, 'CLE': 114, 'COL': 115, 'DET': 116,
    'HOU': 117, 'KCR': 118, 'LAA': 108, 'LAD': 119, 'MIA': 146,
    'MIL': 158, 'MIN': 142, 'NYM': 121, 'NYY': 147, 'OAK': 133,
    'PHI': 143, 'PIT': 134, 'SDP': 135, 'SEA': 136, 'SFG': 137,
    'STL': 138, 'TBR': 139, 'TEX': 140, 'TOR': 141, 'WSN': 120,
}

SMOOTH_WINDOW = 15

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def brighten(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    if (r + g + b) < 120:
        r, g, b = min(255, r + 80), min(255, g + 80), min(255, b + 80)
    return f'#{r:02x}{g:02x}{b:02x}'

def load_season(year):
    all_data = {}
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
                    games.append({'date': de['date'], 'opp': opp_name, 'won': won,
                                  'wl': 'W' if won else 'L'})
            if not games:
                continue
            df = pd.DataFrame(games)
            df['game_num'] = range(1, len(df) + 1)
            df['is_win'] = df['won'].astype(int)
            df['cum_wins'] = df['is_win'].cumsum()
            df['cum_losses'] = df['game_num'] - df['cum_wins']
            df['win_pct'] = (df['cum_wins'] / df['game_num']) * 100
            df['win_pct_smooth'] = df['win_pct'].rolling(SMOOTH_WINDOW, min_periods=1, center=False).mean()
            df['team'] = team
            all_data[team] = df
            w, l = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])
            print(f"  {team}: {len(df)}g ({w}-{l})")
        except Exception as e:
            print(f"  {team}: SKIP - {e}")
    return all_data


def make_hover(meta, df):
    return [
        f"{meta['name']}<br>Game {g}  |  {wp:.1f}%<br>{int(cw)}W  {int(cl)}L<br>{d}<br>vs {opp}  {wl}"
        for g, wp, cw, cl, d, opp, wl in zip(
            df['game_num'], df['win_pct'], df['cum_wins'],
            df['cum_losses'], df['date'], df['opp'], df['wl'])
    ]


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

CHART_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family='Courier Prime, monospace', color='#8a8070'),
    hovermode='closest', dragmode='zoom',
)

def base_axes():
    return dict(
        xaxis=dict(range=[0, 165], showgrid=False, zeroline=False,
                   title=dict(text='GAME', font=dict(size=10, color='rgba(200,175,120,0.3)')),
                   tickfont=dict(size=10, color='rgba(200,175,120,0.25)'), dtick=40),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor='rgba(200,175,120,0.04)',
                   zeroline=False, title=dict(text='WIN %', font=dict(size=10, color='rgba(200,175,120,0.3)')),
                   ticksuffix='%', tickfont=dict(size=10, color='rgba(200,175,120,0.25)'), dtick=10),
    )

def build_combined(season_data, selected_teams, mode, smooth=False):
    fig = go.Figure()
    fig.add_shape(type='line', x0=1, x1=165, y0=50, y1=50,
                  line=dict(color='rgba(200,175,120,0.15)', width=1, dash='dot'))
    fig.add_annotation(x=166, y=50, text='.500', showarrow=False, xanchor='left',
                       font=dict(color='rgba(200,175,120,0.3)', size=11, family='Courier Prime, monospace'))
    y_col = 'win_pct_smooth' if smooth else 'win_pct'
    for team in selected_teams:
        if team not in season_data:
            continue
        df = season_data[team]
        meta = TEAM_META[team]
        is_playoff = team in PLAYOFF_TEAMS_2025
        fw, fl = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])
        dimmed = mode == 'playoffs' and not is_playoff
        if dimmed:
            opacity, width = 0.08, 1
        elif mode == 'playoffs' and is_playoff:
            opacity, width = 1.0, 2.5
        elif mode == 'division':
            opacity, width = 0.9, 2.2
        else:
            opacity, width = 0.7, 1.8
        tc = brighten(meta['color'])
        suffix = '  POST' if is_playoff else ''
        label = f'{meta["abbr"]}  {fw}-{fl}{suffix}'
        if smooth:
            fig.add_trace(go.Scatter(x=df['game_num'].values, y=df['win_pct'].values,
                name=label, mode='lines', showlegend=False,
                line=dict(color=tc, width=0.5), opacity=opacity*0.2, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df['game_num'].values, y=df[y_col].values,
            name=label, mode='lines',
            line=dict(color=tc, width=width+(0.5 if smooth else 0)), opacity=opacity,
            text=make_hover(meta, df) if not dimmed else None,
            hoverinfo='text' if not dimmed else 'skip', showlegend=not dimmed))
    fig.update_layout(**CHART_LAYOUT, height=680, **base_axes(),
        legend=dict(font=dict(size=10, family='Courier Prime, monospace', color='#6a6050'),
                    bgcolor='rgba(0,0,0,0)', borderwidth=0, itemsizing='constant', tracegroupgap=2),
        margin=dict(t=10, b=40, l=60, r=20))
    return fig

def build_faceted(season_data, available_teams):
    fig = make_subplots(rows=2, cols=3, subplot_titles=DIVISIONS,
                        horizontal_spacing=0.06, vertical_spacing=0.10)
    for idx, div in enumerate(DIVISIONS):
        row, col = (idx // 3) + 1, (idx % 3) + 1
        div_teams = sorted([t for t in available_teams if TEAM_META[t]['div'] == div],
                           key=lambda t: season_data[t]['win_pct'].iloc[-1], reverse=True)
        fig.add_shape(type='line', x0=1, x1=165, y0=50, y1=50,
                      line=dict(color='rgba(200,175,120,0.12)', width=1, dash='dot'), row=row, col=col)
        for team in div_teams:
            df = season_data[team]
            meta = TEAM_META[team]
            is_playoff = team in PLAYOFF_TEAMS_2025
            fw, fl = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])
            tc = brighten(meta['color'])
            fig.add_trace(go.Scatter(x=df['game_num'].values, y=df['win_pct'].values,
                mode='lines', showlegend=False, line=dict(color=tc, width=0.5),
                opacity=0.15, hoverinfo='skip'), row=row, col=col)
            fig.add_trace(go.Scatter(x=df['game_num'].values, y=df['win_pct_smooth'].values,
                name=f'{meta["abbr"]} {fw}-{fl}{"  *" if is_playoff else ""}',
                mode='lines', line=dict(color=tc, width=2.5),
                opacity=0.95 if is_playoff else 0.7,
                text=make_hover(meta, df), hoverinfo='text', legendgroup=div),
                row=row, col=col)
            fig.add_annotation(x=162, y=df['win_pct_smooth'].iloc[-1], text=f' {meta["abbr"]}',
                showarrow=False, xanchor='left',
                font=dict(size=9, color=tc, family='Courier Prime, monospace'),
                opacity=0.8, row=row, col=col)
    fig.update_layout(**CHART_LAYOUT, height=700, showlegend=False, margin=dict(t=40, b=30, l=50, r=40))
    for i in range(1, 7):
        xk = f'xaxis{i}' if i > 1 else 'xaxis'
        yk = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{
            xk: dict(range=[0, 170], showgrid=False, zeroline=False,
                     tickfont=dict(size=9, color='rgba(200,175,120,0.2)'), dtick=40),
            yk: dict(range=[0, 100], showgrid=True, gridcolor='rgba(200,175,120,0.04)',
                     zeroline=False, ticksuffix='%', tickfont=dict(size=9, color='rgba(200,175,120,0.2)'), dtick=10),
        })
    for ann in fig.layout.annotations:
        ann.font = dict(size=11, color='rgba(200,175,120,0.5)', family='Courier Prime, monospace')
    return fig


# ---------------------------------------------------------------------------
# Build standings HTML
# ---------------------------------------------------------------------------

def standings_html(season_data):
    standings = []
    for team, df in season_data.items():
        w, l = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])
        standings.append({'team': team, 'w': w, 'l': l, 'pct': w/(w+l),
                          'div': TEAM_META[team]['div'], 'color': TEAM_META[team]['color'],
                          'playoff': team in PLAYOFF_TEAMS_2025})

    html = '<div class="standings-grid">'
    for div in DIVISIONS:
        div_teams = sorted([s for s in standings if s['div'] == div], key=lambda x: x['pct'], reverse=True)
        html += f'<div class="division-block"><div class="division-label">{div}</div>'
        for s in div_teams:
            post = '<span class="standing-playoff">POST</span>' if s['playoff'] else ''
            html += (f'<div class="standing-row">'
                     f'<span class="standing-dot" style="background:{s["color"]}"></span>'
                     f'<span class="standing-abbr">{s["team"]}</span>'
                     f'<span class="standing-record">{s["w"]}-{s["l"]}</span>'
                     f'<span class="standing-pct">.{int(s["pct"]*1000):03d}</span>'
                     f'{post}</div>')
        html += '</div>'
    html += '</div>'
    return html


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

print("Loading 2025 season data...")
season_data = load_season(2025)
available = [t for t in ALL_TEAMS if t in season_data]
print(f"Loaded {len(season_data)} teams.\n")

print("Building charts...")
charts = {}
for smooth in [False, True]:
    tag = 'smooth' if smooth else 'raw'
    charts[f'{tag}_all'] = build_combined(season_data, available, 'all', smooth)
    charts[f'{tag}_playoffs'] = build_combined(season_data, available, 'playoffs', smooth)
    for div in DIVISIONS:
        div_teams = [t for t in available if TEAM_META[t]['div'] == div]
        key = div.lower().replace(' ', '_')
        charts[f'{tag}_{key}'] = build_combined(season_data, div_teams, 'division', smooth)
charts['facet'] = build_faceted(season_data, available)

# Convert charts to JSON
chart_json = {}
for key, fig in charts.items():
    chart_json[key] = fig.to_json()

print(f"Built {len(charts)} charts.\n")

# Build HTML
os.makedirs('docs', exist_ok=True)

standings = standings_html(season_data)

html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2025 MLB Season Tracker</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,700;1,6..72,300;1,6..72,400&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
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
        }
        body::before {
            content: ''; position: fixed; inset: 0; z-index: 9999;
            pointer-events: none; opacity: 0.025;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
        }
        .container { max-width: 1440px; margin: 0 auto; padding: 50px 40px 80px; overflow-x: hidden; }
        .header { margin-bottom: 60px; }
        .header::after { content: ''; display: block; width: 60px; height: 1px; background: var(--gold); margin-top: 30px; opacity: 0.4; }
        .eyebrow { font-size: 11px; letter-spacing: 4px; text-transform: uppercase; color: var(--gold); opacity: 0.6; margin-bottom: 14px; }
        .title { font-family: var(--serif); font-size: clamp(36px,5vw,64px); font-weight: 300; line-height: 1.05; color: var(--text); letter-spacing: -0.5px; margin-bottom: 16px; }
        .title em { font-style: italic; color: var(--gold); }
        .subtitle { font-family: var(--serif); font-size: 17px; font-weight: 300; line-height: 1.6; color: var(--text-dim); max-width: 600px; font-style: italic; }
        .controls-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
        .controls-bar .label { color: var(--text-dim); font-size: 10px; letter-spacing: 2px; margin-right: 8px; }
        .mode-btn {
            font-family: var(--mono); font-size: 11px; letter-spacing: 1.5px;
            text-transform: uppercase; padding: 8px 18px; background: transparent;
            color: var(--text-dim); border: 1px solid var(--border); cursor: pointer;
            transition: all 0.25s ease;
        }
        .mode-btn:hover { color: var(--gold); border-color: var(--gold-dim); }
        .mode-btn.active { color: var(--gold); border-color: var(--gold); background: var(--gold-faint); }
        .main-grid { display: grid; grid-template-columns: 1fr 240px; gap: 40px; align-items: start; margin-top: 24px; }
        @media (max-width: 1000px) {
            .main-grid { grid-template-columns: 1fr; }
            .sidebar { position: static; }
        }
        @media (max-width: 600px) {
            .container { padding: 24px 16px 40px; }
            .header { margin-bottom: 30px; }
            .eyebrow { font-size: 9px; letter-spacing: 3px; margin-bottom: 10px; }
            .title { font-size: 28px; margin-bottom: 10px; }
            .subtitle { font-size: 14px; }
            .controls-bar { gap: 4px; margin-bottom: 8px; }
            .controls-bar .label { font-size: 8px; margin-right: 4px; }
            .mode-btn { font-size: 9px; padding: 6px 10px; letter-spacing: 1px; }
            .chart-container { padding: 10px 2px 2px; }
            .chart-container::before { font-size: 7px; letter-spacing: 2px; top: 3px; left: 8px; }
            .standings-grid { grid-template-columns: 1fr 1fr; gap: 0 16px; }
            .division-block { margin-bottom: 12px; }
            .footer { flex-direction: column; gap: 4px; }
            .footer-text { font-size: 9px; }
        }
        @media (min-width: 601px) and (max-width: 1000px) {
            .standings-grid { grid-template-columns: 1fr 1fr 1fr; gap: 0 24px; }
        }
        .chart-container {
            background: var(--bg-card); border: 1px solid var(--border);
            padding: 20px 10px 10px; position: relative;
        }
        .chart-container::before {
            content: 'WIN PERCENTAGE OVER THE SEASON'; position: absolute; top: 8px; left: 20px;
            font-size: 9px; letter-spacing: 3px; color: var(--text-dim); opacity: 0.4;
        }
        .sidebar { position: sticky; top: 40px; }
        .sidebar-title { font-size: 10px; letter-spacing: 3px; text-transform: uppercase; color: var(--gold); opacity: 0.5; margin-bottom: 20px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
        .standings-grid { display: grid; grid-template-columns: 1fr; gap: 0 20px; }
        .division-block { margin-bottom: 20px; }
        .division-label { font-size: 9px; letter-spacing: 2.5px; text-transform: uppercase; color: var(--text-dim); opacity: 0.5; margin-bottom: 6px; }
        .standing-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 12px; line-height: 1; }
        .standing-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
        .standing-abbr { width: 30px; font-weight: 700; font-size: 11px; color: var(--text); opacity: 0.7; }
        .standing-record { flex: 1; color: var(--text-dim); font-size: 11px; }
        .standing-pct { color: var(--text-dim); font-size: 11px; width: 36px; text-align: right; }
        .standing-playoff { font-size: 8px; font-weight: 700; letter-spacing: 1.5px; color: var(--gold); opacity: 0.7; width: 30px; text-align: right; margin-left: 4px; }
        .footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; }
        .footer-text { font-size: 10px; letter-spacing: 1px; color: var(--text-dim); opacity: 0.4; }
        .js-plotly-plot .plotly .modebar { opacity: 0.3; }
        .js-plotly-plot .plotly .modebar:hover { opacity: 0.7; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .header { animation: fadeUp 0.8s ease both; }
        .controls-bar { animation: fadeUp 0.8s ease 0.1s both; }
        .chart-container { animation: fadeUp 0.8s ease 0.2s both; }
        .sidebar { animation: fadeUp 0.8s ease 0.3s both; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="eyebrow">MAJOR LEAGUE BASEBALL</div>
        <h1 class="title"><em>2025</em> Season</h1>
        <p class="subtitle">Every team's win percentage, game by game across the full 162-game season.</p>
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
        <button class="mode-btn" data-filter="al_east" onclick="setFilter(this)">AL EAST</button>
        <button class="mode-btn" data-filter="al_central" onclick="setFilter(this)">AL CENTRAL</button>
        <button class="mode-btn" data-filter="al_west" onclick="setFilter(this)">AL WEST</button>
        <button class="mode-btn" data-filter="nl_east" onclick="setFilter(this)">NL EAST</button>
        <button class="mode-btn" data-filter="nl_central" onclick="setFilter(this)">NL CENTRAL</button>
        <button class="mode-btn" data-filter="nl_west" onclick="setFilter(this)">NL WEST</button>
    </div>

    <div class="main-grid">
        <div class="chart-container">
            <div id="chart"></div>
        </div>
        <div class="sidebar">
            <div class="sidebar-title">FINAL STANDINGS</div>
            STANDINGS_PLACEHOLDER
        </div>
    </div>

    <div class="footer">
        <span class="footer-text">DATA: MLB STATS API</span>
        <span class="footer-text">2025 REGULAR SEASON / 162 GAMES</span>
    </div>
</div>

<script>
const CHARTS = CHARTS_PLACEHOLDER;

let currentView = 'smooth';
let currentFilter = 'all';

function getChartKey() {
    if (currentView === 'facet') return 'facet';
    return currentView + '_' + currentFilter;
}

function renderChart() {
    const key = getChartKey();
    const spec = JSON.parse(CHARTS[key]);
    const isMobile = window.innerWidth < 600;
    if (isMobile) {
        spec.layout.height = 400;
        spec.layout.margin = {t: 10, b: 30, l: 40, r: 10};
        spec.layout.legend = {font: {size: 8}, x: 0, y: 1};
        if (spec.layout.yaxis) spec.layout.yaxis.title = null;
        if (spec.layout.xaxis) spec.layout.xaxis.title = null;
    }
    Plotly.react('chart', spec.data, spec.layout, {displayModeBar: !isMobile, responsive: true, modeBarButtonsToRemove: ['lasso2d','select2d']});
}

function setView(btn) {
    document.querySelectorAll('[data-view]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentView = btn.dataset.view;
    document.getElementById('filter-bar').style.display = currentView === 'facet' ? 'none' : 'flex';
    renderChart();
}

function setFilter(btn) {
    document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderChart();
}

renderChart();
window.addEventListener('resize', () => { clearTimeout(window._rz); window._rz = setTimeout(renderChart, 200); });
</script>
</body>
</html>'''

html_out = html_template.replace('CHARTS_PLACEHOLDER', json.dumps(chart_json))
html_out = html_out.replace('STANDINGS_PLACEHOLDER', standings)

with open('docs/index.html', 'w') as f:
    f.write(html_out)

print(f"Built docs/index.html ({len(html_out)//1024} KB)")
print("Done!")
