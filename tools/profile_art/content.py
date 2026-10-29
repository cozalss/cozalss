"""Every word that appears inside the artwork lives here, nowhere else."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chip:
    label: str
    accent: str  # teal | plum | coral


@dataclass(frozen=True)
class Pod:
    name: str
    accent: str


@dataclass(frozen=True)
class Hero:
    kicker: str
    name: str
    role: str
    role_short: tuple[str, str]  # two big lines for the phone layout
    motto: str  # typed once
    chips: tuple[Chip, ...]
    pods: tuple[Pod, Pod, Pod]
    status: str
    alt: str


HERO = Hero(
    kicker="whoami",
    name="Cem Özal",
    role="Software engineer · cloud-native & AI agents",
    role_short=("Software engineer", "cloud-native · AI agents"),
    motto="deterministic fallbacks > vibes",
    chips=(
        Chip("Kubernetes · Docker", "teal"),
        Chip("AI agents · RAG", "plum"),
        Chip("FastAPI · React", "coral"),
    ),
    pods=(Pod("yetenek-2.0", "coral"), Pod("adalet-agent", "plum"), Pod("kamu-evrak", "teal")),
    status="3/3 pods Running · 0 dead demos",
    alt="Cem Özal — software engineer, cloud-native and AI agents. Motto: deterministic fallbacks over vibes. "
        "An isometric Kubernetes cluster runs the projects YETENEK 2.0, Adalet Agent and Kamu Evrak as pods.",
)


@dataclass(frozen=True)
class Metric:
    value: str
    label: str
    note: str = ""


@dataclass(frozen=True)
class Card:
    slug: str
    title: str
    accent: str
    context: str
    tag: str
    pitch: str
    metrics: tuple[Metric, Metric, Metric]
    stack: tuple[str, ...]
    url: str
    medal: str = ""  # place number drawn as a medal before `context`

    @property
    def alt(self) -> str:
        facts = "; ".join(f"{m.value} {m.label}{f' ({m.note})' if m.note else ''}" for m in self.metrics)
        return f"{self.title} — {self.context}. {self.pitch} {facts}. Stack: {', '.join(self.stack)}."


# Figures come from each repository's own README (checked 2026-10-29).
CARDS = (
    Card(
        slug="yetenek",
        title="YETENEK 2.0",
        accent="coral",
        medal="2",
        context="2nd place · METU Sports Tech Hackathon 2026",
        tag="public",
        pitch="A phone camera screens kids aged 8–15 for sports talent: MediaPipe scores a "
              "5-minute test, Claude picks 3–5 of 12 sports and flags injury risk.",
        metrics=(Metric("5 min", "test battery"), Metric("12", "sport profiles"),
                 Metric("0", "videos uploaded", "landmarks only")),
        stack=("Next.js", "MediaPipe", "Claude", "Supabase"),
        url="https://github.com/cozalss/YETENEK2.0",
    ),
    Card(
        slug="adalet",
        title="Adalet Agent",
        accent="plum",
        context="Turkish civil law · live demo",
        tag="MIT",
        pitch="Multi-agent legal assistant grounded in the statute: fabricated citations "
              "are dropped, unmatched claims are flagged as unverified.",
        metrics=(Metric("159k", "legal vectors", "8 areas of law"), Metric("84.4%", "correct article", "32 live cases"),
                 Metric("1.8k", "tests", "80% cov. gate")),
        stack=("FastAPI", "LangGraph", "Qdrant", "React"),
        url="https://github.com/cozalss/adalet-agent",
    ),
    Card(
        slug="kamu-evrak",
        title="Kamu Evrak",
        accent="teal",
        context="public-sector paperwork · team TasnifX",
        tag="MIT",
        pitch="Agents read, classify (19 types), check and draft official correspondence for "
              "human sign-off, with a rule-based fallback behind every LLM step.",
        metrics=(Metric("76%", "usable output", "up from 22%"), Metric("~7 s", "per document", "~$0.001 each"),
                 Metric("3.4k", "tests")),
        stack=("FastAPI", "LangGraph", "React", "RapidOCR"),
        url="https://github.com/cozalss/KAMU-EVRAK",
    ),
    Card(
        slug="grid-up",
        title="Grid-Up Datathon",
        accent="coral",
        context="Kaggle · 493 teams · team TasnifX",
        tag="public",
        pitch="Daily electricity-use forecasts for 7,036 distribution transformers, with "
              "separate models for units with and without past data.",
        metrics=(Metric("7,036", "transformers", "forecast daily"), Metric("1.5k", "tests"),
                 Metric("80", "decision records")),
        stack=("Python", "CatBoost", "LightGBM", "XGBoost"),
        url="https://github.com/cozalss/Grid-Up-Datathon---TasnifX",
    ),
)


@dataclass(frozen=True)
class Tool:
    icon: str  # file stem in tools/icons
    label: str


@dataclass(frozen=True)
class Panel:
    slug: str
    title: str
    subtitle: str
    accent: str
    tools: tuple[Tool, ...]  # used in shipped, public work
    learning: tuple[Tool, ...] = ()  # labs and coursework so far
    footnote: str = ""

    @property
    def alt(self) -> str:
        used = f"{self.title} — {self.subtitle}: {', '.join(t.label for t in self.tools)}."
        learning = f" Lab and learning: {', '.join(t.label for t in self.learning)}." if self.learning else ""
        return used + learning + (f" {self.footnote.capitalize()}." if self.footnote else "")


@dataclass(frozen=True)
class Contact:
    slug: str
    label: str
    icon: str
    accent: str
    alt: str
    url: str


CONTACTS = (
    Contact("email", "cemmozal@gmail.com", "gmail", "coral", "Email Cem at cemmozal@gmail.com",
            "mailto:cemmozal@gmail.com"),
    Contact("linkedin", "LinkedIn", "linkedin", "teal", "Cem Özal on LinkedIn",
            "https://www.linkedin.com/in/cem-%C3%B6zal-5b9b2226a"),
)


PANELS = (
    Panel(
        slug="build",
        title="Build",
        subtitle="AI systems & product",
        accent="plum",
        tools=(
            Tool("python", "Python"), Tool("typescript", "TypeScript"), Tool("javascript", "JavaScript"),
            Tool("fastapi", "FastAPI"), Tool("langgraph", "LangGraph"), Tool("qdrant", "Qdrant"),
            Tool("pytorch", "PyTorch"), Tool("mediapipe", "MediaPipe"), Tool("claude", "Claude API"),
            Tool("react", "React"), Tool("nextdotjs", "Next.js"), Tool("vite", "Vite"),
            Tool("tailwindcss", "Tailwind"), Tool("postgresql", "PostgreSQL"), Tool("supabase", "Supabase"),
            Tool("redis", "Redis"), Tool("openjdk", "Java"),
        ),
        footnote="every tool here runs in one of my public repos",
    ),
    Panel(
        slug="ship",
        title="Ship",
        subtitle="cloud, DevOps & quality",
        accent="teal",
        tools=(
            Tool("docker", "Docker"), Tool("githubactions", "GitHub Actions"), Tool("amazonwebservices", "AWS"),
            Tool("terraform", "Terraform"), Tool("linux", "Linux"), Tool("gnubash", "Bash"), Tool("git", "Git"),
            Tool("pytest", "pytest"), Tool("vitest", "Vitest"), Tool("playwright", "Playwright"),
        ),
        learning=(
            Tool("kubernetes", "Kubernetes"), Tool("ansible", "Ansible"), Tool("jenkins", "Jenkins"),
            Tool("gitlab", "GitLab CI"), Tool("azure", "Azure"), Tool("googlecloud", "Google Cloud"),
            Tool("nginx", "Nginx"),
        ),
    ),
)
