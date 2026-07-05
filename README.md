<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cozalss/cozalss/main/assets/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cozalss/cozalss/main/assets/banner-light.svg">
  <img alt="Cem Özal — AI agent pipelines · full-stack engineering · TEKNOFEST 2026" width="100%" src="https://raw.githubusercontent.com/cozalss/cozalss/main/assets/banner-dark.svg">
</picture>

<a href="https://github.com/cozalss"><img alt="typing intro" src="https://readme-typing-svg.demolab.com/?lines=Building+AI+agents+for+public+document+workflows;TasnifX+%E2%80%94+TEKNOFEST+2026+AI+Language+Agents;OCR+%C2%B7+RAG+%C2%B7+LangGraph+%C2%B7+deterministic+fallbacks;Kamu+evrak%C4%B1n%C4%B1+okuyan+ve+yazan+ajanlar+%F0%9F%87%B9%F0%9F%87%B7&font=Fira+Code&size=18&color=2F8FA6&background=00000000&center=true&vCenter=true&width=680&height=44&duration=3600&pause=900" /></a>

</div>

Merhaba 👋 I'm **Cem** — a software engineering student who builds agent pipelines that **read, understand and draft official documents**. I care about three unfashionable things: deterministic fallbacks, measurable evals, and calm UIs.

- 🛰️ **Now:** [TasnifX](https://github.com/cozalss/TasnifX-TeknoFest) — intelligent agent support system for public-sector document & correspondence workflows *(TEKNOFEST 2026 · AI Language Agents)*
- 🩺 **Before:** a GDPR-compliant healthcare collaboration platform, and a Java scheduling engine
- 📐 **Rule I code by:** every LLM call gets a deterministic fallback — the demo never dies on stage

## ⚙️ TasnifX — the flagship

Multi-agent pipeline (FastAPI · LangGraph · React · DeepSeek) that takes a raw scanned document and returns a classified, summarized, legally-grounded official reply draft:

```text
evrak.pdf → ocr → sınıflandır → bilgi çıkar → eksik tespit → mevzuat (BM25 RAG) → özet → resmî yazı taslağı → birim yönlendirme
```

Engineering highlights (measured on the project's eval harness, not vibes):

| What | Result | How |
|---|---|---|
| OCR word error rate | **51% → 29%** | LLM post-correction pass over OCR output |
| Legislation Recall@1 | **0.65 → 1.00** | BM25 retrieval + DeepSeek listwise rerank |
| Cost per document | **~$0.001–0.002** | JSON-mode caching + escalation only when uncertain |
| PII | **masked by default** | checksum-valid synthetic TCKNs in all test data |

<div align="center">

## 🧰 Toolbox

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://skillicons.dev/icons?i=python,fastapi,react,vite,js,java,git,githubactions,supabase,vscode&theme=dark&perline=10">
  <source media="(prefers-color-scheme: light)" srcset="https://skillicons.dev/icons?i=python,fastapi,react,vite,js,java,git,githubactions,supabase,vscode&theme=light&perline=10">
  <img alt="Python, FastAPI, React, Vite, JavaScript, Java, Git, GitHub Actions, Supabase, VS Code" src="https://skillicons.dev/icons?i=python,fastapi,react,vite,js,java,git,githubactions,supabase,vscode&theme=dark&perline=10">
</picture>

## 📦 Selected builds

<a href="https://github.com/cozalss/SENG384-project"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG384-project&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7">
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG384-project&hide_border=true&bg_color=00000000&title_color=1f6b7e&icon_color=b8442e&text_color=3a3229">
  <img alt="SENG384-project — GDPR-compliant healthcare platform" src="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG384-project&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7">
</picture></a><a href="https://github.com/cozalss/SENG383-project"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG383-project&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7">
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG383-project&hide_border=true&bg_color=00000000&title_color=1f6b7e&icon_color=b8442e&text_color=3a3229">
  <img alt="SENG383-project — Java scheduling engine" src="https://github-readme-stats.vercel.app/api/pin/?username=cozalss&repo=SENG383-project&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7">
</picture></a>

## 📊 Numbers

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api?username=cozalss&show_icons=true&include_all_commits=true&count_private=true&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7&ring_color=2f8fa6&rank_icon=github">
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api?username=cozalss&show_icons=true&include_all_commits=true&count_private=true&hide_border=true&bg_color=00000000&title_color=1f6b7e&icon_color=b8442e&text_color=3a3229&ring_color=1f6b7e&rank_icon=github">
  <img alt="GitHub stats" height="170" src="https://github-readme-stats.vercel.app/api?username=cozalss&show_icons=true&include_all_commits=true&count_private=true&hide_border=true&bg_color=00000000&title_color=2f8fa6&icon_color=e0563c&text_color=adbac7&ring_color=2f8fa6&rank_icon=github">
</picture><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-readme-stats.vercel.app/api/top-langs/?username=cozalss&layout=compact&langs_count=8&hide_border=true&bg_color=00000000&title_color=2f8fa6&text_color=adbac7">
  <source media="(prefers-color-scheme: light)" srcset="https://github-readme-stats.vercel.app/api/top-langs/?username=cozalss&layout=compact&langs_count=8&hide_border=true&bg_color=00000000&title_color=1f6b7e&text_color=3a3229">
  <img alt="Top languages" height="170" src="https://github-readme-stats.vercel.app/api/top-langs/?username=cozalss&layout=compact&langs_count=8&hide_border=true&bg_color=00000000&title_color=2f8fa6&text_color=adbac7">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://streak-stats.demolab.com/?user=cozalss&hide_border=true&background=00000000&ring=2f8fa6&fire=e0563c&currStreakNum=e8edf2&sideNums=adbac7&currStreakLabel=2f8fa6&sideLabels=8aa3b8&dates=6b7a88&stroke=2b3a49">
  <source media="(prefers-color-scheme: light)" srcset="https://streak-stats.demolab.com/?user=cozalss&hide_border=true&background=00000000&ring=1f6b7e&fire=b8442e&currStreakNum=161616&sideNums=3a3229&currStreakLabel=1f6b7e&sideLabels=6b5d4a&dates=8a7a63&stroke=d9cbb8">
  <img alt="Contribution streak" src="https://streak-stats.demolab.com/?user=cozalss&hide_border=true&background=00000000&ring=2f8fa6&fire=e0563c&currStreakNum=e8edf2&sideNums=adbac7&currStreakLabel=2f8fa6&sideLabels=8aa3b8&dates=6b7a88&stroke=2b3a49">
</picture>

<details>
<summary>🏆 Trophy cabinet</summary>
<br>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github-profile-trophy.vercel.app/?username=cozalss&theme=dark_dimmed&no-bg=true&no-frame=true&column=7&margin-w=8&margin-h=8">
  <source media="(prefers-color-scheme: light)" srcset="https://github-profile-trophy.vercel.app/?username=cozalss&theme=flat&no-bg=true&no-frame=true&column=7&margin-w=8&margin-h=8">
  <img alt="GitHub trophies" src="https://github-profile-trophy.vercel.app/?username=cozalss&theme=dark_dimmed&no-bg=true&no-frame=true&column=7&margin-w=8&margin-h=8">
</picture>
</details>

## 🐍 The contribution graph gets eaten nightly

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/cozalss/cozalss/output/github-snake-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/cozalss/cozalss/output/github-snake.svg">
  <img alt="Snake eating the contribution graph" src="https://raw.githubusercontent.com/cozalss/cozalss/output/github-snake-dark.svg">
</picture>

## 📬 Reach me

<a href="mailto:cannozall@gmail.com"><img alt="Gmail" src="https://img.shields.io/badge/gmail-cannozall%40gmail.com-e0563c?style=for-the-badge&logo=gmail&logoColor=white"></a>
<a href="https://github.com/cozalss?tab=followers"><img alt="Followers" src="https://img.shields.io/github/followers/cozalss?style=for-the-badge&logo=github&color=2f8fa6&labelColor=30363d"></a>
<img alt="Profile views" src="https://komarev.com/ghpvc/?username=cozalss&label=views&color=8e3d66&style=for-the-badge">

<sub>

The header is a **handcrafted animated SVG** (SMIL, no generator — [source](https://github.com/cozalss/cozalss/blob/main/assets/banner-dark.svg)) themed after TasnifX's design tokens.
The snake redraws itself every night via [![snake workflow](https://github.com/cozalss/cozalss/actions/workflows/snake.yml/badge.svg)](https://github.com/cozalss/cozalss/actions/workflows/snake.yml)

</sub>

</div>
