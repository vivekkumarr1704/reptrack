from __future__ import annotations
import html
import streamlit as st


def inject_css(theme: str = "dark") -> None:
    bg = "#0b0d12" if theme == "dark" else "#f4f6fa"
    surface = "#141821" if theme == "dark" else "#ffffff"
    surface2 = "#1b202b" if theme == "dark" else "#eef1f6"
    text = "#f4f6fb" if theme == "dark" else "#161b26"
    muted = "#98a2b3" if theme == "dark" else "#667085"
    border = "rgba(255,255,255,.09)" if theme == "dark" else "rgba(16,24,40,.12)"
    st.markdown(f"""
    <style>
    :root {{ --vf-bg:{bg}; --vf-card:{surface}; --vf-card2:{surface2}; --vf-text:{text}; --vf-muted:{muted}; --vf-border:{border}; --vf-lime:#c3f53c; --vf-green:#8dbd27; }}
    html, body, [data-testid="stAppViewContainer"] {{ background:var(--vf-bg); color:var(--vf-text); }}
    [data-testid="stHeader"] {{ background:transparent; }}
    [data-testid="stAppViewContainer"] .main .block-container {{ max-width:1400px; padding-top:1.35rem; padding-bottom:3.5rem; padding-left:clamp(1rem,3vw,2.6rem); padding-right:clamp(1rem,3vw,2.6rem); }}
    [data-testid="stSidebar"] {{ background:var(--vf-card); border-right:1px solid var(--vf-border); }}
    h1,h2,h3,h4 {{ letter-spacing:-.035em; color:var(--vf-text); }}
    p, label, .stMarkdown {{ color:var(--vf-text); }}
    [data-testid="stCaptionContainer"] p {{ color:var(--vf-muted); }}
    .vf-brand {{ display:flex; align-items:center; gap:10px; font-weight:850; letter-spacing:.08em; font-size:1rem; }}
    .vf-brand-mark {{ display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:11px; background:var(--vf-lime); color:#13180a; font-weight:950; font-size:16px; }}
    .vf-chip {{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--vf-border); border-radius:999px; padding:5px 10px; color:var(--vf-muted); font-size:.76rem; white-space:nowrap; }}
    .vf-hero {{ padding:clamp(1.25rem,3vw,2.1rem); border:1px solid var(--vf-border); border-radius:24px; background:radial-gradient(circle at 92% 5%, rgba(195,245,60,.12), transparent 30%), linear-gradient(135deg,var(--vf-card),var(--vf-card2)); margin:.6rem 0 1.2rem 0; }}
    .vf-eyebrow {{ color:var(--vf-lime); font-size:.75rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; margin-bottom:.55rem; }}
    .vf-hero-title {{ font-size:clamp(1.8rem,4.2vw,3rem); font-weight:850; line-height:1.05; letter-spacing:-.055em; margin:0; color:var(--vf-text); }}
    .vf-subtitle {{ color:var(--vf-muted); margin-top:.65rem; font-size:.98rem; }}
    .vf-card {{ background:var(--vf-card); border:1px solid var(--vf-border); border-radius:18px; padding:1rem 1.1rem; height:100%; }}
    .vf-metric-label {{ color:var(--vf-muted); font-size:.78rem; font-weight:650; margin-bottom:.45rem; }}
    .vf-metric-value {{ color:var(--vf-text); font-size:clamp(1.35rem,2.7vw,2.0rem); font-weight:850; letter-spacing:-.05em; line-height:1.1; }}
    .vf-metric-foot {{ color:var(--vf-muted); font-size:.78rem; margin-top:.45rem; }}
    .vf-section-head {{ display:flex; flex-wrap:wrap; align-items:end; justify-content:space-between; gap:10px; margin:1.2rem 0 .75rem; }}
    .vf-section-head h3 {{ margin:0; font-size:1.2rem; }}
    .vf-muted {{ color:var(--vf-muted); }}
    .vf-exercise {{ border:1px solid var(--vf-border); background:var(--vf-card); border-radius:17px; padding:1rem; }}
    .vf-exercise-visual {{ display:flex; align-items:center; justify-content:center; height:88px; border-radius:12px; background:radial-gradient(circle at 60% 30%, rgba(195,245,60,.18), transparent 65%), var(--vf-card2); font-size:2rem; }}
    .vf-pill {{ display:inline-block; background:rgba(195,245,60,.1); color:var(--vf-lime); border:1px solid rgba(195,245,60,.2); padding:4px 9px; border-radius:999px; font-size:.72rem; font-weight:750; margin:2px 4px 2px 0; }}
    .vf-progress-track {{ height:8px; width:100%; background:var(--vf-card2); border-radius:99px; overflow:hidden; }}
    .vf-progress-fill {{ height:100%; background:var(--vf-lime); border-radius:99px; }}
    div.stButton > button {{ border-radius:12px; border:1px solid var(--vf-border); min-height:2.65rem; font-weight:700; transition:all .14s ease; }}
    div.stButton > button[kind="primary"] {{ background:var(--vf-lime); color:#121609; border-color:var(--vf-lime); }}
    div.stButton > button:hover {{ border-color:var(--vf-lime); color:var(--vf-text); }}
    div.stButton > button[kind="primary"]:hover {{ background:#d4ff65; color:#121609; }}
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input, [data-testid="stTextArea"] textarea {{ border-radius:11px; }}
    [data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div {{ border-radius:11px; }}
    [data-testid="stTabs"] button {{ font-weight:750; }}
    [data-testid="stForm"] {{ border:1px solid var(--vf-border); border-radius:16px; padding:1rem; background:color-mix(in srgb, var(--vf-card) 80%, transparent); }}
    .vf-divider {{ height:1px; background:var(--vf-border); margin:1rem 0; }}
    .vf-auth-wrap {{ max-width:560px; margin:2vh auto 0 auto; }}
    .vf-footnote {{ color:var(--vf-muted); font-size:.78rem; line-height:1.5; }}
    @media (max-width: 768px) {{
      [data-testid="stAppViewContainer"] .main .block-container {{ padding-top:.7rem; padding-left:.8rem; padding-right:.8rem; }}
      .vf-hero {{ border-radius:18px; }}
      .vf-card {{ padding:.85rem; }}
      .vf-metric-value {{ font-size:1.25rem; }}
      div.stButton > button {{ min-height:2.7rem; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, foot: str = "", icon: str = "") -> None:
    st.markdown(f"""
    <div class="vf-card">
      <div class="vf-metric-label">{html.escape(icon + '  ' if icon else '')}{html.escape(label)}</div>
      <div class="vf-metric-value">{html.escape(str(value))}</div>
      <div class="vf-metric-foot">{html.escape(foot)}</div>
    </div>
    """, unsafe_allow_html=True)


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="vf-section-head"><div><h3>{html.escape(title)}</h3><div class="vf-muted" style="font-size:.86rem;margin-top:4px">{html.escape(subtitle)}</div></div></div>', unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="vf-hero"><div class="vf-eyebrow">{html.escape(eyebrow)}</div><div class="vf-hero-title">{html.escape(title)}</div><div class="vf-subtitle">{html.escape(subtitle)}</div></div>', unsafe_allow_html=True)
