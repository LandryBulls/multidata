#!/usr/bin/env python
"""
Ensure all prerequisites are in place for run_full_extraction.py.

This script processes sessions that are missing:
1. Concatenated + trimmed/aligned video (derivatives/cam*_concatenated_trimmed.mp4)
2. Trimmed audio (derivatives/TRACK*_trimmed.wav)
3. Isolated audio (processed/TRACK*_trimmed_isolated_v2.wav)

It uses the existing multidata functions:
- concatenate_align.process_folder() for step 1+2
- run_isolation.run_isolation() for step 3

Usage:
    # Dry run — show what needs processing
    python run_prerequisites.py --dry-run

    # Process everything needed
    python run_prerequisites.py

    # Only run concat+align (skip isolation)
    python run_prerequisites.py --only concat

    # Only run isolation (skip concat)
    python run_prerequisites.py --only isolate

    # Process specific sessions
    python run_prerequisites.py --session 2025-10-15_001 2025-10-16_000
"""

from pathlib import Path
import argparse
import sys
import glob
from tqdm import tqdm

# Add multidata to path
MULTIDATA_DIR = Path(__file__).parent
sys.path.insert(0, str(MULTIDATA_DIR))


def _import_process_folder():
    from concatenate_align import process_folder
    return process_folder


def _import_run_isolation():
    from run_isolation import run_isolation
    return run_isolation


def get_session_status(session_dir):
    """Check what prerequisites a session is missing."""
    session_dir = Path(session_dir)
    deriv = session_dir / 'derivatives'
    processed = session_dir / 'processed'
    audio_dir = session_dir / 'audio'

    status = {
        'has_raw_cam1': (session_dir / 'cam1').exists() and any((session_dir / 'cam1').glob('*.mp4')),
        'has_raw_cam2': (session_dir / 'cam2').exists() and any((session_dir / 'cam2').glob('*.mp4')),
        'has_raw_360': (session_dir / '360cam').exists() and (
            any((session_dir / '360cam').glob('*.mp4')) or any((session_dir / '360cam').glob('*.360'))
        ),
        'has_audio': audio_dir.exists() and bool(
            list(audio_dir.glob('*.wav')) + list(audio_dir.glob('*.WAV'))
        ),
        'n_audio': len(list(audio_dir.glob('*.wav')) + list(audio_dir.glob('*.WAV'))) if audio_dir.exists() else 0,
    }

    # Check concatenated + trimmed videos
    for cam in ['cam1', 'cam2', '360cam']:
        status[f'{cam}_concat_trimmed'] = (deriv / f'{cam}_concatenated_trimmed.mp4').exists()

    # Check trimmed audio in derivatives
    trimmed_audio = sorted(glob.glob(str(deriv / 'TRACK*_trimmed.wav'))) if deriv.exists() else []
    status['trimmed_audio'] = len(trimmed_audio)

    # Check isolated audio in processed
    isolated = sorted(glob.glob(str(processed / 'TRACK*_trimmed_isolated_v2.wav'))) if processed.exists() else []
    status['isolated_audio'] = len(isolated)

    # Determine what's needed
    has_all_concat = all(status[f'{cam}_concat_trimmed'] for cam in ['cam1', 'cam2', '360cam'])
    status['needs_concat'] = not has_all_concat and status['has_audio']
    status['needs_isolation'] = (
        status['isolated_audio'] < status['n_audio']
        and status['n_audio'] > 0
        and status['trimmed_audio'] >= status['n_audio']  # need trimmed audio first
    )

    return status


def main():
    parser = argparse.ArgumentParser(
        description='Process prerequisites for the full extraction pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without doing it')
    parser.add_argument('--only', choices=['concat', 'isolate'], help='Only run one step')
    parser.add_argument('--session', nargs='+', help='Process only specific session(s)')
    parser.add_argument('--data-dir', type=str, default=None, help='Override data directory')
    parser.add_argument('--stop-on-error', action='store_true', help='Stop on first error')
    args = parser.parse_args()

    # Read data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        with open(Path(__file__).parent / 'data_management' / 'main_data_dir.txt', 'r') as f:
            data_dir = Path(f.read().strip())

    print(f'Data directory: {data_dir}')

    # Find session directories
    all_sessions = sorted([
        d for d in data_dir.iterdir()
        if d.is_dir() and d.name[0].isdigit() and '_remove' not in d.name
    ])

    if args.session:
        all_sessions = [d for d in all_sessions if d.name in args.session]
        if not all_sessions:
            print(f'No matching sessions found for: {args.session}')
            sys.exit(1)

    # Check status of all sessions
    print(f'\nChecking {len(all_sessions)} sessions...')
    statuses = {}
    for d in tqdm(all_sessions, desc='Scanning'):
        statuses[d] = get_session_status(d)

    # Categorize
    needs_concat = [d for d, s in statuses.items() if s['needs_concat']]
    needs_isolation = [d for d, s in statuses.items() if s['needs_isolation']]
    # Sessions that need concat first, then isolation after
    needs_isolation_after_concat = [
        d for d, s in statuses.items()
        if s['needs_concat'] and s['n_audio'] > 0 and s['isolated_audio'] < s['n_audio']
    ]
    skipped = [
        d for d, s in statuses.items()
        if s['needs_concat'] and not s['has_audio']
    ]

    # Report
    print(f'\n{"="*70}')
    print(f'PREREQUISITE STATUS')
    print(f'{"="*70}')
    print(f'Total sessions:              {len(all_sessions)}')
    print(f'Need concat+align:           {len(needs_concat)}')
    print(f'Need isolation (ready now):  {len(needs_isolation)}')
    print(f'Need isolation (after concat): {len(needs_isolation_after_concat)}')
    if skipped:
        print(f'Skipped (no audio/cameras):  {len(skipped)}')
        for d in skipped:
            s = statuses[d]
            print(f'  {d.name}: cam1={s["has_raw_cam1"]}, cam2={s["has_raw_cam2"]}, audio={s["n_audio"]}')

    if needs_concat and args.only != 'isolate':
        print(f'\nSessions needing concat+align:')
        for d in needs_concat:
            s = statuses[d]
            missing = [cam for cam in ['cam1', 'cam2', '360cam'] if not s[f'{cam}_concat_trimmed']]
            print(f'  {d.name}  (missing: {", ".join(missing)}, audio tracks: {s["n_audio"]})')

    if needs_isolation and args.only != 'concat':
        print(f'\nSessions needing isolation (ready):')
        for d in needs_isolation:
            s = statuses[d]
            print(f'  {d.name}  (have {s["isolated_audio"]}/{s["n_audio"]} isolated)')

    if needs_isolation_after_concat and args.only != 'concat':
        print(f'\nSessions needing isolation (after concat):')
        for d in needs_isolation_after_concat:
            if d not in needs_isolation:
                s = statuses[d]
                print(f'  {d.name}  (have {s["isolated_audio"]}/{s["n_audio"]} isolated)')

    if args.dry_run:
        print(f'\n(Dry run — no changes made)')
        return

    # ---- Step 1: Concatenation + Alignment ----
    if needs_concat and args.only != 'isolate':
        print(f'\n{"="*70}')
        print(f'STEP 1: CONCATENATION + ALIGNMENT ({len(needs_concat)} sessions)')
        print(f'{"="*70}')

        n_success = 0
        n_failed = 0
        for i, d in enumerate(needs_concat, 1):
            print(f'\n[{i}/{len(needs_concat)}] Processing {d.name}...')
            try:
                _import_process_folder()(d)
                n_success += 1
                # Update status after concat
                statuses[d] = get_session_status(d)
            except Exception as e:
                n_failed += 1
                print(f'  ERROR: {e}')
                if args.stop_on_error:
                    print('Stopping on error.')
                    sys.exit(1)

        print(f'\nConcat results: {n_success} succeeded, {n_failed} failed')

        # After concat, re-check which sessions now need isolation
        needs_isolation = [
            d for d, s in statuses.items()
            if s['isolated_audio'] < s['n_audio']
            and s['n_audio'] > 0
            and s['trimmed_audio'] >= s['n_audio']
        ]

    # ---- Step 2: Audio Isolation ----
    if needs_isolation and args.only != 'concat':
        print(f'\n{"="*70}')
        print(f'STEP 2: AUDIO ISOLATION ({len(needs_isolation)} sessions)')
        print(f'{"="*70}')

        n_success = 0
        n_failed = 0
        for i, d in enumerate(needs_isolation, 1):
            print(f'\n[{i}/{len(needs_isolation)}] Isolating {d.name}...')
            try:
                _import_run_isolation()(d)
                n_success += 1
            except Exception as e:
                n_failed += 1
                print(f'  ERROR: {e}')
                if args.stop_on_error:
                    print('Stopping on error.')
                    sys.exit(1)

        print(f'\nIsolation results: {n_success} succeeded, {n_failed} failed')

    print(f'\nDone.')


if __name__ == '__main__':
    main()
