import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import date

# Anchor points taken from published reports cited in the analysis (not tick-by-tick data)
# Dollar free market (Toman)
d_dates = [date(2026,9,13), date(2026,10,4), date(2026,10,7), date(2026,10,11), date(2026,10,12), date(2026,10,13)]
d_vals  = [231350, 266700, 270000, 265000, 262200, 262000]

# Gold 18k per gram (Toman)
g_dates = [date(2026,9,26), date(2026,10,4), date(2026,10,7), date(2026,10,10), date(2026,10,12), date(2026,10,13)]
g_vals  = [24124600, 26000000, 26700000, 25651400, 26019210, 25700000]

plt.rcParams['font.family'] = 'DejaVu Sans'
fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=False)
fig.patch.set_facecolor('white')

# --- Dollar ---
ax = axes[0]
ax.set_facecolor('#0f172a')
ax.plot(d_dates, d_vals, color='#38bdf8', lw=3, marker='o', markersize=7,
        markerfacecolor='white', markeredgewidth=2, zorder=5, label='USD free market (anchor closes)')
ax.fill_between(d_dates, d_vals, alpha=0.15, color='#38bdf8')
# bands
ax.axhspan(259000, 262000, color='#22c55e', alpha=0.22, label='Support 259k-262k')
ax.axhspan(262500, 265100, color='#f59e0b', alpha=0.22, label='Resistance 262.5k-265.1k')
ax.axhspan(268500, 272010, color='#ef4444', alpha=0.20, label='ATH zone 268.5k-272k')
for i,(x, y) in enumerate(zip(d_dates, d_vals)):
    off = (0,-18) if i==4 else (0,10)
    ax.annotate(f"{y:,}", (x, y), textcoords="offset points", xytext=off, ha='center', color='white', fontsize=9, weight='bold')
ax.set_ylim(225000, 276000)
ax.set_title('USD / Toman — Free Market: Uptrend + Short-term Correction (Sep-Oct 2026)', color='white', fontsize=13, weight='bold', loc='left')
ax.set_ylabel('Toman', color='white')
ax.tick_params(colors='white')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{int(v/1000)}k"))
ax.grid(True, color='white', alpha=0.12)
ax.legend(facecolor='#1e293b', labelcolor='white', fontsize=8, loc='lower right')
for s in ax.spines.values(): s.set_color('#334155')

# --- Gold ---
ax = axes[1]
ax.set_facecolor('#1a1207')
ax.plot(g_dates, g_vals, color='#facc15', lw=3, marker='o', markersize=7,
        markerfacecolor='white', markeredgewidth=2, zorder=5, label='Gold 18k / gram (anchor closes)')
ax.fill_between(g_dates, g_vals, alpha=0.15, color='#facc15')
ax.axhspan(25251000, 25700000, color='#22c55e', alpha=0.22, label='Support 25.25M-25.70M')
ax.axhline(26000000, color='#f59e0b', lw=2, ls='--', label='Pivot 26.00M')
ax.axhspan(26500000, 26871000, color='#ef4444', alpha=0.20, label='Resistance / High 26.50M-26.87M')
for x, y in zip(g_dates, g_vals):
    ax.annotate(f"{y/1e6:.2f}M", (x, y), textcoords="offset points", xytext=(0,10), ha='center', color='white', fontsize=9, weight='bold')
ax.set_ylim(23500000, 27500000)
ax.set_title('Gold 18k (per gram) / Toman: Driven by USD, Testing Support After Peak', color='white', fontsize=13, weight='bold', loc='left')
ax.set_ylabel('Toman', color='white')
ax.tick_params(colors='white')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"{v/1e6:.1f}M"))
ax.grid(True, color='white', alpha=0.12)
ax.legend(facecolor='#292524', labelcolor='white', fontsize=8, loc='upper left')
for s in ax.spines.values(): s.set_color('#44403c')

fig.suptitle('Gold & USD — Iran Market  |  21 Mehr 1405 (13 Oct 2026)  |  Schematic from published anchor levels, not tick data',
             fontsize=11, color='#334155', y=0.98)
plt.tight_layout(rect=[0,0,1,0.96])
plt.savefig('/home/user/Hitler/gold-dollar-chart.png', dpi=200, bbox_inches='tight')
print("saved")
