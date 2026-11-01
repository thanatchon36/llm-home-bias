"""Build the web reader docs/paper/ from paper/paper.tex (same text as the PDF).

Adapted from stablecoin-tbills-genius-act's paper/web.py. A standalone page built by pandoc with paper/reader.html:
masthead, abstract, a results strip whose numbers come from paper/numbers.tex (generated from
output/tables/results.json), contents, numbered sections, citations linked to the references.
The PDF and the PNG figures are copied next to it; GitHub Pages serves the folder. Requires pandoc
on PATH. Usage: python3 paper/web.py
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "docs" / "paper"
REPO_URL = "https://github.com/thanatchon36/llm-home-bias"
PAPER_URL = "https://thanatchon36.github.io/llm-home-bias/"
DATA_URL = f"{REPO_URL}/blob/main/DATASET_CARD.md"

# (label, verdict, css class, finding, detail) with \macro placeholders from numbers.tex.
RESULTS = [
    (
        "H1",
        "not supported",
        "r-null",
        r"A model's home market gets \betaHome pp relative to other models",
        r"95% CI \betaHomeLo to \betaHomeHi; post hoc, allowing for dispersion: \betaPosthocDisp pp",
    ),
    (
        "H2",
        "not supported",
        "r-null",
        r"English prompts, no investor nationality: \betaHtwo pp",
        "12 prompts per model; SE clustered by prompt",
    ),
    (
        "H3",
        "mixed",
        "r-ref",
        r"Thai fine-tunes: OpenThaiGPT \ftOpenthaigptoneFiveSevenb pp, Typhoon2 \ftTyphoontwoEightb pp",
        "Thailand weight vs the base model (Qwen2.5-7B, Llama-3.1-8B), prompt fixed effects",
    ),
    (
        "Investor",
        "larger",
        "r-ref",
        r"Investor's stated residence: \gammaInv pp for that market",
        r"prompt language \lambdaLang pp; \gammaRatio× the pooled home effect",
    ),
    (
        "Cash",
        "USD default",
        "r-ref",
        r"Every model holds cash in USD in \usdCashMin–\usdCashMax% of replies",
        r"home-currency premium \cash pp",
    ),
    (
        "Robustness",
        "no positive tilt",
        "r-null",
        r"Leave-one-model-out β from \lomoMin to \lomoMax pp",
        "pre-registered checks in Table III",
    ),
]


def macros() -> dict[str, str]:
    """numbers.tex values as plain text (one \\newcommand per line)."""
    text = (HERE / "numbers.tex").read_text(encoding="utf-8")
    values = {}
    for m in re.finditer(r"^\\newcommand\{\\(\w+)\}\{(.*)\}$", text, re.MULTILINE):
        v = (
            m.group(2)
            .replace("\\ensuremath{-}", "\u2212")
            .replace("\\%", "%")
            .replace("~", "\u00a0")
        )
        v = re.sub(r"^\$p([=<])(.*)\$$", lambda p: f"p {p.group(1)} {p.group(2)}", v)
        values[m.group(1)] = v
    return values


def expand(text: str, values: dict[str, str]) -> str:
    return re.sub(
        r"\\(\w+)", lambda m: values[m.group(1)], text
    )  # a missing macro fails


def unwrap(tex: str, pattern: str) -> str:
    """Replace `<pattern>{content}` by `content` (brace-matched)."""
    while (m := re.search(pattern, tex)) is not None:
        depth, end = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(tex[end], 0)
            end += 1
        tex = tex[: m.start()] + tex[m.end() : end - 1] + tex[end:]
    return tex


def inline(tex: str) -> str:
    return re.sub(
        r"\\input\{([^}]+)\}",
        lambda m: inline(
            (HERE / (m.group(1).removesuffix(".tex") + ".tex")).read_text("utf-8")
        ),
        tex,
    )


def flatten(tex: str) -> str:
    """Inline \\input files and undo constructs pandoc drops or mangles: `table*` floats, adjustbox,
    \\parbox notes, and IEEEtran's lettered appendices (pandoc would number them 10, 11, ...)."""
    tex = inline(tex)
    tex = tex.replace("\\begin{table*}", "\\begin{table}").replace(
        "\\end{table*}", "\\end{table}"
    )
    tex = re.sub(
        r"\\begin\{adjustbox\}\{[^}]*\}|\\end\{adjustbox\}|\\vspace\{[^}]*\}", "", tex
    )
    tex = unwrap(tex, r"\\parbox\{[^}]*\}\{")
    tex = re.sub(
        r"\\cmidrule(\([a-z]*\))?\{[^}]*\}", "", tex
    )  # pandoc prints "(lr)2-3"
    # pandoc leaves equation references as "[eq:x]": number labelled equations in order.
    for i, label in enumerate(re.findall(r"\\label\{(eq:[^}]+)\}", tex), start=1):
        tex = tex.replace(f"\\label{{{label}}}", f"\\tag{{{i}}}")
        tex = tex.replace(f"\\eqref{{{label}}}", f"({i})").replace(
            f"\\ref{{{label}}}", str(i)
        )
    head, sep, appendix = tex.partition("\\appendices")
    if sep:
        letters = {}
        for i, m in enumerate(
            re.finditer(r"\\section\{([^}]*)\}\\label\{([^}]+)\}", appendix)
        ):
            letters[m.group(2)] = chr(ord("A") + i)
        appendix = re.sub(
            r"\\section\{([^}]*)\}\\label\{([^}]+)\}",
            lambda m: (
                f"\\section*{{Appendix {letters[m.group(2)]}: {m.group(1)}}}\\label{{{m.group(2)}}}"
            ),
            appendix,
        )
        tex = head + appendix
        for label, letter in letters.items():
            tex = tex.replace(f"\\ref{{{label}}}", f"\\hyperref[{label}]{{{letter}}}")
    return tex


def pandoc(tex: str, args: list[str]) -> str:
    tmp = HERE / ".web.tex"
    tmp.write_text(tex, encoding="utf-8")
    try:
        return subprocess.run(
            [
                "pandoc",
                tmp.name,
                "--from=latex",
                "--to=html5",
                "--mathml",
                "--wrap=none",
                *args,
            ],
            cwd=HERE,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    finally:
        tmp.unlink(missing_ok=True)


def doi() -> str | None:
    m = re.search(
        r'^doi:\s*"?([^"\s]+)"?',
        (ROOT / "CITATION.cff").read_text("utf-8"),
        re.MULTILINE,
    )
    return m.group(1) if m else None


def main() -> int:
    main_tex = (HERE / "paper.tex").read_text(encoding="utf-8")
    title = re.search(r"\\title\{(.*?)\}\n", main_tex, re.DOTALL).group(1).strip()
    author = re.search(r"\\IEEEauthorblockN\{(.*?)\}", main_tex).group(1).strip()
    preamble = flatten(main_tex.split("\\begin{document}")[0])
    abstract = (HERE / "sections" / "abstract.tex").read_text(encoding="utf-8")
    abstract = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}", abstract, re.DOTALL
    )
    if abstract is None:
        raise SystemExit("no abstract in sections/abstract.tex")
    abstract_html = pandoc(
        preamble + "\\begin{document}\n" + abstract.group(1) + "\n\\end{document}\n", []
    )
    body = flatten(
        main_tex.replace("\\input{sections/abstract}", "").replace("\\maketitle", "")
    )
    page = pandoc(
        body,
        [
            f"--template={HERE / 'reader.html'}",
            "--standalone",
            "--citeproc",
            "--bibliography=refs.bib",
            "--csl=ieee.csl",  # numbered [n] citations as in the PDF (CSL project, CC BY-SA 3.0)
            "--resource-path=.:sections",
            "--number-sections",
            "--toc",
            "--toc-depth=1",
            f"--metadata=title:{title}",
            f"--metadata=author:{author}",
            "--metadata=pagetitle:LLM home bias",
            (
                "--metadata=description:Pre-registered audit of home-market tilt in equity allocations "
                "from 12 open-weight LLMs of Chinese, American, European, Thai and Korean origin."
            ),
        ],
    )
    page = re.sub(
        r'<(?:embed|img) src="figures/([\w-]+)\.(?:pdf|png)"[^>]*/>',
        r'<img src="figures/\1.png" alt="" />',
        page,
    )
    values = macros()
    items = "\n".join(
        f'<li class="r {cls}"><span class="r-id">{label}</span><span class="r-tag">{tag}</span>'
        f'<span class="r-text">{html.escape(expand(text, values))}'
        f"<small>{html.escape(expand(detail, values))}</small></span></li>"
        for label, tag, cls, text, detail in RESULTS
    )
    meta = (
        f"<b>Pre-registered</b> · {values['nModelsRun']} open-weight models · 240 factorial prompts · "
        f"{values['nObs']} model × prompt × market weights · local inference (Ollama, Q4_K_M)"
    )
    d = doi()
    blob = f"{REPO_URL}/blob/main"
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code</a></li>'
        f'<li><a href="{DATA_URL}">Data</a></li>'
        f'<li><a href="{blob}/docs/PAP.md">Pre-analysis plan</a></li>'
        f'<li><a href="{blob}/docs/FINDINGS.md">Research log</a></li>'
        f'<li><a href="{blob}/docs/SUMMARY_TH.md">สรุปภาษาไทย</a></li>'
    )
    if d:
        actions += f'<li><a href="https://doi.org/{d}">DOI {d}</a></li>'
    bib = (
        "@techreport{chongmankhong2026homebias,\n"
        "  author = {Chongmankhong, Thanatchon},\n"
        f"  title  = {{{title.replace('LLMs', '{LLMs}').replace('Chinese', '{Chinese}').replace('American', '{American}').replace('European', '{European}').replace('Thai', '{Thai}')}}},\n"
        "  year   = {2026},\n"
        "  type   = {Research note},\n"
        + (f"  doi    = {{{d}}},\n" if d else "")
        + f"  url    = {{{PAPER_URL}}}\n"
        "}"
    )
    cite = f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"
    colophon = (
        "<p>Pre-registration, code, analysis and manuscript draft by Claude (Anthropic) under the "
        "author's written brief; the author directed the work and is responsible for the content. "
        "Associations, not causal effects.</p>"
        "<p>Rendered from <code>paper/paper.tex</code> by <code>make paper</code>. Every number "
        "comes from <code>output/tables/results.json</code> through "
        "<code>paper/numbers.tex</code>; the PDF is authoritative.</p>"
    )
    for marker, value in (
        ("<!--ABSTRACT-->", abstract_html),
        ("<!--META-->", meta),
        ("<!--ACTIONS-->", actions),
        (
            "<!--RESULTS-NOTE-->",
            "Pre-registered hypotheses; numbers generated from the results files.",
        ),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", cite),
        ("<!--COLOPHON-->", colophon),
    ):
        if marker not in page:
            raise SystemExit(f"reader.html lacks {marker}")
        page = page.replace(marker, value)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(HERE / "paper.pdf", OUT / "paper.pdf")
    (OUT / "figures").mkdir(exist_ok=True)
    for name in sorted(set(re.findall(r'src="figures/([\w.-]+)"', page))):
        shutil.copyfile(ROOT / "output" / "figures" / name, OUT / "figures" / name)
    print(f"wrote {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
