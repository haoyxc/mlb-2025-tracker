import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from dash import Dash, html, dcc, callback, Output, Input, clientside_callback
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Config
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
    'NYY', 'CLE', 'SEA', 'TOR', 'BOS', 'DET',   # AL
    'PHI', 'MIL', 'LAD', 'CHC', 'SDP', 'CIN',    # NL
}

DIVISIONS = ['AL East', 'AL Central', 'AL West', 'NL East', 'NL Central', 'NL West']

# MLB Stats API team IDs
MLB_TEAM_IDS = {
    'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111, 'CHC': 112,
    'CHW': 145, 'CIN': 113, 'CLE': 114, 'COL': 115, 'DET': 116,
    'HOU': 117, 'KCR': 118, 'LAA': 108, 'LAD': 119, 'MIA': 146,
    'MIL': 158, 'MIN': 142, 'NYM': 121, 'NYY': 147, 'OAK': 133,
    'PHI': 143, 'PIT': 134, 'SDP': 135, 'SEA': 136, 'SFG': 137,
    'STL': 138, 'TBR': 139, 'TEX': 140, 'TOR': 141, 'WSN': 120,
}

# ---------------------------------------------------------------------------
# Data loading (MLB Stats API - full 162 games, correct results)
# ---------------------------------------------------------------------------

def load_season_mlb(year):
    """Load game-by-game data for all teams from the MLB Stats API."""
    all_data = {}
    for team, team_id in MLB_TEAM_IDS.items():
        try:
            r = requests.get(
                "https://statsapi.mlb.com/api/v1/schedule",
                params={
                    "sportId": 1, "teamId": team_id, "season": year,
                    "gameType": "R", "startDate": f"{year}-03-01",
                    "endDate": f"{year}-10-15",
                },
                timeout=20,
            )
            data = r.json()

            games = []
            seen_pks = set()
            for date_entry in data.get('dates', []):
                for game in date_entry['games']:
                    status = game['status']['detailedState']
                    if status not in ('Final', 'Completed Early'):
                        continue
                    # Deduplicate by gamePk (rescheduled games appear twice)
                    pk = game['gamePk']
                    if pk in seen_pks:
                        continue
                    seen_pks.add(pk)

                    away = game['teams']['away']
                    home = game['teams']['home']
                    is_home = home['team']['id'] == team_id
                    if is_home:
                        won = home.get('isWinner', False)
                        opp_name = away['team']['name']
                        our_r, opp_r = home.get('score', 0), away.get('score', 0)
                    else:
                        won = away.get('isWinner', False)
                        opp_name = home['team']['name']
                        our_r, opp_r = away.get('score', 0), home.get('score', 0)

                    games.append({
                        'date': date_entry['date'],
                        'opp': opp_name,
                        'home': is_home,
                        'won': won,
                        'R': our_r, 'RA': opp_r,
                        'wl': 'W' if won else 'L',
                    })

            if not games:
                print(f"  {team}: no games found")
                continue

            df = pd.DataFrame(games)
            df['game_num'] = range(1, len(df) + 1)
            df['is_win'] = df['won'].astype(int)
            df['cum_wins'] = df['is_win'].cumsum()
            df['cum_losses'] = df['game_num'] - df['cum_wins']
            df['win_pct'] = (df['cum_wins'] / df['game_num']) * 100
            df['team'] = team
            # Build W-L string
            df['W-L'] = df['cum_wins'].astype(str) + '-' + df['cum_losses'].astype(str)
            # Opp abbreviation (short name)
            df['Opp'] = df['opp']
            df['Date'] = df['date']
            df['W/L'] = df['wl']

            all_data[team] = df
            w = int(df['cum_wins'].iloc[-1])
            l = int(df['cum_losses'].iloc[-1])
            print(f"  {team}: {len(df)}g ({w}-{l})")
        except Exception as e:
            print(f"  {team}: SKIP - {str(e)[:80]}")
    return all_data


print("Loading 2025 season data from MLB Stats API...")
season_data = load_season_mlb(2025)
print(f"Loaded {len(season_data)}/30 teams.\n")

# Precompute final standings for the sidebar
standings = []
for team, df in season_data.items():
    w = int(df['cum_wins'].iloc[-1])
    l = int(df['cum_losses'].iloc[-1])
    standings.append({
        'team': team,
        'name': TEAM_META[team]['name'],
        'color': TEAM_META[team]['color'],
        'div': TEAM_META[team]['div'],
        'w': w, 'l': l,
        'pct': w / (w + l),
        'playoff': team in PLAYOFF_TEAMS_2025,
    })
standings.sort(key=lambda x: x['pct'], reverse=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SMOOTH_WINDOW = 15  # rolling average window

def brighten(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    if (r + g + b) < 120:
        r, g, b = min(255, r + 80), min(255, g + 80), min(255, b + 80)
    return f'#{r:02x}{g:02x}{b:02x}'

def add_reference_lines(fig):
    fig.add_shape(type='line', x0=1, x1=165, y0=50, y1=50,
                  line=dict(color='rgba(200,175,120,0.15)', width=1, dash='dot'))
    fig.add_annotation(x=166, y=50, text='.500', showarrow=False, xanchor='left',
                       font=dict(color='rgba(200,175,120,0.3)', size=11,
                                 family='Courier Prime, monospace'))

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
        f"Game {g}  |  {wp:.1f}%<br>"
        f"{int(cw)}W  {int(cl)}L<br>"
        f"{d}<br>"
        f"vs {opp}  {wl}"
        for g, wp, cw, cl, d, opp, wl in zip(
            df['game_num'], df['win_pct'], df['cum_wins'],
            df['cum_losses'], df['Date'], df['Opp'], df['W/L']
        )
    ]

# Precompute smoothed win_pct for each team
for team, df in season_data.items():
    df['win_pct_smooth'] = df['win_pct'].rolling(SMOOTH_WINDOW, min_periods=1, center=False).mean()


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_combined(selected_teams, mode, smooth=False):
    """Single chart with all selected teams overlaid."""
    fig = go.Figure()
    add_reference_lines(fig)

    y_col = 'win_pct_smooth' if smooth else 'win_pct'

    for team in selected_teams:
        if team not in season_data:
            continue
        df = season_data[team]
        meta = TEAM_META[team]
        is_playoff = team in PLAYOFF_TEAMS_2025
        final_w, final_l = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])

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
        label = f'{meta["abbr"]}  {final_w}-{final_l}{suffix}'

        # Raw line (faint) when smoothing is on
        if smooth:
            fig.add_trace(go.Scatter(
                x=df['game_num'].values, y=df['win_pct'].values,
                name=label, mode='lines', showlegend=False,
                line=dict(color=team_color, width=0.5),
                opacity=opacity * 0.2,
                hoverinfo='skip',
            ))

        fig.add_trace(go.Scatter(
            x=df['game_num'].values, y=df[y_col].values,
            name=label, mode='lines',
            line=dict(color=team_color, width=width + (0.5 if smooth else 0)),
            opacity=opacity,
            text=make_hover_text(meta, df) if not dimmed else None,
            hoverinfo='text' if not dimmed else 'skip',
            showlegend=not dimmed,
        ))

    fig.update_layout(
        **CHART_LAYOUT, height=680,
        **axis_style(),
        legend=dict(font=dict(size=10, family='Courier Prime, monospace', color='#6a6050'),
                    bgcolor='rgba(0,0,0,0)', borderwidth=0, itemsizing='constant', tracegroupgap=2),
        margin=dict(t=10, b=40, l=60, r=20),
    )
    return fig


from plotly.subplots import make_subplots

def build_faceted():
    """Small multiples: one subplot per division."""
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[d for d in DIVISIONS],
        horizontal_spacing=0.06, vertical_spacing=0.10,
    )

    for idx, div in enumerate(DIVISIONS):
        row, col = (idx // 3) + 1, (idx % 3) + 1
        div_teams = sorted(
            [t for t in available_teams if TEAM_META[t]['div'] == div],
            key=lambda t: season_data[t]['win_pct'].iloc[-1], reverse=True
        )

        # .500 line per subplot
        fig.add_shape(type='line', x0=1, x1=165, y0=50, y1=50,
                      line=dict(color='rgba(200,175,120,0.12)', width=1, dash='dot'),
                      row=row, col=col)

        for team in div_teams:
            df = season_data[team]
            meta = TEAM_META[team]
            is_playoff = team in PLAYOFF_TEAMS_2025
            final_w, final_l = int(df['cum_wins'].iloc[-1]), int(df['cum_losses'].iloc[-1])
            team_color = brighten(meta['color'])
            suffix = ' *' if is_playoff else ''
            label = f'{meta["abbr"]} {final_w}-{final_l}{suffix}'

            # Faint raw line
            fig.add_trace(go.Scatter(
                x=df['game_num'].values, y=df['win_pct'].values,
                mode='lines', showlegend=False,
                line=dict(color=team_color, width=0.5), opacity=0.15,
                hoverinfo='skip',
            ), row=row, col=col)

            # Smooth trend
            fig.add_trace(go.Scatter(
                x=df['game_num'].values, y=df['win_pct_smooth'].values,
                name=label, mode='lines',
                line=dict(color=team_color, width=2.5),
                opacity=0.95 if is_playoff else 0.7,
                text=make_hover_text(meta, df),
                hoverinfo='text',
                legendgroup=div,
            ), row=row, col=col)

            # End-of-season label
            fig.add_annotation(
                x=161, y=df['win_pct_smooth'].iloc[-1],
                text=f' {meta["abbr"]}',
                showarrow=False, xanchor='left',
                font=dict(size=9, color=team_color, family='Courier Prime, monospace'),
                opacity=0.8,
                row=row, col=col,
            )

    fig.update_layout(
        **CHART_LAYOUT, height=700, showlegend=False,
        margin=dict(t=40, b=30, l=50, r=40),
    )

    # Style all subplots
    for i in range(1, 7):
        xkey = f'xaxis{i}' if i > 1 else 'xaxis'
        ykey = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{
            xkey: dict(range=[0, 170], showgrid=False, zeroline=False,
                       tickfont=dict(size=9, color='rgba(200,175,120,0.2)'), dtick=40),
            ykey: dict(range=[0, 100], showgrid=True,
                       gridcolor='rgba(200,175,120,0.04)', zeroline=False,
                       ticksuffix='%', tickfont=dict(size=9, color='rgba(200,175,120,0.2)'),
                       dtick=10),
        })

    # Style subplot titles
    for ann in fig.layout.annotations:
        ann.font = dict(size=11, color='rgba(200,175,120,0.5)',
                        family='Courier Prime, monospace')

    return fig


# Precompute all figures at startup for instant filtering
print("Precomputing charts...")
available_teams = [t for t in ALL_TEAMS if t in season_data]
PRECOMPUTED = {}
for smooth in [False, True]:
    tag = 'smooth' if smooth else 'raw'
    PRECOMPUTED[(tag, 'all')] = build_combined(available_teams, 'all', smooth)
    PRECOMPUTED[(tag, 'playoffs')] = build_combined(available_teams, 'playoffs', smooth)
    for div in DIVISIONS:
        div_teams = [t for t in available_teams if TEAM_META[t]['div'] == div]
        PRECOMPUTED[(tag, div)] = build_combined(div_teams, 'division', smooth)
PRECOMPUTED[('facet', 'all')] = build_faceted()
print("Charts precomputed.\n")


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Expose for gunicorn
app.title = "2025 MLB Season Tracker"

# Build team pill buttons
def team_pill(team):
    meta = TEAM_META[team]
    is_playoff = team in PLAYOFF_TEAMS_2025
    if team not in season_data:
        return None
    df = season_data[team]
    w = int(df['cum_wins'].iloc[-1])
    l = int(df['cum_losses'].iloc[-1])
    return html.Button(
        id={'type': 'team-pill', 'team': team},
        children=[
            html.Span(meta['abbr'], style={'fontWeight': '700', 'letterSpacing': '0.5px'}),
            html.Span(f' {w}-{l}', style={'opacity': '0.5', 'fontSize': '11px', 'marginLeft': '3px'}),
            html.Span(' P', style={
                'color': '#c8af78', 'fontSize': '9px', 'marginLeft': '4px',
                'fontWeight': '800', 'letterSpacing': '1px',
            }) if is_playoff else None,
        ],
        className='team-pill active',
        n_clicks=0,
    )


# Division groups for sidebar
def division_block(div_name):
    teams_in_div = sorted(
        [s for s in standings if s['div'] == div_name],
        key=lambda x: x['pct'], reverse=True
    )
    return html.Div(className='division-block', children=[
        html.Div(div_name, className='division-label'),
        *[html.Div(className='standing-row', children=[
            html.Span(className='standing-dot',
                      style={'backgroundColor': s['color']}),
            html.Span(s['team'], className='standing-abbr'),
            html.Span(f'{s["w"]}-{s["l"]}', className='standing-record'),
            html.Span(f'.{int(s["pct"]*1000):03d}', className='standing-pct'),
            html.Span('POST', className='standing-playoff') if s['playoff'] else None,
        ]) for s in teams_in_div],
    ])

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
            --bg:        #08080a;
            --bg-card:   #0e0e12;
            --border:    rgba(200,175,120,0.08);
            --gold:      #c8af78;
            --gold-dim:  rgba(200,175,120,0.3);
            --gold-faint:rgba(200,175,120,0.08);
            --text:      #d0c8b8;
            --text-dim:  #5a5548;
            --text-faint:#2a2825;
            --serif:     'Newsreader', Georgia, serif;
            --mono:      'Courier Prime', 'Courier New', monospace;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--mono);
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }

        /* Grain overlay */
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

        /* --- Header --- */
        .header {
            margin-bottom: 60px;
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
            letter-spacing: 4px;
            text-transform: uppercase;
            color: var(--gold);
            opacity: 0.6;
            margin-bottom: 14px;
        }
        .title {
            font-family: var(--serif);
            font-size: clamp(36px, 5vw, 64px);
            font-weight: 300;
            line-height: 1.05;
            color: var(--text);
            letter-spacing: -0.5px;
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
            max-width: 600px;
            font-style: italic;
        }

        /* --- Controls --- */
        .controls-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        .mode-btn {
            font-family: var(--mono);
            font-size: 11px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 8px 18px;
            background: transparent;
            color: var(--text-dim);
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .mode-btn:hover {
            color: var(--gold);
            border-color: var(--gold-dim);
        }
        .mode-btn.active {
            color: var(--gold);
            border-color: var(--gold);
            background: var(--gold-faint);
        }

        /* --- Main layout --- */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 240px;
            gap: 40px;
            align-items: start;
        }
        @media (max-width: 1000px) {
            .main-grid { grid-template-columns: 1fr; }
        }

        /* --- Chart area --- */
        .chart-container {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 20px 10px 10px 10px;
            position: relative;
        }
        .chart-container::before {
            content: 'WIN PERCENTAGE OVER THE SEASON';
            position: absolute;
            top: 8px;
            left: 20px;
            font-size: 9px;
            letter-spacing: 3px;
            color: var(--text-dim);
            opacity: 0.4;
        }

        /* --- Sidebar --- */
        .sidebar {
            position: sticky;
            top: 40px;
        }
        .sidebar-title {
            font-family: var(--mono);
            font-size: 10px;
            letter-spacing: 3px;
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
            letter-spacing: 2.5px;
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
            letter-spacing: 1.5px;
            color: var(--gold);
            opacity: 0.7;
            width: 30px;
            text-align: right;
        }

        /* --- Team pills --- */
        .pill-section {
            margin-bottom: 30px;
        }
        .pill-label {
            font-size: 9px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            color: var(--text-dim);
            opacity: 0.5;
            margin-bottom: 10px;
        }
        .pill-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        .team-pill {
            font-family: var(--mono);
            font-size: 11px;
            padding: 5px 10px;
            background: transparent;
            color: var(--text-dim);
            border: 1px solid var(--text-faint);
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .team-pill:hover {
            color: var(--text);
            border-color: var(--gold-dim);
        }
        .team-pill.active {
            color: var(--text);
            border-color: var(--border);
            background: rgba(200,175,120,0.03);
        }
        .team-pill.active:hover {
            border-color: var(--gold-dim);
        }

        /* --- Footer --- */
        .footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }
        .footer-text {
            font-size: 10px;
            letter-spacing: 1px;
            color: var(--text-dim);
            opacity: 0.4;
        }

        /* --- Plotly overrides --- */
        .js-plotly-plot .plotly .modebar { opacity: 0.3; }
        .js-plotly-plot .plotly .modebar:hover { opacity: 0.7; }

        /* --- Dash dropdown override --- */
        .Select-control, .Select-menu-outer { background: var(--bg-card) !important; }

        /* --- Fade in --- */
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(20px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .header      { animation: fadeUp 0.8s ease both; }
        .controls-bar{ animation: fadeUp 0.8s ease 0.1s both; }
        .pill-section{ animation: fadeUp 0.8s ease 0.15s both; }
        .chart-container { animation: fadeUp 0.8s ease 0.25s both; }
        .sidebar     { animation: fadeUp 0.8s ease 0.35s both; }
        .footer      { animation: fadeUp 0.8s ease 0.45s both; }
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

app.layout = html.Div(className='app-container', children=[

    # Hidden stores
    dcc.Store(id='filter-mode', data='all'),
    dcc.Store(id='chart-style', data='smooth'),  # 'raw', 'smooth', 'facet'

    # Header
    html.Div(className='header', children=[
        html.Div('MAJOR LEAGUE BASEBALL', className='eyebrow'),
        html.H1(['The Arc of a ', html.Em('Season')], className='title'),
        html.P(
            'Every team\'s win percentage, game by game across the 2025 season. '
            'Watch contenders separate from pretenders\u2014and ask whether '
            'the first 30 games predict the final 130.',
            className='subtitle'
        ),
    ]),

    # Chart style toggle
    html.Div(className='controls-bar', style={'marginBottom': '12px'}, children=[
        html.Span('VIEW', style={'color': 'var(--text-dim)', 'fontSize': '10px',
                                  'letterSpacing': '2px', 'marginRight': '8px'}),
        html.Button('SMOOTHED', id='btn-smooth', className='mode-btn active', n_clicks=0),
        html.Button('RAW', id='btn-raw', className='mode-btn', n_clicks=0),
        html.Button('BY DIVISION', id='btn-facet', className='mode-btn', n_clicks=0),
    ]),

    # Filter controls
    html.Div(className='controls-bar', children=[
        html.Span('FILTER', style={'color': 'var(--text-dim)', 'fontSize': '10px',
                                    'letterSpacing': '2px', 'marginRight': '8px'}),
        html.Button('ALL TEAMS', id='btn-all', className='mode-btn active', n_clicks=0),
        html.Button('PLAYOFF TEAMS', id='btn-playoffs', className='mode-btn', n_clicks=0),
        html.Button('AL EAST', id='btn-ale', className='mode-btn', n_clicks=0),
        html.Button('AL CENTRAL', id='btn-alc', className='mode-btn', n_clicks=0),
        html.Button('AL WEST', id='btn-alw', className='mode-btn', n_clicks=0),
        html.Button('NL EAST', id='btn-nle', className='mode-btn', n_clicks=0),
        html.Button('NL CENTRAL', id='btn-nlc', className='mode-btn', n_clicks=0),
        html.Button('NL WEST', id='btn-nlw', className='mode-btn', n_clicks=0),
    ]),

    # Main content
    html.Div(className='main-grid', children=[
        # Chart
        html.Div(className='chart-container', children=[
            dcc.Graph(id='main-chart', config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            }),
        ]),

        # Sidebar standings
        html.Div(className='sidebar', children=[
            html.Div('FINAL STANDINGS', className='sidebar-title'),
            *[division_block(d) for d in DIVISIONS],
        ]),
    ]),

    # Footer
    html.Div(className='footer', children=[
        html.Span('DATA: MLB STATS API', className='footer-text'),
        html.Span('2025 REGULAR SEASON  /  162 GAMES', className='footer-text'),
    ]),
])


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

DIVISION_BTN_MAP = {
    'btn-ale': 'AL East', 'btn-alc': 'AL Central', 'btn-alw': 'AL West',
    'btn-nle': 'NL East', 'btn-nlc': 'NL Central', 'btn-nlw': 'NL West',
}

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
    tid = ctx.triggered_id
    if tid == 'btn-playoffs':
        return 'playoffs'
    elif tid in DIVISION_BTN_MAP:
        return DIVISION_BTN_MAP[tid]
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
    return {'btn-smooth': 'smooth', 'btn-raw': 'raw', 'btn-facet': 'facet'}.get(ctx.triggered_id, 'smooth')


@callback(
    Output('main-chart', 'figure'),
    Input('filter-mode', 'data'),
    Input('chart-style', 'data'),
)
def update_chart(filter_mode, style):
    if style == 'facet':
        return PRECOMPUTED[('facet', 'all')]
    tag = 'smooth' if style == 'smooth' else 'raw'
    key = (tag, filter_mode)
    if key in PRECOMPUTED:
        return PRECOMPUTED[key]
    # Fallback: build on the fly
    if filter_mode == 'playoffs':
        teams = [t for t in PLAYOFF_TEAMS_2025 if t in season_data]
        return build_combined(teams, 'playoffs', style == 'smooth')
    elif filter_mode in DIVISIONS:
        teams = [t for t in available_teams if TEAM_META[t]['div'] == filter_mode]
        return build_combined(teams, 'division', style == 'smooth')
    return build_combined(available_teams, 'all', style == 'smooth')


# Clientside callbacks to toggle active classes on button groups
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
