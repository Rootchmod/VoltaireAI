#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate TTS audio with "认知便利店" voice, concatenate per scene.
"""

import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from gradio_client import Client

AUDIO_DIR = Path("D:/work/外挂式ai/docs/out/tts_audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "认知便利店"

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


def call_tts(text):
    """Call TTS API and return the path to the generated WAV file."""
    client = Client("http://8.155.1.235:7005/")
    result = client.predict(
        text=text,
        selected_voice=VOICE,
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
    return result[0]


def ffprobe_dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def main():
    print("=" * 60)
    print(f"TTS Generation - Voice: {VOICE}")
    print("=" * 60)

    for scene_id, lines in NARRATIONS.items():
        print(f"\n--- [{scene_id}] {len(lines)} lines ---")

        line_wavs = []
        for i, line in enumerate(lines):
            cache_path = AUDIO_DIR / f"line_{scene_id}_{i:02d}.wav"
            if cache_path.exists():
                dur = ffprobe_dur(str(cache_path))
                print(f"  [{i}] Cached ({dur:.1f}s): {line[:40]}...")
                line_wavs.append((str(cache_path), dur))
                continue

            print(f"  [{i}] Generating: {line[:50]}...")
            try:
                tmp_wav = call_tts(line)
                shutil.copy(tmp_wav, str(cache_path))
                dur = ffprobe_dur(str(cache_path))
                print(f"    -> {dur:.1f}s")
                line_wavs.append((str(cache_path), dur))
            except Exception as e:
                print(f"    -> ERROR: {e}")
                continue

            time.sleep(0.5)

        # Concatenate lines into scene WAV
        scene_wav = AUDIO_DIR / f"scene_{scene_id}.wav"
        total_dur = sum(d for _, d in line_wavs)
        if scene_wav.exists():
            print(f"  Scene WAV cached ({ffprobe_dur(str(scene_wav)):.1f}s)")
            continue

        concat_txt = AUDIO_DIR / f"_concat_{scene_id}.txt"
        with open(str(concat_txt), "w", encoding="utf-8") as f:
            for path, _ in line_wavs:
                f.write(f"file '{os.path.abspath(path).replace(chr(92), '/')}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt), "-c", "copy", str(scene_wav)
        ], capture_output=True)

        dur = ffprobe_dur(str(scene_wav))
        print(f"  -> scene_{scene_id}.wav: {dur:.1f}s (lines sum: {total_dur:.1f}s)")

    print("\nDone! All scene WAVs generated.")
    # Print summary
    print("\nScene durations:")
    for scene_id in NARRATIONS:
        sw = AUDIO_DIR / f"scene_{scene_id}.wav"
        if sw.exists():
            print(f"  {scene_id}: {ffprobe_dur(str(sw)):.1f}s")


if __name__ == "__main__":
    main()
