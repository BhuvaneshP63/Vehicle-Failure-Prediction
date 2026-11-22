"""Shared dashboard heading and CSS-built cutaway rotor."""
import streamlit as st


def heading(title, description):
    if title != "Fleet overview":
        st.header(title, anchor=False, divider="green")
        st.caption(description)
        return
    discs = "".join(f'<i style="--z:{z}px"></i>' for z in range(-80, 81, 8))
    st.html(f"""
    <style>
    .fs-banner {{position:relative;isolation:isolate;overflow:hidden;padding:2.3rem;
      border-radius:20px;background:radial-gradient(ellipse at 80% 70%,#265954,transparent 53%),#102727;
      border:1px solid #41615d;box-shadow:0 6px 0 #0c2121,0 16px 25px #15353022;
      margin-bottom:1rem;color:#f6fffc}}
    .fs-banner h1 {{color:inherit;font:700 clamp(2rem,4vw,3.45rem)/1.06 'Segoe UI',sans-serif;
      letter-spacing:-.045em;margin:0;padding:0}}
    .fs-banner p {{color:#cde3dc;max-width:34rem;margin:.8rem 0 0}}
    .fs-copy {{position:relative;z-index:1;width:65%}}
    .fs-stage {{position:absolute;right:4%;top:50%;width:24%;height:1px;perspective:600px}}
    .fs-shaft {{position:absolute;left:50%;transform-style:preserve-3d;
      transform:rotateX(-16deg) rotateY(-54deg) rotateZ(12deg)}}
    .fs-shaft i {{position:absolute;width:90px;height:90px;left:-45px;top:-45px;border-radius:50%;
      transform:translateZ(var(--z));border:2px solid #a3d3bf;
      background:radial-gradient(circle,#153b39 0 11%,#d7cb86 12% 19%,transparent 20%),
      repeating-conic-gradient(from 20deg,#85b6a4 0deg 8deg,#335d55 10deg 22deg,#193932 24deg 30deg)}}
    .fs-banner:hover .fs-shaft {{transform:rotateX(-22deg) rotateY(-42deg) rotateZ(22deg)}}
    @media(prefers-reduced-motion:no-preference){{.fs-shaft {{transition:transform .65s ease}}}}
    @media(prefers-reduced-motion:reduce){{.fs-banner:hover .fs-shaft {{transform:rotateX(-16deg) rotateY(-54deg) rotateZ(12deg)}}}}
    @media(max-width:640px){{.fs-banner {{padding:1.35rem}} .fs-copy {{width:100%}} .fs-stage {{display:none}}}}
    [data-testid="stMetric"],[data-testid="stForm"] {{background:#fff;border-radius:16px;
      box-shadow:0 3px 0 #dce6df,0 8px 20px #1a37300a}}
    [data-testid="stMainBlockContainer"] {{max-width:1400px;padding-top:3.8rem}}
    [data-testid="stSidebar"] {{border-right:1px solid #cdded7}}
    [data-testid="stSidebar"] [role="radiogroup"] {{gap:.4rem}}
    [data-testid="stSidebar"] [role="radiogroup"] label {{padding:.55rem .75rem;border-radius:9px}}
    [data-testid="stSidebar"] label:has(input:checked) {{background:#cde5db;box-shadow:inset 3px 0 #087f71}}
    [data-testid="stMetric"] {{border-top:3px solid #328679;padding:1rem 1.2rem}}
    [data-testid="stMetricValue"] {{font-variant-numeric:tabular-nums;letter-spacing:-.045em}}
    [data-testid="stTabs"] [role="tablist"] {{gap:.45rem}}
    [data-testid="stTabs"] [role="tab"] {{padding-inline:.85rem}}
    [data-testid="stTabs"] [aria-selected="true"] {{background:#e4f1eb;border-radius:8px 8px 0 0}}
    .fs-banner::before {{content:"";position:absolute;inset:0 0 0 60%;z-index:-1;
      background-image:linear-gradient(#9dd4bf18 1px,transparent 1px),linear-gradient(90deg,#9dd4bf18 1px,transparent 1px);
      background-size:22px 22px;mask-image:linear-gradient(90deg,transparent,#000)}}
    </style>
    <div class="fs-banner"><div class="fs-copy"><h1>{title}</h1><p>{description}</p></div>
    <div class="fs-stage" aria-hidden="true"><div class="fs-shaft">{discs}</div></div></div>
    """)
