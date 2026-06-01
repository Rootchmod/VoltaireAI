#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rebuild audio timeline for new scene durations and mux with video."""

import subprocess
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDIO_DIR = Path(__file__).parent / "out" / "tts_audio"
VIDEO_IN = Path(__file__).parent / "out" / "voltaire-intro.mp4"
VIDEO_OUT = Path(__file__).parent / "out" / "voltaire-intro-with-audio.mp4"

scenes = [
    (0,   12, "opening"),
    (12,  28, "pain1"),
    (40,  21, "pain2"),
    (61,  42, "pain3"),
    (103, 23, "whatis"),
    (126, 31, "comparison"),
    (157, 31, "capabilities"),
    (188, 5,  "demo_intro"),
    (193, 29, "demo_qa"),
    (222, 27, "demo_op"),
    (249, 33, "demo_fix"),
    (282, 28, "tech_agent"),
    (310, 37, "tech_kb"),
    (347, 44, "tech_rag"),
    (391, 28, "tech_explorer"),
    (419, 28, "install"),
    (447, 25, "closing"),
]

def ffprobe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def build_silence(dur, path):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono:d={dur}",
                    "-c:a", "pcm_s16le", str(path)],
                   capture_output=True)

def main():
    concat_entries = []
    current_pos = 0.0

    for start, duration, scene_id in scenes:
        # Handle gap before scene
        if start > current_pos + 0.01:
            gap_dur = start - current_pos
            gap_path = AUDIO_DIR / f"gap_{current_pos:.0f}_{start:.0f}.wav"
            if not gap_path.exists():
                build_silence(gap_dur, str(gap_path))
            concat_entries.append(str(gap_path))
            print(f"  Gap: {current_pos:.1f}s -> {start:.1f}s ({gap_dur:.1f}s silence)")
            current_pos = start

        scene_wav = AUDIO_DIR / f"scene_{scene_id}.wav"

        if scene_wav.exists():
            audio_dur = ffprobe_dur(str(scene_wav))
            trim_path = AUDIO_DIR / f"t_{scene_id}.wav"

            if not trim_path.exists():
                if audio_dur > duration:
                    # Trim
                    subprocess.run(["ffmpeg", "-y", "-i", str(scene_wav),
                                    "-af", f"atrim=0:{duration}",
                                    "-c:a", "pcm_s16le", str(trim_path)],
                                   capture_output=True)
                else:
                    # Pad with silence
                    pad_dur = duration - audio_dur
                    subprocess.run(["ffmpeg", "-y", "-i", str(scene_wav),
                                    "-af", f"apad=pad_dur={pad_dur}",
                                    "-c:a", "pcm_s16le", str(trim_path)],
                                   capture_output=True)

            actual = ffprobe_dur(str(trim_path))
            print(f"  [{scene_id}] {start}s-{start+duration}s: raw={audio_dur:.1f}s -> {actual:.1f}s")
            concat_entries.append(str(trim_path))
        else:
            sil_path = AUDIO_DIR / f"sil_{scene_id}.wav"
            if not sil_path.exists():
                build_silence(duration, str(sil_path))
            concat_entries.append(str(sil_path))
            print(f"  [{scene_id}] {start}s-{start+duration}s: silence {duration}s")

        current_pos = start + duration

    # Write concat list with ASCII-safe absolute paths
    concat_txt = AUDIO_DIR / "timeline3.txt"
    with open(str(concat_txt), "w", encoding="utf-8") as f:
        for p in concat_entries:
            abs_path = os.path.abspath(p).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    print(f"\n  Concat list: {concat_txt} ({len(concat_entries)} entries)")

    final_wav = AUDIO_DIR / "final_472s.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat_txt), "-c", "copy", str(final_wav)])

    final_dur = ffprobe_dur(str(final_wav))
    target = scenes[-1][0] + scenes[-1][1]
    print(f"  Final audio: {final_dur:.1f}s (target: {target}s)")

    # Mux
    print(f"\n  Muxing with video...")
    subprocess.run(["ffmpeg", "-y",
                    "-i", str(VIDEO_IN),
                    "-i", str(final_wav),
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    str(VIDEO_OUT)])

    size_mb = os.path.getsize(str(VIDEO_OUT)) / (1024 * 1024)
    print(f"\n  Done! {VIDEO_OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
