"""
Isolate audio for all group conversation sessions using voicolate's 
cross-microphone spectral dominance approach.

This script processes audio files in the derivatives/ folder and saves
isolated audio to processed/ with naming compatible with the full 
extraction pipeline (TRACK*_trimmed_isolated_v2.wav).

Usage:
    # Process a single session
    python isolate_all_group_audio.py /path/to/session
    
    # Process all sessions in a directory
    python isolate_all_group_audio.py /path/to/sessions --all
    
    # Force reprocessing
    python isolate_all_group_audio.py /path/to/sessions --all --force
    
    # Custom parameters
    python isolate_all_group_audio.py /path/to/session --dominance 3.0 --harmonicity 0.5
"""

import argparse
from pathlib import Path
from glob import glob
import os
from scipy.io import wavfile
import numpy as np

from voicolate.isolate import isolate


def get_audio_files(session_path: Path) -> list:
    """Get trimmed audio files from derivatives folder."""
    derivatives_dir = session_path / 'derivatives'
    if not derivatives_dir.exists():
        return []
    
    # Look for trimmed WAV files
    audio_files = sorted(derivatives_dir.glob('TRACK*_trimmed.wav'))
    return [str(f) for f in audio_files]


def check_existing_outputs(session_path: Path, n_files: int) -> bool:
    """Check if isolated outputs already exist."""
    processed_dir = session_path / 'processed'
    if not processed_dir.exists():
        return False
    
    # Check for TRACK*_trimmed_isolated_v2.wav files
    existing = list(processed_dir.glob('TRACK*_trimmed_isolated_v2.wav'))
    return len(existing) >= n_files


def isolate_session(session_path: Path, force: bool = False,
                   dominance_margin_db: float = 3.0,
                   harmonicity_weight: float = 0.5,
                   gate_threshold_db: float = -40,
                   gate_lookahead_ms: float = 30,
                   gate_hold_ms: float = 50) -> bool:
    """
    Isolate audio for a single session.
    
    Parameters:
        session_path: Path to session directory
        force: Reprocess even if outputs exist
        dominance_margin_db: dB advantage required to be dominant (lower = more aggressive)
        harmonicity_weight: Weight for harmonicity penalty (higher = more breath suppression)
        gate_threshold_db: Soft gate threshold in dB below peak
        gate_lookahead_ms: Gate lookahead to preserve onsets
        gate_hold_ms: Gate hold time to preserve offsets
    
    Returns:
        True if successful, False otherwise
    """
    session_id = session_path.name
    print(f"\n{'='*60}")
    print(f"Processing: {session_id}")
    print(f"{'='*60}")
    
    # Get input audio files
    audio_files = get_audio_files(session_path)
    if not audio_files:
        print(f"  ✗ No audio files found in {session_path / 'derivatives'}")
        return False
    
    print(f"  Found {len(audio_files)} audio files")
    
    # Check for existing outputs
    if check_existing_outputs(session_path, len(audio_files)) and not force:
        print(f"  ✓ Isolated audio already exists, skipping (use --force to reprocess)")
        return True
    
    # Create processed directory
    processed_dir = session_path / 'processed'
    processed_dir.mkdir(exist_ok=True)
    
    # Check audio lengths match
    lengths = []
    for f in audio_files:
        sr, audio = wavfile.read(f)
        lengths.append(len(audio))
    
    if len(set(lengths)) > 1:
        print(f"  ⚠ Audio files have different lengths: {lengths}")
        print(f"  Padding shorter files to match longest...")
    
    # Run isolation
    print(f"  Isolating with parameters:")
    print(f"    dominance_margin_db: {dominance_margin_db}")
    print(f"    harmonicity_weight: {harmonicity_weight}")
    print(f"    gate_threshold_db: {gate_threshold_db}")
    print(f"    gate_lookahead_ms: {gate_lookahead_ms}")
    print(f"    gate_hold_ms: {gate_hold_ms}")
    
    try:
        isolated_audio = isolate(
            audio_files,
            dominance_margin_db=dominance_margin_db,
            harmonicity_weight=harmonicity_weight,
            gate_threshold_db=gate_threshold_db,
            gate_lookahead_ms=gate_lookahead_ms,
            gate_hold_ms=gate_hold_ms,
            normalize_input=True,
            save_files=False,  # We'll save with custom names
        )
        
        # Get sample rate from first file
        sr, _ = wavfile.read(audio_files[0])
        
        # Save with pipeline-compatible naming
        for i, (audio_file, isolated) in enumerate(zip(audio_files, isolated_audio)):
            # Extract base name: TRACK01_trimmed.wav -> TRACK01_trimmed
            base_name = Path(audio_file).stem
            output_name = f"{base_name}_isolated_v2.wav"
            output_path = processed_dir / output_name
            
            # Convert to appropriate format for saving
            # Scale to int16 range if needed
            if isolated.dtype == np.float32 or isolated.dtype == np.float64:
                # Normalize to prevent clipping
                max_val = np.max(np.abs(isolated))
                if max_val > 0:
                    isolated = isolated / max_val * 0.95
                isolated = (isolated * 32767).astype(np.int16)
            
            wavfile.write(str(output_path), sr, isolated)
            print(f"  ✓ Saved {output_name}")
        
        print(f"  ✓ Isolation complete for {session_id}")
        return True
        
    except Exception as e:
        print(f"  ✗ Isolation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_sessions(base_path: Path) -> list:
    """Find all session directories (those with derivatives/TRACK*.wav files)."""
    sessions = []
    
    # Check if base_path itself is a session
    if get_audio_files(base_path):
        return [base_path]
    
    # Otherwise, look for subdirectories that are sessions
    for subdir in sorted(base_path.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith('.'):
            if get_audio_files(subdir):
                sessions.append(subdir)
    
    return sessions


def main():
    parser = argparse.ArgumentParser(
        description='Isolate audio for group conversation sessions using voicolate'
    )
    parser.add_argument('path', type=str, 
                       help='Path to session or directory containing sessions')
    parser.add_argument('--all', action='store_true',
                       help='Process all sessions in directory')
    parser.add_argument('--force', action='store_true',
                       help='Reprocess even if outputs exist')
    parser.add_argument('--dominance', type=float, default=3.0,
                       help='Dominance margin in dB (default: 3.0, lower = more aggressive)')
    parser.add_argument('--harmonicity', type=float, default=0.5,
                       help='Harmonicity weight 0-1 (default: 0.5, higher = more breath suppression)')
    parser.add_argument('--gate-threshold', type=float, default=-40,
                       help='Gate threshold in dB below peak (default: -40)')
    parser.add_argument('--gate-lookahead', type=float, default=30,
                       help='Gate lookahead in ms (default: 30, preserves onsets)')
    parser.add_argument('--gate-hold', type=float, default=50,
                       help='Gate hold time in ms (default: 50, preserves offsets)')
    
    args = parser.parse_args()
    
    base_path = Path(args.path)
    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}")
        return 1
    
    # Find sessions to process
    if args.all:
        sessions = find_sessions(base_path)
        if not sessions:
            print(f"No sessions found in {base_path}")
            return 1
        print(f"Found {len(sessions)} sessions to process")
    else:
        # Single session
        if get_audio_files(base_path):
            sessions = [base_path]
        else:
            print(f"No audio files found in {base_path / 'derivatives'}")
            return 1
    
    # Process sessions
    success_count = 0
    fail_count = 0
    
    for session_path in sessions:
        success = isolate_session(
            session_path,
            force=args.force,
            dominance_margin_db=args.dominance,
            harmonicity_weight=args.harmonicity,
            gate_threshold_db=args.gate_threshold,
            gate_lookahead_ms=args.gate_lookahead,
            gate_hold_ms=args.gate_hold,
        )
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}")
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    exit(main())
