#!/usr/bin/env python3
"""
Extract key buffer pool metrics from a PGBufBench metrics CSV.
Usage:
    python3 extract_metrics.py                                         # latest run
    python3 extract_metrics.py results/metrics_<id>.csv               # specific run
    python3 extract_metrics.py results/metrics_<id>.csv config/x.yaml # with buffer size
Output is printed to stdout and appended to summary.log
"""
import csv
import sys
import os
import glob
import subprocess
import re
from datetime import datetime


LOG_FILE = 'summary.log'


class Tee:
    """Write to both stdout and a log file simultaneously."""
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log      = open(filepath, 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def get_db_size():
    try:
        env = {**os.environ, 'PGPASSWORD': 'bgbench123'}
        result = subprocess.run(
            ['psql', '-U', 'bgbench', '-h', 'localhost',
             '-d', 'bgbenchdb', '-t', '-c',
             'SELECT pg_size_pretty(pg_database_size(current_database()));'],
            capture_output=True, text=True, timeout=10, env=env
        )
        return result.stdout.strip()
    except Exception:
        return 'N/A'


def get_buffer_size(config_filepath):
    if not config_filepath or not os.path.exists(config_filepath):
        return 'N/A'
    try:
        import yaml
        with open(config_filepath) as f:
            config = yaml.safe_load(f)
        pg = config.get('postgresql', {})
        return pg.get('shared_buffers', 'N/A')
    except Exception:
        return 'N/A'


def get_summary_tps(metrics_filepath):
    """Read TPS and latency from the matching summary CSV (authoritative)."""
    summary_file = metrics_filepath.replace('metrics_', 'summary_')
    if os.path.exists(summary_file):
        with open(summary_file) as f:
            rows = list(csv.DictReader(f))
            if rows:
                r = rows[0]
                return {
                    'tps':         float(r['tps']),
                    'avg_latency': float(r['avg_latency']),
                    'min_latency': float(r['min_latency']),
                    'max_latency': float(r['max_latency']),
                    'p50_latency': float(r['p50_latency']),
                    'p95_latency': float(r['p95_latency']),
                    'p99_latency': float(r['p99_latency']),
                    'total_txns':  int(r['total_txns']),
                }
    return None


def get_interference_summary(metrics_filepath):
    """Read aggregate interference stats from the matching txt file."""
    run_id      = os.path.basename(metrics_filepath) \
        .replace('metrics_', '').replace('.csv', '')
    results_dir = os.path.dirname(metrics_filepath)
    txt_file    = os.path.join(results_dir, f"interference_{run_id}.txt")
    if not os.path.exists(txt_file):
        return None
    stats = {}
    with open(txt_file) as f:
        content = f.read()
    ckpt = re.search(
        r'CHECKPOINT\s+count=(\d+)\s+avg_drop=([\d.]+)%\s+'
        r'max_drop=([\d.]+)%\s+avg_recovery=([\d.]+)s', content)
    vac = re.search(
        r'VACUUM\s+count=(\d+)\s+avg_drop=([\d.]+)%\s+'
        r'max_drop=([\d.]+)%\s+avg_recovery=([\d.]+)s', content)
    if ckpt:
        stats['ckpt_count']    = int(ckpt.group(1))
        stats['ckpt_avg_drop'] = float(ckpt.group(2))
        stats['ckpt_max_drop'] = float(ckpt.group(3))
        stats['ckpt_avg_rec']  = float(ckpt.group(4))
    if vac:
        stats['vac_count']    = int(vac.group(1))
        stats['vac_avg_drop'] = float(vac.group(2))
        stats['vac_max_drop'] = float(vac.group(3))
        stats['vac_avg_rec']  = float(vac.group(4))
    return stats if stats else None


def extract(filepath, config_filepath=None):
    with open(filepath, 'r') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No data found.")
        return

    def col(name):
        return [float(r[name]) for r in rows if r.get(name, '').strip()]

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    def total_delta(name):
        vals = col(name)
        return sum(vals) if vals else 0

    # ── Core metrics ─────────────────────────────────────────────
    hit_rates   = [v for v in col('hit_rate_pct')         if v > 0]
    evictions   = col('eviction_rate')
    utilization = col('buffer_utilization_pct')
    dirty       = col('dirty_buffers')
    avg_uc      = col('avg_usage_count')
    pinned      = col('pinned_buffers')
    used_bufs   = col('used_buffers')
    free_bufs   = col('free_buffers')
    heap_hr     = [v for v in col('heap_hit_rate_pct')    if v > 0]
    index_hr    = [v for v in col('index_hit_rate_pct')   if v > 0]

    # ── Throughput / tuple activity ───────────────────────────────
    tps_vals  = [v for v in col('tps')      if v > 0]
    commits   = [v for v in col('commits')  if v > 0]
    rollbacks = col('rollbacks')
    tup_ins   = col('tup_inserted')
    tup_upd   = col('tup_updated')
    tup_del   = col('tup_deleted')
    tup_fet   = col('tup_fetched')

    # ── bgwriter / checkpointer ───────────────────────────────────
    bufs_alloc   = total_delta('buffers_alloc')
    bufs_clean   = total_delta('buffers_clean')
    bufs_written = total_delta('buffers_written')
    maxwritten   = total_delta('maxwritten_clean')
    write_time   = total_delta('write_time')
    sync_time    = total_delta('sync_time')

    # ── Background events ─────────────────────────────────────────
    ckpt_rows   = [r for r in rows if float(r.get('checkpoint_happened', 0)) == 1]
    vac_rows    = [r for r in rows if float(r.get('vacuum_happened',    0)) == 1]
    dead_tuples = col('dead_tuples')

    # ── External sources ──────────────────────────────────────────
    run_id      = os.path.basename(filepath) \
        .replace('metrics_', '').replace('.csv', '')
    db_size     = get_db_size()
    buffer_size = get_buffer_size(config_filepath)
    summary     = get_summary_tps(filepath)
    interf      = get_interference_summary(filepath)

    # ─────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Run: {run_id}")
    print(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # ── Database ──────────────────────────────────────────────────
    print(f"\n-- Database --")
    print(f"  DB size:              {db_size}")
    print(f"  Shared buffers:       {buffer_size}")
    print(f"  Snapshots collected:  {len(rows)}")

    # ── Throughput ────────────────────────────────────────────────
    print(f"\n-- Throughput --")
    if summary:
        print(f"  TPS:                  {summary['tps']:.2f}"
              f"  (from summary — authoritative)")
        print(f"  Total transactions:   {summary['total_txns']:,}")
        print(f"  Avg latency:          {summary['avg_latency']:.2f} ms")
        print(f"  Min latency:          {summary['min_latency']:.2f} ms")
        print(f"  Max latency:          {summary['max_latency']:.2f} ms")
        print(f"  p50 latency:          {summary['p50_latency']:.2f} ms")
        print(f"  p95 latency:          {summary['p95_latency']:.2f} ms")
        print(f"  p99 latency:          {summary['p99_latency']:.2f} ms")
    else:
        print(f"  TPS avg:              {avg(tps_vals):.2f}"
              f"  (from metrics — summary CSV not found)")
        print(f"  TPS max:              {max(tps_vals):.2f}")
        print(f"  TPS min:              {min(tps_vals):.2f}")
    if commits:
        total_commits   = sum(commits)
        total_rollbacks = sum(rollbacks)
        total_ops       = total_commits + total_rollbacks
        rollback_pct    = (total_rollbacks / total_ops * 100) if total_ops else 0
        print(f"  Commits (total):      {total_commits:,.0f}")
        print(f"  Rollbacks (total):    {total_rollbacks:,.0f}"
              f"  ({rollback_pct:.2f}%)")

    # ── Tuple activity ────────────────────────────────────────────
    print(f"\n-- Tuple Activity (avg/s) --")
    print(f"  Inserted:             {avg(tup_ins):,.1f}")
    print(f"  Updated:              {avg(tup_upd):,.1f}")
    print(f"  Deleted:              {avg(tup_del):,.1f}")
    print(f"  Fetched:              {avg(tup_fet):,.1f}")

    # ── Buffer pool ───────────────────────────────────────────────
    print(f"\n-- Buffer Pool --")
    print(f"  Hit rate avg:         {avg(hit_rates):.2f}%")
    print(f"  Hit rate min:         {min(hit_rates):.2f}%")
    print(f"  Hit rate max:         {max(hit_rates):.2f}%")
    if heap_hr:
        print(f"  Heap hit rate avg:    {avg(heap_hr):.2f}%")
    if index_hr:
        print(f"  Index hit rate avg:   {avg(index_hr):.2f}%")
    print(f"  Eviction avg:         {avg(evictions):.2f} pages/s")
    print(f"  Eviction max:         {max(evictions):.2f} pages/s")
    print(f"  Utilization avg:      {avg(utilization):.2f}%")
    print(f"  Used buffers avg:     {avg(used_bufs):,.0f}")
    print(f"  Free buffers avg:     {avg(free_bufs):,.0f}")
    print(f"  Dirty bufs avg:       {avg(dirty):,.0f}")
    print(f"  Pinned bufs avg:      {avg(pinned):,.0f}")
    print(f"  Avg usage count:      {avg(avg_uc):.2f}")

    # ── bgwriter / checkpointer ───────────────────────────────────
    print(f"\n-- bgwriter / Checkpointer --")
    print(f"  Buffers alloc (total):   {bufs_alloc:,.0f}")
    print(f"  Buffers cleaned (total): {bufs_clean:,.0f}")
    print(f"  Buffers written (total): {bufs_written:,.0f}")
    print(f"  maxwritten_clean:        {maxwritten:,.0f}")
    print(f"  Checkpoint write time:   {write_time:,.0f} ms")
    print(f"  Checkpoint sync time:    {sync_time:,.0f} ms")

    # ── Background events ─────────────────────────────────────────
    print(f"\n-- Background Events --")
    print(f"  Checkpoint events:    {len(ckpt_rows)}")
    print(f"  Vacuum events:        {len(vac_rows)}")
    if dead_tuples:
        print(f"  Dead tuples avg:      {avg(dead_tuples):,.0f}")
        print(f"  Dead tuples max:      {max(dead_tuples):,.0f}")

    # ── Interference summary ──────────────────────────────────────
    if interf:
        print(f"\n-- Interference Summary --")
        if 'ckpt_count' in interf:
            print(f"  Checkpoint count:     {interf['ckpt_count']}")
            print(f"  Checkpoint avg drop:  {interf['ckpt_avg_drop']:.1f}%")
            print(f"  Checkpoint max drop:  {interf['ckpt_max_drop']:.1f}%")
            print(f"  Checkpoint avg rec:   {interf['ckpt_avg_rec']:.1f}s")
        if 'vac_count' in interf:
            print(f"  Vacuum count:         {interf['vac_count']}")
            print(f"  Vacuum avg drop:      {interf['vac_avg_drop']:.1f}%")
            print(f"  Vacuum max drop:      {interf['vac_max_drop']:.1f}%")
            print(f"  Vacuum avg rec:       {interf['vac_avg_rec']:.1f}s")

    # ── TPC-H Query Summary (from main.py output) ────────────────
    run_dir  = os.path.dirname(filepath)
    qph_file = os.path.join(run_dir, f"tpch_qph_{run_id}.csv")
    if os.path.exists(qph_file):
        print(f"\n-- TPC-H Query Summary --")
        print(f"  {'Query':<8} {'Count':>6} {'Avg(ms)':>10} {'P50(ms)':>10} {'P99(ms)':>10} {'Q/hour':>10}")
        print(f"  {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
        with open(qph_file) as f:
            reader = csv.DictReader(f)
            total_qph = 0
            for row in reader:
                print(f"  {row['query']:<8} {row['count']:>6} {row['avg_ms']:>10} {row['p50_ms']:>10} {row['p99_ms']:>10} {row['qph']:>10}")
                total_qph += float(row['qph'])
        print(f"  {'TOTAL':<8} {'':>6} {'':>10} {'':>10} {'':>10} {round(total_qph,1):>10}")
    print()


if __name__ == '__main__':
    tee = Tee(LOG_FILE)
    sys.stdout = tee

    try:
        if len(sys.argv) < 2:
            files = sorted(glob.glob('results/metrics_*.csv'))
            if files:
                extract(files[-1])
            else:
                print("No metrics files found.")
        elif len(sys.argv) == 2:
            extract(sys.argv[1])
        else:
            extract(sys.argv[1], sys.argv[2])
    finally:
        sys.stdout = tee.terminal
        tee.close()
        print(f"[extract_metrics] Output appended to {LOG_FILE}")
