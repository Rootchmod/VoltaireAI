#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix audio timing: trim each scene's audio to exact scene duration,
build a proper timed audio track, and re-mux with video.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_VIDEO = Path("D:/work/外挂式ai/docs/out/voltaire-intro.mp4")
AUDIO_DIR = Path("D:/work/外挂式ai/docs/out/tts_audio")
FINAL_AUDIO = AUDIO_DIR / "final_audio_trimmed.wav"
OUTPUT_FINAL = Path("D:/work/外挂式ai/docs/out/voltaire-intro-with-audio.mp4")

# Scene timing (start_sec, duration_sec, scene_id)
SCENES = [
    (0,   18, "opening"),
    (18,  26, "pain1"),
    (44,  26, "pain2"),
    (70,  25, "pain3"),
    (95,  20, "whatis"),
    (115, 25, "comparison"),
    (140, 25, "capabilities"),
    (165, 10, "demo_intro"),
    (175, 30, "demo_qa"),
    (205, 40, "demo_op"),
    (245, 25, "demo_fix"),
    (270, 28, "tech_agent"),
    (298, 28, "tech_kb"),
    (326, 24, "tech_rag"),
    (350, 22, "tech_explorer"),
    (372, 28, "install"),
    (400, 30, "closing"),
]

def get_audio_duration(wav_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def build_silence(duration_sec, output_path):
    """Generate a WAV silence file of exact duration."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono:d={duration_sec}",
        "-c:a", "pcm_s16le", str(output_path)
    ], capture_output=True)
    return output_path

def main():
    print("=" * 60)
    print("Fix Audio Timing")
    print("=" * 60)

    # Step 1: Trim each scene audio to exact duration
    print("\n[Step 1] Trimming scene audio to exact durations...")
    trimmed_parts = []

    for start, duration, scene_id in SCENES:
        scene_wav = AUDIO_DIR / f"scene_{scene_id}.wav"

        if scene_wav.exists():
            audio_dur = get_audio_duration(str(scene_wav))
            trim_path = AUDIO_DIR / f"scene_{scene_id}_trim.wav"

            if not trim_path.exists():
                # Trim to exact scene duration (pad with silence if shorter, cut if longer)
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", str(scene_wav),
                    "-af", f"atrim=0:{duration}",
                    "-c:a", "pcm_s16le", str(trim_path)
                ], capture_output=True)

            actual = get_audio_duration(str(trim_path))
            print(f"  [{scene_id}] {audio_dur:.1f}s -> trimmed to {actual:.1f}s (scene: {duration}s)")
            trimmed_parts.append((start, duration, scene_id, str(trim_path)))
        else:
            # No audio for this scene - use silence
            sil_path = AUDIO_DIR / f"sil_{scene_id}.wav"
            if not sil_path.exists():
                build_silence(duration, str(sil_path))
            print(f"  [{scene_id}] no audio -> {duration}s silence")
            trimmed_parts.append((start, duration, scene_id, str(sil_path)))

    # Step 2: Build timeline with precise gap handling
    print("\n[Step 2] Building precise timeline...")
    concat_list_path = str(AUDIO_DIR / "timeline_concat.txt")
    concat_entries = []
    current_pos = 0.0

    for start, duration, scene_id, audio_path in trimmed_parts:
        # Fill gap before this scene
        if start > current_pos + 0.01:
            gap_dur = start - current_pos
            gap_path = str(AUDIO_DIR / f"gap_{current_pos:.0f}_{start:.0f}.wav")
            if not os.path.exists(gap_path):
                build_silence(gap_dur, gap_path)
            concat_entries.append(gap_path)
            print(f"  Gap: {current_pos:.2f}s -> {start:.2f}s ({gap_dur:.2f}s silence)")
            current_pos = start

        # Add trimmed scene audio
        concat_entries.append(audio_path)
        actual_dur = get_audio_duration(audio_path)
        print(f"  [{scene_id}] {start}s-{start+duration}s (audio: {actual_dur:.2f}s)")
        current_pos = start + duration

    # Write concat list
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for path in concat_entries:
            f.write(f"file '{os.path.abspath(path)}'\n")

    print(f"\n  Total entries: {len(concat_entries)}")
    print(f"  Concatenating to: {FINAL_AUDIO}")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy", str(FINAL_AUDIO)
    ])

    final_dur = get_audio_duration(str(FINAL_AUDIO))
    print(f"  Final audio: {final_dur:.2f}s (target: {SCENES[-1][0] + SCENES[-1][1]}s)")

    # Step 3: Re-mux with video
    print(f"\n[Step 3] Muxing with video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(OUTPUT_VIDEO),
        "-i", str(FINAL_AUDIO),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(OUTPUT_FINAL)
    ])

    final_size = OUTPUT_FINAL.stat().st_size / (1024 * 1024)
    print(f"\nDone! {OUTPUT_FINAL}")
    print(f"File size: {final_size:.1f} MB")


if __name__ == "__main__":
    main()
