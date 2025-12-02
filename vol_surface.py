"""
Implied Volatility Surface Builder
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata
import warnings

warnings.filterwarnings('ignore')


def load_trades(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'prtTimestamp'
    df['timestamp'] = pd.to_datetime(df[ts_col].str.replace('D', 'T', regex=False), errors='coerce')
    df['timestamp'] = df['timestamp'] - pd.Timedelta(hours=5)
    
    for col in ['prtPrice', 'prtSize', 'uBid', 'uAsk', 'uPrc', 'okey_xx', 'prtIv']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    if 'ticker_tk' in df.columns:
        df = df[df['ticker_tk'] == 'SPY'].copy()
    
    df['expiration'] = pd.to_datetime(
        df['okey_yr'].astype(str) + '-' +
        df['okey_mn'].astype(str).str.zfill(2) + '-' +
        df['okey_dy'].astype(str).str.zfill(2)
    )
    
    return df


def filter_trades(df: pd.DataFrame, bucket_freq: str = '5min') -> pd.DataFrame:
    df = df[
        (df['prtPrice'] >= 0.05) &
        (df['prtSize'] > 0) &
        (df['prtIv'] > 0.02) &
        (df['prtIv'] < 1.0) &
        (df['uPrc'] > 0)
    ].copy()
    
    df['moneyness'] = df['okey_xx'] / df['uPrc']
    df = df[(df['moneyness'] >= 0.80) & (df['moneyness'] <= 1.20)]
    
    df['is_otm'] = (
        ((df['okey_cp'] == 'Put') & (df['okey_xx'] < df['uPrc'])) |
        ((df['okey_cp'] == 'Call') & (df['okey_xx'] > df['uPrc']))
    )
    
    df['bucket_time'] = df['timestamp'].dt.floor(bucket_freq)
    
    ref_date = df['bucket_time'].min().normalize()
    df['days_to_exp'] = (df['expiration'] - ref_date).dt.days
    df = df[df['days_to_exp'] > 0]
    
    return df


def aggregate_curves(df: pd.DataFrame, min_volume: int = 2) -> pd.DataFrame:
    agg = df.groupby(['bucket_time', 'expiration', 'okey_xx', 'okey_cp', 'is_otm']).agg({
        'prtIv': lambda x: np.average(x, weights=df.loc[x.index, 'prtSize']),
        'prtSize': 'sum',
        'days_to_exp': 'first',
        'uPrc': 'first',
        'moneyness': 'first'
    }).reset_index()
    
    agg.columns = ['bucket_time', 'expiration', 'strike', 'cp', 'is_otm',
                   'iv', 'volume', 'days_to_exp', 'underlying', 'moneyness']
    
    agg = agg[agg['volume'] >= min_volume]
    agg = agg[(agg['iv'] >= 0.05) & (agg['iv'] <= 0.35)]
    agg = agg[agg['days_to_exp'] <= 60]
    
    return agg


def build_animation(curves: pd.DataFrame, view: str = 'both', speed_ms: int = 500) -> go.Figure:
    buckets = sorted(curves['bucket_time'].unique())
    spot = curves['underlying'].median()
    
    k_min, k_max = spot * 0.90, spot * 1.10
    k_grid = np.linspace(k_min, k_max, 25)
    t_grid = np.linspace(1, 45, 18)
    K, T = np.meshgrid(k_grid, t_grid)
    
    colormap = {'puts': 'Reds', 'calls': 'Blues', 'both': 'Viridis'}
    colors = {'puts': 'red', 'calls': 'blue'}
    
    if view == 'puts':
        data = curves[curves['cp'] == 'Put']
    elif view == 'calls':
        data = curves[curves['cp'] == 'Call']
    else:
        data = curves
    
    frames = []
    
    for bt in buckets:
        bt_data = data[data['bucket_time'] == bt]
        if len(bt_data) < 5:
            continue
        
        frame_traces = []
        
        otm = bt_data[bt_data['is_otm'] == True]
        if len(otm) >= 5:
            try:
                Z = griddata(
                    (otm['strike'].values, otm['days_to_exp'].values),
                    otm['iv'].values * 100,
                    (K, T),
                    method='linear'
                )
                frame_traces.append(go.Surface(
                    x=K, y=T, z=Z,
                    colorscale=colormap.get(view, 'Viridis'),
                    opacity=0.7,
                    showscale=True,
                    colorbar=dict(title='IV %', len=0.5)
                ))
            except:
                pass
        
        if view == 'both':
            for side, color in [('Put', 'red'), ('Call', 'blue')]:
                subset = bt_data[bt_data['cp'] == side]
                if len(subset) > 0:
                    frame_traces.append(go.Scatter3d(
                        x=subset['strike'],
                        y=subset['days_to_exp'],
                        z=subset['iv'] * 100,
                        mode='markers',
                        marker=dict(size=5, color=color, opacity=0.8),
                        name=side
                    ))
        else:
            frame_traces.append(go.Scatter3d(
                x=bt_data['strike'],
                y=bt_data['days_to_exp'],
                z=bt_data['iv'] * 100,
                mode='markers',
                marker=dict(size=5, color=colors.get(view, 'gray'), opacity=0.8),
                name=view.capitalize()
            ))
        
        frame_traces.append(go.Scatter3d(
            x=[spot]*2, y=[1, 45], z=[8, 15],
            mode='lines',
            line=dict(color='limegreen', width=8),
            name='ATM'
        ))
        
        if frame_traces:
            frames.append(go.Frame(data=frame_traces, name=str(bt)))
    
    fig = go.Figure(data=frames[0].data, frames=frames)
    
    sliders = [{
        'active': 0,
        'currentvalue': {'prefix': 'Time: '},
        'pad': {'t': 50},
        'steps': [
            {'args': [[f.name], {'frame': {'duration': speed_ms, 'redraw': True}, 'mode': 'immediate'}],
             'label': pd.Timestamp(f.name).strftime('%H:%M'),
             'method': 'animate'}
            for f in frames
        ]
    }]
    
    buttons = [{
        'type': 'buttons',
        'showactive': False,
        'x': 0, 'y': 0,
        'buttons': [
            {'label': '▶', 'method': 'animate',
             'args': [None, {'frame': {'duration': speed_ms}, 'fromcurrent': True}]},
            {'label': '⏸', 'method': 'animate',
             'args': [[None], {'frame': {'duration': 0}, 'mode': 'immediate'}]}
        ]
    }]
    
    title_map = {
        'puts': 'Put Options',
        'calls': 'Call Options',
        'both': 'Puts & Calls'
    }
    
    fig.update_layout(
        title=dict(text=f'SPY Vol Surface — {title_map.get(view, view)}', x=0.5, y=0.95),
        scene=dict(
            xaxis_title='Strike',
            yaxis_title='DTE',
            zaxis_title='IV %',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.0)),
            aspectratio=dict(x=1, y=1, z=0.7),
            domain=dict(x=[0, 1], y=[0.1, 0.9])
        ),
        sliders=sliders,
        updatemenus=buttons,
        autosize=True,
        margin=dict(l=10, r=10, t=50, b=80),
        showlegend=True,
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(0,0,0,0.5)'),
        paper_bgcolor='rgba(0,0,0,0)',
        template='plotly_dark'
    )
    
    return fig


def build_price_chart(df: pd.DataFrame, freq: str = '5min') -> go.Figure:
    """Build OHLC candlestick chart for underlying price."""
    
    ohlc = df.groupby(df['bucket_time']).agg({
        'uPrc': ['first', 'max', 'min', 'last']
    }).reset_index()
    ohlc.columns = ['time', 'open', 'high', 'low', 'close']
    
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=ohlc['time'],
        open=ohlc['open'],
        high=ohlc['high'],
        low=ohlc['low'],
        close=ohlc['close'],
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350',
        name='SPY'
    ))
    
    fig.update_layout(
        title=dict(text='SPY Intraday Price', x=0.5, font=dict(size=14)),
        yaxis_title='Price ($)',
        xaxis_title='',
        height=280,
        margin=dict(l=50, r=20, t=40, b=30),
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        paper_bgcolor='rgba(18,18,26,1)',
        plot_bgcolor='rgba(18,18,26,1)'
    )
    
    return fig


def run(csv_path: str, output_dir: str = 'docs'):
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    df = load_trades(csv_path)
    df = filter_trades(df)
    curves = aggregate_curves(df)
    
    # Price chart
    fig_price = build_price_chart(df)
    fig_price.write_html(f'{output_dir}/price_chart.html')
    print(f'Saved {output_dir}/price_chart.html')
    
    for view in ['both', 'puts', 'calls']:
        fig = build_animation(curves, view=view)
        out = f'{output_dir}/vol_surface_v3_{view}.html'
        fig.write_html(out)
        print(f'Saved {out}')
    
    fig_clean = build_animation(curves, view='both')
    fig_clean.write_html(f'{output_dir}/vol_surface_v3_clean.html')
    print(f'Saved {output_dir}/vol_surface_v3_clean.html')


if __name__ == '__main__':
    run('Dec2023_Opratrade_2023.12.01_SPY.csv')

