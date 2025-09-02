#!/usr/bin/env python3
"""Performance analysis and reporting tool for elysiactl sync operations."""

import argparse
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

def analyze_checkpoint_performance(db_path: str) -> Dict[str, Any]:
    """Analyze performance from checkpoint database."""
    if not Path(db_path).exists():
        return {"error": "Checkpoint database not found"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Get run statistics
        runs = conn.execute("""
            SELECT run_id, started_at, completed_at, processed_lines,
                   success_count, error_count, collection_name
            FROM sync_runs
            WHERE completed_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 10
        """).fetchall()

        if not runs:
            return {"error": "No completed runs found"}

        # Calculate performance metrics
        run_metrics = []
        for run in runs:
            start_time = datetime.fromisoformat(run['started_at'])
            end_time = datetime.fromisoformat(run['completed_at'])
            duration = (end_time - start_time).total_seconds()

            files_per_second = run['processed_lines'] / duration if duration > 0 else 0
            success_rate = (run['success_count'] / max(run['processed_lines'], 1)) * 100

            run_metrics.append({
                'run_id': run['run_id'],
                'duration': duration,
                'files_processed': run['processed_lines'],
                'files_per_second': files_per_second,
                'success_rate': success_rate,
                'error_count': run['error_count'],
                'collection': run['collection_name']
            })

        # Aggregate statistics
        durations = [m['duration'] for m in run_metrics]
        fps_values = [m['files_per_second'] for m in run_metrics]
        success_rates = [m['success_rate'] for m in run_metrics]

        analysis = {
            'total_runs': len(run_metrics),
            'avg_duration': statistics.mean(durations),
            'avg_files_per_second': statistics.mean(fps_values),
            'avg_success_rate': statistics.mean(success_rates),
            'best_performance': max(fps_values),
            'worst_performance': min(fps_values),
            'recent_runs': run_metrics[:5],
            'performance_trend': 'improving' if len(fps_values) >= 2 and fps_values[0] > fps_values[-1] else 'stable'
        }

        # Get processing time statistics
        processing_times = conn.execute("""
            SELECT AVG(processing_time_ms) as avg_time,
                   MAX(processing_time_ms) as max_time,
                   MIN(processing_time_ms) as min_time,
                   COUNT(*) as total_operations
            FROM completed_lines
            WHERE processing_time_ms > 0
        """).fetchone()

        if processing_times and processing_times['total_operations'] > 0:
            analysis['avg_processing_time_ms'] = processing_times['avg_time']
            analysis['max_processing_time_ms'] = processing_times['max_time']
            analysis['min_processing_time_ms'] = processing_times['min_time']
            analysis['total_operations'] = processing_times['total_operations']

        return analysis

    finally:
        conn.close()

def generate_performance_report(db_path: str, output_dir: str = "performance_reports"):
    """Generate comprehensive performance report."""
    analysis = analyze_checkpoint_performance(db_path)

    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        return

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Generate text report
    report_file = output_path / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_file, 'w') as f:
        f.write("ElysiaCtl Sync Performance Report\n")
        f.write("=" * 35 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Database: {db_path}\n\n")

        f.write("Summary Statistics:\n")
        f.write(f"  Total runs analyzed: {analysis['total_runs']}\n")
        f.write(f"  Average duration: {analysis['avg_duration']:.2f} seconds\n")
        f.write(f"  Average throughput: {analysis['avg_files_per_second']:.1f} files/second\n")
        f.write(f"  Average success rate: {analysis['avg_success_rate']:.1f}%\n")
        f.write(f"  Best performance: {analysis['best_performance']:.1f} files/second\n")
        f.write(f"  Worst performance: {analysis['worst_performance']:.1f} files/second\n")
        f.write(f"  Performance trend: {analysis['performance_trend']}\n\n")

        if 'avg_processing_time_ms' in analysis:
            f.write("Processing Time Statistics:\n")
            f.write(f"  Average per operation: {analysis['avg_processing_time_ms']:.2f}ms\n")
            f.write(f"  Maximum per operation: {analysis['max_processing_time_ms']:.2f}ms\n")
            f.write(f"  Minimum per operation: {analysis['min_processing_time_ms']:.2f}ms\n")
            f.write(f"  Total operations: {analysis['total_operations']}\n\n")

        f.write("Recent Runs:\n")
        for i, run in enumerate(analysis['recent_runs'], 1):
            f.write(f"  {i}. {run['run_id']}\n")
            f.write(f"     Duration: {run['duration']:.2f}s\n")
            f.write(f"     Throughput: {run['files_per_second']:.1f} files/sec\n")
            f.write(f"     Success rate: {run['success_rate']:.1f}%\n")
            f.write(f"     Errors: {run['error_count']}\n\n")

    # Generate JSON report for programmatic use
    json_file = output_path / f"performance_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"Performance report generated:")
    print(f"  Text report: {report_file}")
    print(f"  JSON data: {json_file}")

    # Generate visualizations if matplotlib available
    try:
        generate_performance_charts(analysis, output_path)
    except ImportError:
        print("  Matplotlib not available - skipping charts")

def generate_performance_charts(analysis: Dict[str, Any], output_dir: Path):
    """Generate performance visualization charts."""
    # Throughput over time
    recent_runs = analysis['recent_runs']
    if len(recent_runs) >= 2:
        plt.figure(figsize=(12, 8))

        # Extract data
        run_numbers = list(range(len(recent_runs), 0, -1))  # Reverse for chronological order
        throughputs = [run['files_per_second'] for run in reversed(recent_runs)]
        success_rates = [run['success_rate'] for run in reversed(recent_runs)]

        # Throughput chart
        plt.subplot(2, 2, 1)
        plt.plot(run_numbers, throughputs, 'b-o', linewidth=2)
        plt.title('Throughput Over Recent Runs')
        plt.xlabel('Run Number (Most Recent → Oldest)')
        plt.ylabel('Files per Second')
        plt.grid(True, alpha=0.3)

        # Success rate chart
        plt.subplot(2, 2, 2)
        plt.plot(run_numbers, success_rates, 'g-o', linewidth=2)
        plt.title('Success Rate Over Recent Runs')
        plt.xlabel('Run Number (Most Recent → Oldest)')
        plt.ylabel('Success Rate (%)')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 105)

        # Performance distribution
        plt.subplot(2, 2, 3)
        plt.hist(throughputs, bins=max(3, len(throughputs)//2), alpha=0.7, color='blue')
        plt.title('Throughput Distribution')
        plt.xlabel('Files per Second')
        plt.ylabel('Frequency')
        plt.grid(True, alpha=0.3)

        # Summary statistics
        plt.subplot(2, 2, 4)
        plt.axis('off')
        stats_text = f"""Performance Summary:

Runs Analyzed: {analysis['total_runs']}
Avg Throughput: {analysis['avg_files_per_second']:.1f} files/sec
Best Performance: {analysis['best_performance']:.1f} files/sec
Avg Success Rate: {analysis['avg_success_rate']:.1f}%
Trend: {analysis['performance_trend']}"""

        plt.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))

        plt.tight_layout()

        chart_file = output_dir / f"performance_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  Performance charts: {chart_file}")

def main():
    parser = argparse.ArgumentParser(description="Analyze elysiactl sync performance")
    parser.add_argument("--db",
                       default="/var/lib/elysiactl/sync_checkpoints.db",
                       help="Path to checkpoint database")
    parser.add_argument("--output", "-o",
                       default="performance_reports",
                       help="Output directory for reports")
    parser.add_argument("--json-only",
                       action="store_true",
                       help="Output only JSON data")

    args = parser.parse_args()

    if args.json_only:
        analysis = analyze_checkpoint_performance(args.db)
        print(json.dumps(analysis, indent=2, default=str))
    else:
        generate_performance_report(args.db, args.output)

if __name__ == "__main__":
    main()