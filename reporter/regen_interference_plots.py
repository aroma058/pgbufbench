"""
Regenerate checkpoint and interference plots for tpcb_20260607_104402
with larger fonts for paper inclusion.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import csv
import os

os.makedirs('Plots', exist_ok=True)

RUN_ID = 'tpcb_20260607_104402'

# ── Font sizes ────────────────────────────────────────────────────────────────
FS_LABEL  = 22
FS_TICK   = 18
FS_ANNOT  = 13
FS_LEGEND = 18
FS_TITLE  = 19

# ── Load metrics CSV ──────────────────────────────────────────────────────────
elapsed    = []
tps        = []
write_time = []

with open(f'/home/cc/bgbench/results/metrics_{RUN_ID}.csv', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        elapsed.append(float(row['elapsed_sec']))
        tps.append(float(row['tps']))
        write_time.append(float(row['write_time']))

# ── Events from interference CSV ─────────────────────────────────────────────
events = [
    {'type': 'VACUUM',      'elapsed': 40.6,  'tps_during': 617.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 57.7,  'tps_during': 617.0, 'drop_pct': 0.0},
    {'type': 'VACUUM',      'elapsed': 100.3, 'tps_during': 618.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 117.5, 'tps_during': 609.0, 'drop_pct': 1.3},
    {'type': 'VACUUM',      'elapsed': 161.0, 'tps_during': 630.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 176.2, 'tps_during': 621.0, 'drop_pct': 1.4},
    {'type': 'VACUUM',      'elapsed': 220.8, 'tps_during': 650.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 234.0, 'tps_during': 653.0, 'drop_pct': 0.0},
    {'type': 'VACUUM',      'elapsed': 280.6, 'tps_during': 653.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 291.7, 'tps_during': 646.0, 'drop_pct': 1.0},
    {'type': 'VACUUM',      'elapsed': 340.3, 'tps_during': 662.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 348.4, 'tps_during': 649.0, 'drop_pct': 1.8},
    {'type': 'VACUUM',      'elapsed': 401.1, 'tps_during': 681.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 405.1, 'tps_during': 666.0, 'drop_pct': 0.0},
    {'type': 'CHECKPOINT',  'elapsed': 461.8, 'tps_during': 672.0, 'drop_pct': 1.7},
    {'type': 'CHECKPOINT',  'elapsed': 517.6, 'tps_during': 692.0, 'drop_pct': 1.0},
    {'type': 'VACUUM',      'elapsed': 520.6, 'tps_during': 677.0, 'drop_pct': 2.2},
    {'type': 'CHECKPOINT',  'elapsed': 573.3, 'tps_during': 706.0, 'drop_pct': 0.0},
]

ckpt_events = [e for e in events if e['type'] == 'CHECKPOINT']
vac_events  = [e for e in events if e['type'] == 'VACUUM']
max_tps     = max(tps)

# ── Plot 1: TPS vs Checkpoint Write Time ──────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(14, 5))

ax1.plot(elapsed, tps, color='steelblue', linewidth=1.5, label='TPS')
ax1.set_xlabel('Elapsed (s)', fontsize=FS_LABEL)
ax1.set_ylabel('TPS', color='steelblue', fontsize=FS_LABEL)
ax1.tick_params(axis='both', labelsize=FS_TICK)
ax1.tick_params(axis='y', labelcolor='steelblue')

ax2 = ax1.twinx()
write_time_s = [v / 1000 for v in write_time]
ax2.plot(elapsed, write_time_s, color='red', linewidth=1.2, alpha=0.8)
ax2.set_ylabel('Checkpoint write time (s)', color='red', fontsize=FS_LABEL)
ax2.tick_params(axis='y', labelcolor='red', labelsize=FS_TICK)

# no title
ax1.set_xticks([0, 100, 200, 300, 400, 500, 600])
ax1.set_yticks([0, 200, 400, 600, 800, 1000, 1200, 1400])
ax1.grid(True, alpha=0.3)
plt.tight_layout()
out = f'Plots/{RUN_ID}_checkpoint.pdf'
fig.savefig(out, dpi=300, bbox_inches='tight')
print(f'Saved: {out}')
plt.close()

# ── Plot 2: TPS with Background Event Interference ───────────────────────────
fig, ax = plt.subplots(figsize=(14, 5))

ax.plot(elapsed, tps, color='steelblue', linewidth=1.5, label='TPS', zorder=3)

for e in ckpt_events:
    ax.axvline(x=e['elapsed'], color='red', alpha=0.7, linewidth=1.5,
               linestyle='--', zorder=2)
    ax.annotate(
        f"-{e['drop_pct']}%",
        xy=(e['elapsed'], e['tps_during']),
        xytext=(e['elapsed'] + 1.5, e['tps_during'] + max_tps * 0.06),
        fontsize=FS_ANNOT, color='red',
        arrowprops=dict(arrowstyle='->', color='red', lw=0.8)
    )

for e in vac_events:
    ax.axvline(x=e['elapsed'], color='orange', alpha=0.7, linewidth=1.5,
               linestyle='--', zorder=2)
    ax.annotate(
        f"-{e['drop_pct']}%",
        xy=(e['elapsed'], e['tps_during']),
        xytext=(e['elapsed'], max_tps * 0.25),
        fontsize=FS_ANNOT, color='darkorange', ha='center',
        arrowprops=dict(arrowstyle='->', color='darkorange', lw=0.8)
    )

ax.legend(handles=[
    mpatches.Patch(color='steelblue', label='TPS'),
    mpatches.Patch(color='red',    alpha=0.7, label='Checkpoint'),
    mpatches.Patch(color='orange', alpha=0.7, label='Vacuum'),
], fontsize=FS_LEGEND, frameon=False, loc='upper center',
           bbox_to_anchor=(0.5, 1.18), ncol=3)

ax.set_xlabel('Elapsed (s)', fontsize=FS_LABEL)
ax.set_ylabel('TPS', fontsize=FS_LABEL)
ax.tick_params(labelsize=FS_TICK)
# no title
ax.set_xticks([0, 100, 200, 300, 400, 500, 600])
ax.set_yticks([0, 200, 400, 600, 800, 1000, 1200, 1400])
ax.grid(True, alpha=0.3)
plt.tight_layout()
out = f'Plots/{RUN_ID}_interference.pdf'
fig.savefig(out, dpi=300, bbox_inches='tight')
print(f'Saved: {out}')
plt.close()
