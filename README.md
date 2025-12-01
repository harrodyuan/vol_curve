# SPY Implied Volatility Surface

Interactive 3D visualization of SPY options implied volatility dynamics.

**[View Live Demo →](https://harrodyuan.github.io/vol_curve/)**

## Visualizations

| View | Description |
|------|-------------|
| [Clean Surface](docs/vol_surface_v3_clean.html) | Interpolated surface from OTM options |
| [Puts & Calls](docs/vol_surface_v3_both.html) | Combined view with red puts, blue calls |
| [Puts Only](docs/vol_surface_v3_puts.html) | Put option volatility |
| [Calls Only](docs/vol_surface_v3_calls.html) | Call option volatility |

## Data

Options trade data sourced from SpiderRock OPRA feed via kdb+/q.

### Download Data

```python
from data_download import download_sample_day

# Set environment variables
# SPIDERROCK_HOST=your_host
# SPIDERROCK_PORT=5000

download_sample_day()
```

### Data Schema

| Column | Description |
|--------|-------------|
| `prtTimestamp` | Trade timestamp (UTC) |
| `okey_xx` | Strike price |
| `okey_cp` | Put/Call indicator |
| `prtPrice` | Trade price |
| `prtSize` | Trade size |
| `prtIv` | Implied volatility |
| `uPrc` | Underlying price |

## Build Surfaces

```bash
python vol_surface.py
```

Generates four HTML files in `docs/`:
- `vol_surface_v3_clean.html`
- `vol_surface_v3_both.html`
- `vol_surface_v3_puts.html`
- `vol_surface_v3_calls.html`

## Technical Notes

- **Time buckets**: 5-minute aggregation
- **IV filter**: 5% to 35%
- **Moneyness**: 80% to 120% of spot
- **Expiration**: ≤60 days
- **Timezone**: Eastern Time (ET)
- **Surface**: Linear interpolation on OTM options

## Requirements

```
pandas
numpy
scipy
plotly
pykx  # for data download
```

## GitHub Pages

To enable the live demo:
1. Go to repo Settings → Pages
2. Set Source: Deploy from branch
3. Select: `main` branch, `/docs` folder
4. Save

