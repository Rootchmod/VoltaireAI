#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate TTS audio narration for VoltaireAI intro video and merge with video.
Uses VoxCPM TTS service (http://8.155.1.235:7005/) with "阿囧" voice preset.

Workflow:
1. Define scene timing from video-component.tsx
2. Generate TTS audio for each scene's narration
3. Build a timed audio track aligned with scene boundaries
4. Use FFmpeg to mux audio with the rendered video
"""

import os
import sys
import time
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

from gradio_client import Client

# ── Config ──
FPS = 30
OUTPUT_VIDEO = Path("D:/work/外挂式ai/docs/out/voltaire-intro.mp4")
OUTPUT_FINAL = Path("D:/work/外挂式ai/docs/out/voltaire-intro-with-audio.mp4")
AUDIO_DIR = Path("D:/work/外挂式ai/docs/out/tts_audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Scenes timing from video-component.tsx (in seconds)
SCENES = [
    # (start_sec, duration_sec, scene_id, scene_name)
    (0,   18, "opening",      "开场 Hook"),
    (18,  26, "pain1",        "痛点1: 页面即迷宫"),
    (44,  26, "pain2",        "痛点2: 客服重复"),
    (70,  25, "pain3",        "痛点3: AI 落地难"),
    (95,  20, "whatis",       "VoltaireAI 是什么"),
    (115, 25, "comparison",   "对比表格"),
    (140, 25, "capabilities", "四大核心能力"),
    (165, 10, "demo_intro",   "Demo 引入"),
    (175, 30, "demo_qa",      "场景A: 智能问答"),
    (205, 40, "demo_op",      "场景B: 分步操作"),
    (245, 25, "demo_fix",     "场景C: 失败自修复"),
    (270, 28, "tech_agent",   "Agent 配置系统"),
    (298, 28, "tech_kb",      "三类知识库"),
    (326, 24, "tech_rag",     "11 种 RAG 策略"),
    (350, 22, "tech_explorer","站点探索器"),
    (372, 28, "install",      "安装部署"),
    (400, 30, "closing",      "结尾"),
]

# Narration text for each scene (extracted & adapted from video-script.md)
NARRATIONS = {
    "opening": [
        "一个SaaS应用，平均有一百多个功能界面。但用户真正会用的，不超过十五个。",
        "你的用户，迷失在复杂的系统迷宫里。",
    ],
    "pain1": [
        "用户登录之后，面对满屏的菜单、表格、筛选条件、操作按钮，他不知道从哪里开始。",
        "如果你做的是ERP、WMS这类制造业系统，情况更糟。产线上的工人根本不看操作手册，他们在客户群里一遍遍问同样的问题。",
        "你不得不扩招客服。系统越来越重，支撑团队也跟着膨胀。",
        "用户不是不想用，他是真的找不到。",
    ],
    "pain2": [
        "怎么改收货地址？订单怎么取消？报表在哪导出？",
        "这些问题在帮助文档里写得清清楚楚，但没人看文档，他们选择问。",
        "你的客服团队每天百分之六十的精力消耗在重复问答上。业务在增长，客服成本线性爬升。这不是一个可规模化的模式。",
    ],
    "pain3": [
        "你知道AI能解决这个问题。你研究了市面上的方案。",
        "对话机器人只能聊天，不能操作页面。用户说帮我导出，它只会回复请点击左上角菜单。用户听完还是不会。",
        "浏览器插件？让客户装插件，IT部门第一个跳出来反对。而且插件看不到你系统的业务逻辑。",
        "自建方案？LangChain、RAG、向量数据库......一个完整的团队，两个月起步。你算了一下投入产出比，默默关掉了浏览器。",
        "你缺的不是技术能力，你缺的是一个能直接嵌入任何网站、既能回答问题、又能操作页面的外挂式AI。",
    ],
    "whatis": [
        "VoltaireAI。一行script标签，为任何网站注入AI智能助手。",
        "它不只是聊天机器人。它能理解页面结构，基于你的知识库灵活回答。它能直接执行代码，点击按钮、填写表单、跳转页面。",
        "而你只需要一行script标签，不需要改任何现有代码。",
    ],
    "comparison": [
        "传统聊天机器人回答预设FAQ，问什么都绕回那几句。VoltaireAI理解页面结构，回答灵活精准。",
        "传统机器人不能触碰页面，只能告诉你该怎么做。VoltaireAI直接帮你做。",
        "传统方案需要SDK集成，适配各种前端框架。VoltaireAI只需一行标签。",
        "传统答案靠人工逐条维护，越用越僵。VoltaireAI自动扫描DOM，知识库自我增长。",
    ],
    "capabilities": [
        "智能问答：用户问什么，AI从知识库中找到答案，不是模板回复。",
        "意图识别：自动判断用户想问问题还是做操作，走不同的处理管线。",
        "代码生成与执行：操作请求直接生成JavaScript，在用户浏览器里运行。不是截图，不是录屏。",
        "失败自修复：代码跑出错了？错误自动回传AI，重新生成修正代码。用户无需任何操作。",
    ],
    "demo_intro": [
        "我们来看三个真实的对话场景。",
    ],
    "demo_qa": [
        "用户打开对话框，输入：这个页面是做什么的？",
        "AI判断意图为问答类型，从三类知识库中同时检索。",
        "不到两秒，AI回复：这是用户管理页面。你可以通过左侧搜索框按姓名或邮箱筛选用户，右上角蓝色按钮用于批量导出数据。",
        "用户追问：帮我导出最近注册的用户。AI判断意图转为操作类型，开始生成操作计划。",
    ],
    "demo_op": [
        "AI不是回复一段文字，而是给出了结构化的操作步骤。",
        "第一步：设置时间范围。第二步：点击筛选按钮。第三步：点击批量导出。",
        "每一步都有文字说明，告诉用户为什么做这一步。每一步都有独立可执行的代码。",
        "用户只需要逐一点击执行按钮，三步完成，浏览器弹出下载对话框。",
        "用户在操作中学会了操作。",
    ],
    "demo_fix": [
        "但AI的代码不是每次都完美。比如页面按钮实际文字是批量汇出，AI第一次用的是批量导出。",
        "代码执行失败。控制台报错，提示找不到目标元素。",
        "前端自动将错误信息发回后端。AI收到错误上下文后，重新分析，改用模糊匹配策略。",
        "再次执行，成功。用户全程只做了一件事：点了执行按钮。重试、修正、重新执行，AI在背后自动完成。",
    ],
    "tech_agent": [
        "AI的所有行为，如何分类意图、如何生成代码、用什么风格回复，全部由配置文件驱动。没有一行规则是硬编码在代码里的。",
        "管理后台直接编辑，保存即自动热加载。下一次对话立即生效，无需重启服务。",
        "你可以针对不同业务场景定制不同的Agent。ERP系统用一套提示词，电商后台用另一套。比微调模型更灵活、更透明。",
    ],
    "tech_kb": [
        "知识库不是一个大杂烩。它按用途分成三类，各司其职。",
        "站点地图：存储页面上的按钮、链接、输入框，来自DOM自动扫描。让AI知道页面上有什么。",
        "操作指引：存储业务流程的步骤序列，来自文档上传。让AI知道业务流程怎么做。",
        "文档资料：存储FAQ、产品说明、帮助文档。让AI知道怎么回答知识性问题。",
        "核心机制：每次对话，三类知识库同时查询。AI始终知道自己站在哪个页面上，能操作什么元素，业务怎么流转。",
    ],
    "tech_rag": [
        "文档上传不是简单切成片段塞进库。系统内置十一种RAG优化策略，全程自动处理，无需人工干预。",
        "层次化索引：先让AI生成内容摘要，再拆细粒度分块。检索时先匹配摘要层，再定位细节层。精准度远超直接分块。",
        "融合检索：语义搜索和关键词匹配双路并行。知识图谱RAG：从文档中提取实体和关系，构建结构化知识图谱。",
        "每种策略由LLM子Agent并行处理。大文档自动拆分为批次，四个子Agent同时运行。你只负责上传文件，AI完成剩下的一切。",
    ],
    "tech_explorer": [
        "内置Playwright站点探索器。浏览器自动打开目标网站，扫描所有可交互元素。",
        "AI分析哪些按钮和链接值得点击，自动排除注销、删除、提交等危险操作。然后点击，新页面加载，重新扫描。",
        "支持单页应用动态内容，支持三种登录认证模式。一个五十个页面的网站，十五分钟完成全站交互元素扫描。",
    ],
    "install": [
        "部署只需要三步。第一步，启动后端。克隆仓库，安装依赖，配置API密钥，一行命令启动服务。",
        "第二步，在你的网站中加一行script标签。刷新页面，右下角浮动按钮自动出现。完成。",
        "第三步，可选但推荐。打开管理后台，上传帮助文档，运行站点地图生成器，调整Agent提示词。",
    ],
    "closing": [
        "一个AI助手。一行代码。三种知识库。",
        "在任何网站上，回答问题，执行操作，教会用户。",
        "VoltaireAI完全开源，MIT协议。部署在你自己的服务器上，数据不外泄。不按调用次数收费，不限制用户数量。",
        "你的网站值得一个AI助手。不是下个月，不是下周，就是今天。",
    ],
}


def call_tts(text, voice="阿囧"):
    """Call TTS API and return the path to the generated WAV file."""
    client = Client("http://8.155.1.235:7005/")
    result = client.predict(
        text=text,
        selected_voice=voice,
        uploaded_prompt_wav=None,
        prompt_text=None,
        cfg_value=2.0,
        inference_timesteps=10,
        normalize=False,
        denoise=False,
        retry_badcase=True,
        retry_badcase_max_times=3,
        retry_badcase_ratio_threshold=6.0,
        api_name="/tts_non_streaming",
    )
    wav_path = result[0]
    return wav_path


def get_audio_duration(wav_path):
    """Get duration of a WAV file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", wav_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def main():
    print("=" * 60)
    print("VoltaireAI Video TTS Audio Generator")
    print("=" * 60)

    # Phase 1: Generate TTS for each scene
    print("\n[Phase 1] Generating TTS audio for each scene...")

    audio_files = {}  # scene_id -> list of (wav_path, duration)

    for start, duration, scene_id, scene_name in SCENES:
        lines = NARRATIONS.get(scene_id, [])
        if not lines:
            print(f"  [{scene_id}] No narration, skipping")
            continue

        scene_audio_dir = AUDIO_DIR / scene_id
        scene_audio_dir.mkdir(parents=True, exist_ok=True)

        scene_audio_files = []
        for i, line in enumerate(lines):
            # Check cache
            cache_path = scene_audio_dir / f"line_{i:02d}.wav"
            if cache_path.exists():
                dur = get_audio_duration(str(cache_path))
                print(f"  [{scene_id}:{i}] Cached ({dur:.1f}s): {line[:40]}...")
                scene_audio_files.append((str(cache_path), dur))
                continue

            print(f"  [{scene_id}:{i}] Generating: {line[:50]}...")
            try:
                tmp_wav = call_tts(line, "阿囧")
                shutil.copy(tmp_wav, str(cache_path))
                dur = get_audio_duration(str(cache_path))
                print(f"    -> Done ({dur:.1f}s)")
                scene_audio_files.append((str(cache_path), dur))
            except Exception as e:
                print(f"    -> ERROR: {e}")
                # Continue with next line
                continue

            # Small delay to not hammer the server
            time.sleep(0.5)

        audio_files[scene_id] = {
            "files": scene_audio_files,
            "start": start,
            "duration": duration,
            "name": scene_name,
        }

    # Save progress
    manifest = {}
    for scene_id, info in audio_files.items():
        manifest[scene_id] = {
            "start": info["start"],
            "duration": info["duration"],
            "name": info["name"],
            "files": [(path, dur) for path, dur in info["files"]],
        }
    with open(str(AUDIO_DIR / "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Phase 2: Build timed audio using FFmpeg
    print("\n[Phase 2] Building timed audio track...")

    # Calculate total audio duration per scene and compare with scene duration
    # Strategy: play lines sequentially within each scene, pad end if needed
    filter_parts = []
    labels = []
    current_time = 0.0

    for start, duration, scene_id, scene_name in SCENES:
        info = audio_files.get(scene_id)
        scene_end = start + duration

        if not info or not info["files"]:
            # Pad silence for scenes without audio
            filter_parts.append(
                f"aevalsrc=0:d={duration}:s=44100:n=1[pad_{scene_id}]"
            )
            labels.append(f"[pad_{scene_id}]")
            continue

        # Calculate total audio duration for this scene
        scene_files = info["files"]
        total_audio = sum(d[1] for d in scene_files)

        if total_audio > duration:
            # Audio is longer than scene - speed up slightly
            speed_factor = total_audio / duration
            # Cap speedup at 1.3x (faster sounds unnatural)
            speed_factor = min(speed_factor, 1.3)
            print(f"  [{scene_id}] Audio {total_audio:.1f}s > scene {duration}s, "
                  f"speeding up {speed_factor:.2f}x")
        else:
            speed_factor = 1.0

        # Build concat filter for this scene's audio segments
        concat_inputs = []
        for i, (path, dur) in enumerate(scene_files):
            input_label = f"inp_{scene_id}_{i}"
            concat_inputs.append(input_label)
            filter_parts.append(
                f"[{input_label}]atrim=0:{dur}[trim_{scene_id}_{i}]"
            )
            labels.append(f"[trim_{scene_id}_{i}]")

        # Concat all lines in scene
        concat_str = "".join(f"[trim_{scene_id}_{i}]" for i in range(len(scene_files)))
        filter_parts.append(f"{concat_str}concat=n={len(scene_files)}:v=0:a=1[scene_{scene_id}]")

        if speed_factor > 1.0:
            filter_parts.append(
                f"[scene_{scene_id}]atempo={speed_factor}[speed_{scene_id}]"
            )
            final_label = f"[speed_{scene_id}]"
        elif total_audio < duration:
            # Pad with silence to fill scene
            pad_dur = duration - total_audio
            filter_parts.append(
                f"[scene_{scene_id}]adelay=0:all=1,"
                f"apad=pad_dur={pad_dur}[padded_{scene_id}]"
            )
            final_label = f"[padded_{scene_id}]"
        else:
            final_label = f"[scene_{scene_id}]"

        # Add a trim to exactly duration
        filter_parts.append(f"{final_label}atrim=0:{duration}[out_{scene_id}]")
        labels.append(f"[out_{scene_id}]")

    # Concat all scene outputs
    all_scene_labels = "".join(f"[out_{scene_id}]" for _, _, scene_id, _ in SCENES if audio_files.get(scene_id))
    filter_parts.append(f"{all_scene_labels}concat=n={len([s for s in SCENES if audio_files.get(s[2])])}:v=0:a=1[aout]")

    # Simple approach: build in stages
    # First, concatenate all lines within each scene
    scene_audio_map = {}

    for start, duration, scene_id, scene_name in SCENES:
        info = audio_files.get(scene_id)
        if not info or not info["files"]:
            continue

        scene_files = info["files"]
        total_audio = sum(d[1] for d in scene_files)
        scene_audio_path = str(AUDIO_DIR / f"scene_{scene_id}.wav")

        if os.path.exists(scene_audio_path):
            print(f"  [{scene_id}] Scene audio cached: {scene_audio_path}")
            scene_audio_map[scene_id] = scene_audio_path
            continue

        # Concat all lines for this scene
        concat_list_path = str(AUDIO_DIR / f"concat_{scene_id}.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for path, dur in scene_files:
                f.write(f"file '{os.path.abspath(path)}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy", scene_audio_path
        ], capture_output=True)

        # Check duration
        scene_dur = get_audio_duration(scene_audio_path)
        print(f"  [{scene_id}] Concatenated {len(scene_files)} lines -> {scene_dur:.1f}s "
              f"(scene is {duration}s)")

        # Adjust speed if needed
        if scene_dur > duration:
            speed_factor = scene_dur / duration
            speed_factor = min(speed_factor, 1.35)
            adjusted_path = str(AUDIO_DIR / f"scene_{scene_id}_adj.wav")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", scene_audio_path,
                "-filter:a", f"atempo={speed_factor}",
                adjusted_path
            ], capture_output=True)
            shutil.move(adjusted_path, scene_audio_path)
            scene_dur = get_audio_duration(scene_audio_path)
            print(f"    -> Sped up {speed_factor:.2f}x -> {scene_dur:.1f}s")

        scene_audio_map[scene_id] = scene_audio_path

    # Now build the complete timeline with silence padding
    print("\n[Phase 3] Building final audio timeline...")

    # Generate silence for each gap and use FFmpeg concat
    concat_parts = []
    current_pos = 0.0

    for start, duration, scene_id, scene_name in SCENES:
        # Handle gap before this scene
        if start > current_pos:
            gap_dur = start - current_pos
            gap_path = str(AUDIO_DIR / f"gap_{current_pos:.0f}_{start:.0f}.wav")
            if not os.path.exists(gap_path):
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono:d={gap_dur}",
                    "-c:a", "pcm_s16le", gap_path
                ], capture_output=True)
            concat_parts.append(gap_path)
            print(f"  Gap: {current_pos:.0f}s -> {start:.0f}s ({gap_dur:.1f}s silence)")

        # Add scene audio (or silence if no audio)
        if scene_id in scene_audio_map:
            concat_parts.append(scene_audio_map[scene_id])
            scene_dur = get_audio_duration(scene_audio_map[scene_id])
            print(f"  [{scene_id}] {scene_name}: audio {scene_dur:.1f}s / scene {duration}s")
        else:
            # Generate silence for this scene
            sil_path = str(AUDIO_DIR / f"silence_{scene_id}.wav")
            if not os.path.exists(sil_path):
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono:d={duration}",
                    "-c:a", "pcm_s16le", sil_path
                ], capture_output=True)
            concat_parts.append(sil_path)
            print(f"  [{scene_id}] {scene_name}: silence {duration}s")

        current_pos = start + duration

    # Generate concat list
    final_concat_list = str(AUDIO_DIR / "final_concat.txt")
    with open(final_concat_list, "w", encoding="utf-8") as f:
        for path in concat_parts:
            f.write(f"file '{os.path.abspath(path)}'\n")

    final_audio = str(AUDIO_DIR / "final_audio.wav")
    print(f"\n  Concatenating {len(concat_parts)} parts into {final_audio}...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", final_concat_list,
        "-c", "copy", final_audio
    ])

    final_dur = get_audio_duration(final_audio)
    print(f"  Final audio duration: {final_dur:.1f}s")

    # Phase 4: Mux with video
    print(f"\n[Phase 4] Muxing audio with video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(OUTPUT_VIDEO),
        "-i", final_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(OUTPUT_FINAL)
    ])

    print(f"\nDone! Final video: {OUTPUT_FINAL}")
    final_size = OUTPUT_FINAL.stat().st_size / (1024 * 1024)
    print(f"File size: {final_size:.1f} MB")


if __name__ == "__main__":
    main()
