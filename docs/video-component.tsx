import { useCurrentFrame, useVideoConfig, AbsoluteFill, Sequence, spring, interpolate } from "remotion";
import React from "react";

// ── Color Palette ──
const BG = "#060b1a";
const BG_CARD = "#0f1535";
const ACCENT = "#3b82f6";
const ACCENT2 = "#6366f1";
const TEAL = "#2dd4bf";
const TEXT = "#e2e8f0";
const TEXT_DIM = "#94a3b8";
const TEXT_MUTED = "#64748b";

// ── Reusable: Fade-in wrapper ──
function FadeIn({ children, startFrame = 0, duration = 30 }: { children: React.ReactNode; startFrame?: number; duration?: number }) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [startFrame, startFrame + duration], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <div style={{ opacity }}>{children}</div>;
}

// ── Reusable: Slide-up wrapper ──
function SlideUp({ children, startFrame = 0, duration = 30, distance = 30 }: { children: React.ReactNode; startFrame?: number; duration?: number; distance?: number }) {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [startFrame, startFrame + duration], [distance, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [startFrame, startFrame + duration], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <div style={{ opacity, transform: `translateY(${y}px)` }}>{children}</div>;
}

// ── Typewriter text component ──
function Typewriter({ text, startFrame, charDuration = 2 }: { text: string; startFrame: number; charDuration?: number }) {
  const frame = useCurrentFrame();
  const charsShown = Math.floor(interpolate(frame, [startFrame, startFrame + text.length * charDuration], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return <span>{text.slice(0, charsShown)}</span>;
}

// ── Scene 1: Opening Hook (0-15s, frames 0-450) ──
function SceneOpening() {
  const frame = useCurrentFrame();
  const bgOpacity = interpolate(frame, [0, 60], [0, 1]);
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <div style={{ opacity: bgOpacity }}>
        <SlideUp startFrame={40} duration={40}>
          <h1 style={{ color: TEXT_DIM, fontSize: 48, fontWeight: 300, textAlign: "center", marginBottom: 0, letterSpacing: 2 }}>
            一个 SaaS 应用平均有一百多个功能界面
          </h1>
        </SlideUp>
        <SlideUp startFrame={120} duration={40} distance={20}>
          <h1 style={{ color: TEXT_DIM, fontSize: 48, fontWeight: 300, textAlign: "center", letterSpacing: 2 }}>
            用户真正会用的，不超过十五个
          </h1>
        </SlideUp>
        <SlideUp startFrame={240} duration={60} distance={40}>
          <h1 style={{
            background: `linear-gradient(135deg, ${ACCENT}, ${TEAL})`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
            fontSize: 72, fontWeight: 900, textAlign: "center", marginTop: 24, letterSpacing: -1
          }}>
            你的用户，迷失在迷宫里
          </h1>
        </SlideUp>
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 2: Pain Points (15-90s, frames 450-2700) ──
function ScenePain1() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 80 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: `linear-gradient(135deg, ${ACCENT}, ${ACCENT2})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 20, color: "#fff" }}>1</div>
          <h2 style={{ color: TEXT, fontSize: 36, fontWeight: 700, margin: 0 }}>页面即迷宫</h2>
        </div>
      </SlideUp>
      <SlideUp startFrame={30} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 22, lineHeight: 1.7, maxWidth: 800, textAlign: "center" }}>
          用户登录后，面对满屏菜单、表格、筛选条件和操作按钮<br/>不知道从哪里开始
        </p>
      </SlideUp>
      <SlideUp startFrame={90} duration={40}>
        <p style={{ color: TEXT_MUTED, fontSize: 20, lineHeight: 1.7, maxWidth: 800, textAlign: "center", marginTop: 24 }}>
          "批量导入在哪？""这个灰色按钮能点吗？"
        </p>
      </SlideUp>
      <SlideUp startFrame={160} duration={50}>
        <div style={{ marginTop: 40, padding: "28px 40px", border: `1px solid ${ACCENT}44`, borderRadius: 12, background: BG_CARD, maxWidth: 750, textAlign: "center" }}>
          <p style={{ color: TEAL, fontSize: 18, lineHeight: 1.6, margin: 0 }}>
            你的 ERP、WMS 系统部署到客户工厂<br/>工人不看操作手册，天天在客户群里问同样的问题<br/>你不得不扩招客服——系统越重，支撑团队越膨胀
          </p>
        </div>
      </SlideUp>
    </AbsoluteFill>
  );
}

function ScenePain2() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 80 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: `linear-gradient(135deg, ${ACCENT}, ${ACCENT2})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 20, color: "#fff" }}>2</div>
          <h2 style={{ color: TEXT, fontSize: 36, fontWeight: 700, margin: 0 }}>客服在回答同样的问题</h2>
        </div>
      </SlideUp>
      <SlideUp startFrame={40} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 22, lineHeight: 1.7, maxWidth: 800, textAlign: "center" }}>
          "怎么改收货地址？""报表在哪导出？""订单怎么取消？"
        </p>
      </SlideUp>
      <SlideUp startFrame={100} duration={50}>
        <p style={{ color: TEXT_DIM, fontSize: 20, lineHeight: 1.7, maxWidth: 780, textAlign: "center", marginTop: 20 }}>
          这些问题在帮助文档里写得清清楚楚<br/>但没人看文档——他们选择问
        </p>
      </SlideUp>
      <SlideUp startFrame={170} duration={50}>
        <div style={{ marginTop: 40, display: "flex", gap: 24 }}>
          <div style={{ textAlign: "center", padding: "20px 32px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}33` }}>
            <div style={{ fontSize: 48, fontWeight: 900, background: `linear-gradient(135deg, ${ACCENT}, ${TEAL})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>60%</div>
            <div style={{ color: TEXT_MUTED, fontSize: 14, marginTop: 4 }}>客服时间消耗在重复问答</div>
          </div>
          <div style={{ textAlign: "center", padding: "20px 32px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}33` }}>
            <div style={{ fontSize: 48, fontWeight: 900, background: `linear-gradient(135deg, ${ACCENT}, ${TEAL})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>线性</div>
            <div style={{ color: TEXT_MUTED, fontSize: 14, marginTop: 4 }}>客服成本随用户数同步增长</div>
          </div>
        </div>
      </SlideUp>
    </AbsoluteFill>
  );
}

function ScenePain3() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 80 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 32 }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: `linear-gradient(135deg, ${ACCENT}, ${ACCENT2})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 20, color: "#fff" }}>3</div>
          <h2 style={{ color: TEXT, fontSize: 36, fontWeight: 700, margin: 0 }}>AI 落地太难</h2>
        </div>
      </SlideUp>
      <SlideUp startFrame={40} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 20, lineHeight: 1.6, maxWidth: 800, textAlign: "center" }}>
          你知道 AI 能解决这些问题。你研究了市面上的方案：
        </p>
      </SlideUp>
      <SlideUp startFrame={90} duration={50}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 32, width: 700 }}>
          {[
            { title: "对话机器人", desc: '只能聊天，不能操作页面。用户说\u201C帮我导出\u201D，它回复\u201C请点击左上角菜单 \u2192 ...\u201D' },
            { title: "浏览器插件", desc: "让客户装插件？IT 部门反对。而且插件看不到系统内部的业务逻辑" },
            { title: "自建方案", desc: "LangChain、RAG、向量数据库、Agent... 一个团队，两个月起步" }
          ].map((item, i) => (
            <div key={i} style={{ padding: "16px 24px", background: BG_CARD, borderRadius: 8, border: `1px solid ${ACCENT}22`, borderLeft: `3px solid ${ACCENT}` }}>
              <strong style={{ color: TEXT }}>{item.title}</strong>
              <span style={{ color: TEXT_MUTED, marginLeft: 12, fontSize: 15 }}>{item.desc}</span>
            </div>
          ))}
        </div>
      </SlideUp>
      <SlideUp startFrame={200} duration={60}>
        <p style={{ color: TEAL, fontSize: 22, fontWeight: 600, marginTop: 40, textAlign: "center" }}>
          你缺的不是技术能力。你缺的是一个能直接嵌入任何网站<br/>既能回答问题、又能操作页面的外挂式 AI
        </p>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 3: What is VoltaireAI (90-135s, frames 2700-4050) ──
function SceneWhatIs() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <div style={{ textAlign: "center" }}>
        <SlideUp startFrame={0} duration={40}>
          <div style={{ display: "inline-block", padding: "6px 18px", border: `1px solid ${ACCENT}88`, borderRadius: 50, fontSize: 13, fontWeight: 500, color: ACCENT, background: `${ACCENT}15`, letterSpacing: 1, marginBottom: 28 }}>
            INTRODUCING
          </div>
        </SlideUp>
        <SlideUp startFrame={30} duration={50}>
          <h1 style={{
            fontSize: 64, fontWeight: 900, letterSpacing: -1.5, margin: 0,
            background: `linear-gradient(135deg, #fff 0%, #a5c9ff 50%, ${ACCENT} 100%)`,
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text"
          }}>
            VoltaireAI
          </h1>
        </SlideUp>
        <SlideUp startFrame={80} duration={40}>
          <p style={{ color: TEXT_DIM, fontSize: 24, marginTop: 12, fontWeight: 400 }}>
            外挂式 AI 助手
          </p>
        </SlideUp>
        <SlideUp startFrame={130} duration={50}>
          <div style={{ marginTop: 36, padding: "20px 36px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}44`, display: "inline-block" }}>
            <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 22, color: TEAL, background: "none" }}>
              {"<script src=\"...voltaire.js\"></script>"}
            </code>
          </div>
        </SlideUp>
        <SlideUp startFrame={190} duration={50}>
          <p style={{ color: TEXT_MUTED, fontSize: 18, marginTop: 24 }}>
            一行代码，为任何网站注入 AI 驱动的智能助手
          </p>
        </SlideUp>
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 4: Comparison Table (135-165s, frames 4050-4950) ──
function SceneComparison() {
  const frame = useCurrentFrame();
  const rows = [
    { left: "回答预设 FAQ", right: "基于知识库灵活回答" },
    { left: "只能告诉你\"怎么做\"", right: "直接执行 JS 代码操作页面" },
    { left: "需要 SDK 集成", right: "一行 script 标签" },
    { left: "答案靠人工维护", right: "DOM 自动扫描，知识库自增长" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 700, marginBottom: 40 }}>它不只是聊天机器人</h2>
      </SlideUp>
      <div style={{ width: 860 }}>
        <div style={{ display: "flex", padding: "14px 24px", borderRadius: "8px 8px 0 0", background: `${ACCENT}20`, border: `1px solid ${ACCENT}44` }}>
          <span style={{ flex: 1, color: TEXT_MUTED, fontWeight: 600, fontSize: 14, textTransform: "uppercase", letterSpacing: 1 }}>传统聊天机器人</span>
          <span style={{ flex: 1, color: ACCENT, fontWeight: 600, fontSize: 14, textTransform: "uppercase", letterSpacing: 1 }}>VoltaireAI</span>
        </div>
        {rows.map((row, i) => (
          <SlideUp key={i} startFrame={30 + i * 35} duration={25}>
            <div style={{ display: "flex", padding: "16px 24px", border: `1px solid ${ACCENT}22`, borderTop: "none", background: i % 2 === 0 ? BG_CARD : "transparent" }}>
              <span style={{ flex: 1, color: TEXT_DIM, fontSize: 16 }}>{row.left}</span>
              <span style={{ flex: 1, color: TEAL, fontSize: 16, fontWeight: 500 }}>{row.right}</span>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 5: Core Capabilities (165-195s, frames 4950-5850) ──
function SceneCapabilities() {
  const caps = [
    { icon: "01", title: "智能问答", desc: "用户问什么，AI 从知识库中找到答案" },
    { icon: "02", title: "意图识别", desc: '自动判断"问问题"还是"做操作"' },
    { icon: "03", title: "代码生成与执行", desc: "操作请求直接生成 JavaScript 在浏览器中运行" },
    { icon: "04", title: "失败自修复", desc: "代码出错自动回传 LLM，重新生成修正" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 700, marginBottom: 40 }}>四大核心能力</h2>
      </SlideUp>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, width: 860 }}>
        {caps.map((cap, i) => (
          <SlideUp key={i} startFrame={40 + i * 50} duration={30}>
            <div style={{ padding: "24px 28px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}22`, borderTop: `2px solid ${i === 0 ? ACCENT : i === 1 ? ACCENT2 : i === 2 ? TEAL : ACCENT}` }}>
              <div style={{ fontSize: 28, fontWeight: 900, color: ACCENT, opacity: 0.6, marginBottom: 8 }}>{cap.icon}</div>
              <h4 style={{ color: TEXT, fontSize: 18, fontWeight: 700, margin: "0 0 6px" }}>{cap.title}</h4>
              <p style={{ color: TEXT_DIM, fontSize: 14, margin: 0, lineHeight: 1.5 }}>{cap.desc}</p>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 6: Demo Intro (195-210s, frames 5850-6300) ──
function SceneDemoIntro() {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <SlideUp startFrame={0} duration={40}>
        <div style={{ display: "inline-block", padding: "6px 18px", border: `1px solid ${TEAL}88`, borderRadius: 50, fontSize: 13, fontWeight: 500, color: TEAL, background: `${TEAL}15`, letterSpacing: 1, marginBottom: 28 }}>
          LIVE DEMO
        </div>
      </SlideUp>
      <SlideUp startFrame={30} duration={50}>
        <h2 style={{ color: TEXT, fontSize: 36, fontWeight: 800, margin: 0 }}>它到底怎么用？</h2>
      </SlideUp>
      <SlideUp startFrame={80} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 20, marginTop: 16 }}>三个真实的对话场景</p>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 7: Demo QA (210-255s, frames 6300-7650) ──
function SceneDemoQA() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
          <span style={{ padding: "4px 12px", background: `${TEAL}20`, color: TEAL, borderRadius: 50, fontSize: 13, fontWeight: 600 }}>场景 A</span>
          <h3 style={{ color: TEXT, fontSize: 24, fontWeight: 700, margin: 0 }}>智能问答</h3>
        </div>
      </SlideUp>
      <SlideUp startFrame={40} duration={40}>
        <div style={{ background: BG_CARD, border: `1px solid ${ACCENT}33`, borderRadius: 12, padding: "20px 28px", maxWidth: 700, marginBottom: 24 }}>
          <p style={{ color: ACCENT, fontSize: 16, margin: 0, fontWeight: 500 }}>用户：</p>
          <p style={{ color: TEXT, fontSize: 18, margin: "8px 0 0" }}>"这个页面是做什么的？"</p>
        </div>
      </SlideUp>
      <SlideUp startFrame={100} duration={50}>
        <div style={{ background: BG_CARD, border: `1px solid ${TEAL}33`, borderRadius: 12, padding: "20px 28px", maxWidth: 700 }}>
          <p style={{ color: TEAL, fontSize: 16, margin: 0, fontWeight: 500 }}>AI 回复（不到 2 秒）：</p>
          <p style={{ color: TEXT, fontSize: 16, margin: "8px 0 0", lineHeight: 1.6 }}>
            "这是用户管理页面。左侧搜索框可按姓名或邮箱筛选用户，右上角蓝色按钮用于批量导出，表格每行操作列支持编辑和删除。需要帮你执行具体操作吗？"
          </p>
        </div>
      </SlideUp>
      <SlideUp startFrame={180} duration={40}>
        <p style={{ color: TEXT_MUTED, fontSize: 15, marginTop: 32 }}>
          用户追问："帮我导出最近注册的用户。"
        </p>
      </SlideUp>
      <SlideUp startFrame={210} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 18, marginTop: 16 }}>
          AI 自动判断意图为 <span style={{ color: TEAL, fontWeight: 600 }}>operation</span>，开始生成操作步骤...
        </p>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 8: Demo Operation (255-330s, frames 7650-9900) ──
function SceneDemoOperation() {
  const steps = [
    { num: 1, title: "设置时间范围", desc: "在日期筛选框中填入起始日期" },
    { num: 2, title: "筛选数据", desc: "点击筛选按钮，加载符合条件的数据" },
    { num: 3, title: "批量导出", desc: "点击导出按钮，完成数据导出" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
          <span style={{ padding: "4px 12px", background: `${ACCENT}20`, color: ACCENT, borderRadius: 50, fontSize: 13, fontWeight: 600 }}>场景 B</span>
          <h3 style={{ color: TEXT, fontSize: 24, fontWeight: 700, margin: 0 }}>分步操作执行</h3>
        </div>
      </SlideUp>
      <div style={{ display: "flex", flexDirection: "column", gap: 20, width: 760 }}>
        {steps.map((step, i) => (
          <SlideUp key={i} startFrame={40 + i * 80} duration={35}>
            <div style={{ display: "flex", gap: 18, alignItems: "flex-start", padding: "20px 24px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}22` }}>
              <div style={{ width: 36, height: 36, borderRadius: "50%", background: `linear-gradient(135deg, ${ACCENT}, ${ACCENT2})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 16, color: "#fff", flexShrink: 0, marginTop: 2 }}>
                {step.num}
              </div>
              <div>
                <h4 style={{ color: TEXT, fontSize: 17, fontWeight: 600, margin: "0 0 6px" }}>{step.title}</h4>
                <p style={{ color: TEXT_DIM, fontSize: 14, margin: "0 0 10px", lineHeight: 1.5 }}>{step.desc}</p>
                <div style={{ padding: "10px 14px", background: "#080d20", borderRadius: 6, border: `1px solid ${ACCENT}18` }}>
                  <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: TEAL, background: "none" }}>```js-start</code>
                  <div style={{ color: TEXT_DIM, fontSize: 12, marginTop: 4 }}>screen.getByText(...) + fireEvent.click(...)</div>
                  <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: TEAL, background: "none" }}>```js-end</code>
                </div>
              </div>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 9: Auto-fix Demo (330-360s, frames 9900-10800) ──
function SceneAutofix() {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
          <span style={{ padding: "4px 12px", background: `${ACCENT2}20`, color: ACCENT2, borderRadius: 50, fontSize: 13, fontWeight: 600 }}>场景 C</span>
          <h3 style={{ color: TEXT, fontSize: 24, fontWeight: 700, margin: 0 }}>失败自动修复</h3>
        </div>
      </SlideUp>
      <SlideUp startFrame={40} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 18, maxWidth: 750, textAlign: "center", lineHeight: 1.6 }}>
          代码执行失败，控制台报错。前端自动将错误信息发回后端
        </p>
      </SlideUp>
      <SlideUp startFrame={90} duration={50}>
        <div style={{ marginTop: 32, display: "flex", alignItems: "center", gap: 24, maxWidth: 750 }}>
          <div style={{ flex: 1, padding: 20, background: BG_CARD, borderRadius: 12, border: `1px solid #ff444444` }}>
            <p style={{ color: "#ff6b6b", fontSize: 14, fontWeight: 600, margin: 0 }}>Error</p>
            <p style={{ color: TEXT_DIM, fontSize: 14, margin: "6px 0 0" }}>{'找不到"批量导出"按钮'}</p>
          </div>
          <div style={{ color: ACCENT, fontSize: 28 }}>→</div>
          <div style={{ flex: 1, padding: 20, background: BG_CARD, borderRadius: 12, border: `1px solid ${TEAL}44` }}>
            <p style={{ color: TEAL, fontSize: 14, fontWeight: 600, margin: 0 }}>AI 修正</p>
            <p style={{ color: TEXT_DIM, fontSize: 14, margin: "6px 0 0" }}>改用模糊匹配：<br/>content.includes('匯出')</p>
          </div>
          <div style={{ color: ACCENT, fontSize: 28 }}>→</div>
          <div style={{ flex: 1, padding: 20, background: BG_CARD, borderRadius: 12, border: `1px solid "#22c55e44"` }}>
            <p style={{ color: "#22c55e", fontSize: 14, fontWeight: 600, margin: 0 }}>Success ✓</p>
            <p style={{ color: TEXT_DIM, fontSize: 14, margin: "6px 0 0" }}>重新执行成功</p>
          </div>
        </div>
      </SlideUp>
      <SlideUp startFrame={180} duration={40}>
        <p style={{ color: TEXT, fontSize: 20, fontWeight: 600, marginTop: 40, textAlign: "center" }}>
          用户全程只做了一件事：<span style={{ color: TEAL }}>点了执行按钮</span>
        </p>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 10: Tech Features - Agent (360-400s, frames 10800-12000) ──
function SceneTechAgent() {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "inline-block", padding: "6px 18px", border: `1px solid ${ACCENT}88`, borderRadius: 50, fontSize: 13, fontWeight: 500, color: ACCENT, background: `${ACCENT}15`, letterSpacing: 1, marginBottom: 28 }}>
          TECHNICAL DEEP DIVE
        </div>
      </SlideUp>
      <SlideUp startFrame={20} duration={40}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 800, margin: "0 0 8px" }}>配置驱动的 Agent 系统</h2>
      </SlideUp>
      <SlideUp startFrame={50} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 16, maxWidth: 750, textAlign: "center", lineHeight: 1.5, marginBottom: 28 }}>
          所有 AI 行为由 JSON 配置文件驱动。管理后台直接编辑 → 保存 → 热加载，无需重启
        </p>
      </SlideUp>
      <SlideUp startFrame={90} duration={50}>
        <div style={{ padding: "20px 28px", background: "#080d20", borderRadius: 12, border: `1px solid ${ACCENT}33`, fontFamily: "'JetBrains Mono', monospace", fontSize: 13, lineHeight: 1.8, color: "#cdd6f4", width: 700 }}>
          <div><span style={{ color: "#585b70" }}>{'{'}</span></div>
          <div>  <span style={{ color: "#a6e3a1" }}>"id"</span>: <span style={{ color: "#a6e3a1" }}>"operation_agent"</span>,</div>
          <div>  <span style={{ color: "#a6e3a1" }}>"role"</span>: <span style={{ color: "#a6e3a1" }}>"你是网页自动化操作导师..."</span>,</div>
          <div>  <span style={{ color: "#a6e3a1" }}>"rules"</span>: [</div>
          <div>    <span style={{ color: "#a6e3a1" }}>"将复杂操作拆分为多个独立步骤"</span>,</div>
          <div>    <span style={{ color: "#a6e3a1" }}>"禁止使用原生 DOM，必须使用 Testing Library"</span>,</div>
          <div>    <span style={{ color: "#a6e3a1" }}>"每个代码块末尾必须执行可见操作"</span></div>
          <div>  ]</div>
          <div><span style={{ color: "#585b70" }}>{'}'}</span></div>
        </div>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 11: Three Knowledge Bases (400-435s, frames 12000-13050) ──
function SceneKnowledgeBases() {
  const kbs = [
    { name: "站点地图 sitemap", stores: "页面按钮、链接、输入框\nCSS 选择器、坐标、可用操作", source: "DOM 自动扫描\nPlaywright 探索器", role: "让 AI 知道\n\"页面上有什么\"" },
    { name: "操作指引 table", stores: "业务流程步骤序列\n如\"创建订单的 5 个步骤\"", source: "文档上传\n手动录入", role: "让 AI 知道\n\"业务怎么做\"" },
    { name: "文档资料 document", stores: "FAQ、产品说明\n帮助文档", source: "文件上传\n11 种 RAG 优化策略", role: "让 AI 知道\n\"怎么回答问题\"" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 800, margin: "0 0 24px" }}>三类知识库协同</h2>
      </SlideUp>
      <div style={{ display: "flex", gap: 16, width: 880 }}>
        {kbs.map((kb, i) => (
          <SlideUp key={i} startFrame={40 + i * 50} duration={40}>
            <div style={{ flex: 1, padding: "20px", background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}22`, borderTop: `3px solid ${[ACCENT, ACCENT2, TEAL][i]}`, textAlign: "center" }}>
              <h4 style={{ color: TEXT, fontSize: 16, fontWeight: 700, margin: "0 0 12px" }}>{kb.name}</h4>
              <div style={{ color: TEXT_MUTED, fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>存什么</div>
              <p style={{ color: TEXT_DIM, fontSize: 13, lineHeight: 1.6, margin: "0 0 12px", whiteSpace: "pre-line" }}>{kb.stores}</p>
              <div style={{ color: TEXT_MUTED, fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>怎么来</div>
              <p style={{ color: TEXT_DIM, fontSize: 13, lineHeight: 1.6, margin: "0 0 12px", whiteSpace: "pre-line" }}>{kb.source}</p>
              <div style={{ padding: "8px 12px", background: `${[ACCENT, ACCENT2, TEAL][i]}15`, borderRadius: 6 }}>
                <p style={{ color: [ACCENT, ACCENT2, TEAL][i], fontSize: 12, fontWeight: 600, whiteSpace: "pre-line", margin: 0 }}>{kb.role}</p>
              </div>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 12: RAG Strategies (435-465s, frames 13050-13950) ──
function SceneRAG() {
  const strategies = [
    { name: "层次化索引", score: "0.84", desc: "先摘要层，再细节层", highlight: true },
    { name: "融合检索", score: "0.82", desc: "语义搜索 + 关键词双路融合" },
    { name: "知识图谱 RAG", score: "0.78", desc: "实体-关系图结构化检索" },
    { name: "CRAG", score: "0.82", desc: "低相关度自动补充" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 800, margin: "0 0 8px" }}>11 种全自动 RAG 优化策略</h2>
      </SlideUp>
      <SlideUp startFrame={30} duration={30}>
        <p style={{ color: TEXT_DIM, fontSize: 16, marginBottom: 28 }}>LLM 子 Agent 并行处理，无需人工干预</p>
      </SlideUp>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, width: 760 }}>
        {strategies.map((s, i) => (
          <SlideUp key={i} startFrame={60 + i * 50} duration={35}>
            <div style={{ padding: "18px 22px", background: BG_CARD, borderRadius: 10, border: `1px solid ${s.highlight ? TEAL : ACCENT}${s.highlight ? "44" : "22"}`, borderLeft: `3px solid ${s.highlight ? TEAL : ACCENT}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ color: TEXT, fontWeight: 600, fontSize: 15 }}>{s.name}</span>
                <span style={{ color: s.highlight ? TEAL : ACCENT, fontWeight: 700, fontSize: 14 }}>{s.score}</span>
              </div>
              <p style={{ color: TEXT_DIM, fontSize: 13, margin: 0 }}>{s.desc}</p>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 13: Sitemap Explorer (465-490s, frames 13950-14700) ──
function SceneExplorer() {
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <h2 style={{ color: TEXT, fontSize: 32, fontWeight: 800, margin: "0 0 24px" }}>智能站点探索器</h2>
      </SlideUp>
      <SlideUp startFrame={40} duration={50}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, maxWidth: 800, background: BG_CARD, borderRadius: 12, border: `1px solid ${ACCENT}33`, padding: "24px 32px" }}>
          <div style={{ fontSize: 36 }}>🔍</div>
          <div>
            <p style={{ color: TEXT_DIM, fontSize: 16, lineHeight: 1.6, margin: 0 }}>
              浏览器自动打开 → 扫描可交互元素 → <span style={{ color: ACCENT, fontWeight: 600 }}>LLM 判断哪些值得点击</span> → 自动点击 → 新页面加载 → 重新扫描 → 继续探索...
            </p>
          </div>
        </div>
      </SlideUp>
      <SlideUp startFrame={120} duration={50}>
        <div style={{ marginTop: 32, display: "flex", gap: 24 }}>
          {[
            { stat: "SPA 支持", desc: "等待异步加载\n扫描动态内容" },
            { stat: "登录认证", desc: "自动填表 / Cookie\n手动等待模式" },
            { stat: "50 页 · 15 分钟", desc: "全站交互元素\n完成扫描" }
          ].map((item, i) => (
            <div key={i} style={{ textAlign: "center", padding: "20px 24px", background: BG_CARD, borderRadius: 10, border: `1px solid ${ACCENT}22`, width: 200 }}>
              <div style={{ color: ACCENT, fontWeight: 700, fontSize: 15, whiteSpace: "pre-line", lineHeight: 1.5 }}>{item.stat}</div>
              <div style={{ color: TEXT_MUTED, fontSize: 12, marginTop: 6, whiteSpace: "pre-line", lineHeight: 1.4 }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── Scene 14: Installation (490-520s, frames 14700-15600) ──
function SceneInstallation() {
  const steps = [
    { num: "1", cmd: "pip install -r requirements.txt\ncd backend && python main.py", desc: "安装依赖，启动后端" },
    { num: "2", cmd: "<script src=\"...voltaire.js\"></script>", desc: "在目标网站中加一行代码" },
    { num: "3", cmd: "打开 frontend/admin.html", desc: "完善知识库（可选）" }
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", padding: 60 }}>
      <SlideUp startFrame={0} duration={30}>
        <div style={{ display: "inline-block", padding: "6px 18px", border: `1px solid ${TEAL}88`, borderRadius: 50, fontSize: 13, fontWeight: 500, color: TEAL, background: `${TEAL}15`, letterSpacing: 1, marginBottom: 28 }}>
          GET STARTED
        </div>
      </SlideUp>
      <SlideUp startFrame={20} duration={40}>
        <h2 style={{ color: TEXT, fontSize: 36, fontWeight: 800, margin: "0 0 28px" }}>三步部署</h2>
      </SlideUp>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, width: 700 }}>
        {steps.map((step, i) => (
          <SlideUp key={i} startFrame={60 + i * 70} duration={40}>
            <div style={{ display: "flex", gap: 18, alignItems: "center", padding: "16px 24px", background: BG_CARD, borderRadius: 10, border: `1px solid ${ACCENT}22` }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: `linear-gradient(135deg, ${ACCENT}, ${ACCENT2})`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 15, color: "#fff", flexShrink: 0 }}>
                {step.num}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ padding: "8px 12px", background: "#080d20", borderRadius: 6, fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: TEAL, whiteSpace: "pre-line", lineHeight: 1.6 }}>
                  {step.cmd}
                </div>
              </div>
              <span style={{ color: TEXT_DIM, fontSize: 14, whiteSpace: "nowrap" }}>{step.desc}</span>
            </div>
          </SlideUp>
        ))}
      </div>
    </AbsoluteFill>
  );
}

// ── Scene 15: Closing (520-545s, frames 15600-16350) ──
function SceneClosing() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: BG, display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
      <SlideUp startFrame={0} duration={40}>
        <h2 style={{ color: TEXT, fontSize: 40, fontWeight: 800, margin: 0, textAlign: "center" }}>
          一个 AI 助手。一行代码。三种知识库。
        </h2>
      </SlideUp>
      <SlideUp startFrame={60} duration={40}>
        <p style={{ color: TEXT_DIM, fontSize: 22, marginTop: 16 }}>
          在任何网站上，<span style={{ color: TEAL, fontWeight: 600 }}>回答问题</span>，执行操作，教会用户
        </p>
      </SlideUp>
      <SlideUp startFrame={130} duration={60}>
        <div style={{ marginTop: 48, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <p style={{ color: TEXT, fontSize: 18, fontWeight: 600, margin: 0 }}>完全开源 · MIT 协议</p>
          <p style={{ color: TEXT_DIM, fontSize: 15, margin: 0 }}>部署在你自己的服务器上，数据不外泄</p>
          <p style={{ color: TEXT_DIM, fontSize: 15, margin: 0 }}>不按调用次数收费，不限制用户数量</p>
        </div>
      </SlideUp>
      <SlideUp startFrame={200} duration={60}>
        <div style={{ marginTop: 48, textAlign: "center" }}>
          <p style={{ color: ACCENT, fontSize: 18, fontWeight: 600, margin: 0 }}>
            github.com/Rootchmod/VoltaireAI
          </p>
          <p style={{ color: TEXT_MUTED, fontSize: 14, marginTop: 8 }}>
            rootchmod.github.io/VoltaireAI
          </p>
        </div>
      </SlideUp>
      <SlideUp startFrame={270} duration={60}>
        <div style={{ marginTop: 52, padding: "16px 32px", border: `1px solid ${ACCENT}44`, borderRadius: 10, background: BG_CARD }}>
          <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 20, color: TEAL, background: "none" }}>
            {"<script src=\"...voltaire.js\"></script>"}
          </code>
        </div>
      </SlideUp>
    </AbsoluteFill>
  );
}

// ── MAIN COMPOSITION ──
export default function Main() {
  const { fps } = useVideoConfig();

  // Scene timings in seconds → frames
  const t = (s: number) => Math.floor(s * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      {/* Chapter 1: Pain Points */}
      <Sequence from={0} durationInFrames={t(12)} name="opening"><SceneOpening /></Sequence>
      <Sequence from={t(12)} durationInFrames={t(28)} name="pain1"><ScenePain1 /></Sequence>
      <Sequence from={t(40)} durationInFrames={t(21)} name="pain2"><ScenePain2 /></Sequence>
      <Sequence from={t(61)} durationInFrames={t(42)} name="pain3"><ScenePain3 /></Sequence>

      {/* Chapter 2: What is VoltaireAI */}
      <Sequence from={t(103)} durationInFrames={t(23)} name="whatis"><SceneWhatIs /></Sequence>
      <Sequence from={t(126)} durationInFrames={t(31)} name="comparison"><SceneComparison /></Sequence>
      <Sequence from={t(157)} durationInFrames={t(31)} name="capabilities"><SceneCapabilities /></Sequence>

      {/* Chapter 3: Demo */}
      <Sequence from={t(188)} durationInFrames={t(5)} name="demo_intro"><SceneDemoIntro /></Sequence>
      <Sequence from={t(193)} durationInFrames={t(29)} name="demo_qa"><SceneDemoQA /></Sequence>
      <Sequence from={t(222)} durationInFrames={t(27)} name="demo_op"><SceneDemoOperation /></Sequence>
      <Sequence from={t(249)} durationInFrames={t(33)} name="demo_fix"><SceneAutofix /></Sequence>

      {/* Chapter 4: Technical Deep Dive */}
      <Sequence from={t(282)} durationInFrames={t(28)} name="tech_agent"><SceneTechAgent /></Sequence>
      <Sequence from={t(310)} durationInFrames={t(37)} name="tech_kb"><SceneKnowledgeBases /></Sequence>
      <Sequence from={t(347)} durationInFrames={t(44)} name="tech_rag"><SceneRAG /></Sequence>
      <Sequence from={t(391)} durationInFrames={t(28)} name="tech_explorer"><SceneExplorer /></Sequence>

      {/* Chapter 5: Installation */}
      <Sequence from={t(419)} durationInFrames={t(28)} name="install"><SceneInstallation /></Sequence>

      {/* Chapter 6: Closing */}
      <Sequence from={t(447)} durationInFrames={t(25)} name="closing"><SceneClosing /></Sequence>
    </AbsoluteFill>
  );
}
