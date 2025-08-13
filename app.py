# founder_mapper_app.py
import os
import re
import json
import requests
import streamlit as st
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict

# Graph + viz
import networkx as nx
from pyvis.network import Network

# -------------------------------------------------
# App config
# -------------------------------------------------
st.set_page_config(page_title="Founder Network Mapper", layout="wide")
st.title("Founder Network Mapper")
st.caption("Demo mode + USV portfolio, Focus on node, Warm Intro Paths, optional web augmentation")

# =================================================
# DEMO DATA (curated; no paid APIs required)
# =================================================
# Nodes: {id, label, type in {company, founder, investor, partner}, url}
# Edges: {u, v, relation}
DEMO_GRAPH = {
    "nodes": [
        # --- Investor: USV + partners ---
        {"id": "investor::usv", "label": "Union Square Ventures", "type": "investor", "url": "https://www.usv.com/"},
        {"id": "partner::fred_wilson",   "label": "Fred Wilson",   "type": "partner",  "url": "https://www.usv.com/team/fred-wilson/"},
        {"id": "partner::albert_wenger", "label": "Albert Wenger", "type": "partner",  "url": "https://www.usv.com/team/albert-wenger/"},
        {"id": "partner::rebecca_kaden", "label": "Rebecca Kaden", "type": "partner",  "url": "https://www.usv.com/team/rebecca-kaden/"},
        {"id": "partner::nick_grossman", "label": "Nick Grossman", "type": "partner",  "url": "https://www.usv.com/team/nick-grossman/"},
        {"id": "partner::andy_weissman", "label": "Andy Weissman", "type": "partner",  "url": "https://www.usv.com/team/andy-weissman/"},

        # --- USV portfolio (representative) + founders ---
        # Etsy
        {"id": "company::etsy", "label": "Etsy", "type": "company", "url": "https://www.etsy.com/"},
        {"id": "founder::rob_kalin", "label": "Rob Kalin", "type": "founder", "url": "https://en.wikipedia.org/wiki/Etsy"},
        {"id": "founder::chris_maguire", "label": "Chris Maguire", "type": "founder", "url": "https://en.wikipedia.org/wiki/Etsy"},
        {"id": "founder::haim_schoppik", "label": "Haim Schoppik", "type": "founder", "url": "https://en.wikipedia.org/wiki/Etsy"},

        # Twitter (X)
        {"id": "company::twitter", "label": "Twitter (X)", "type": "company", "url": "https://x.com/"},
        {"id": "founder::jack_dorsey", "label": "Jack Dorsey", "type": "founder", "url": "https://en.wikipedia.org/wiki/Jack_Dorsey"},
        {"id": "founder::biz_stone", "label": "Biz Stone", "type": "founder", "url": "https://en.wikipedia.org/wiki/Biz_Stone"},
        {"id": "founder::ev_williams", "label": "Evan Williams", "type": "founder", "url": "https://en.wikipedia.org/wiki/Evan_Williams_(Internet_entrepreneur)"},
        {"id": "founder::noah_glass", "label": "Noah Glass", "type": "founder", "url": "https://en.wikipedia.org/wiki/Noah_Glass"},

        # Coinbase
        {"id": "company::coinbase", "label": "Coinbase", "type": "company", "url": "https://www.coinbase.com/"},
        {"id": "founder::brian_armstrong", "label": "Brian Armstrong", "type": "founder", "url": "https://en.wikipedia.org/wiki/Brian_Armstrong"},
        {"id": "founder::fred_ehrsam", "label": "Fred Ehrsam", "type": "founder", "url": "https://en.wikipedia.org/wiki/Fred_Ehrsam"},

        # Duolingo
        {"id": "company::duolingo", "label": "Duolingo", "type": "company", "url": "https://www.duolingo.com/"},
        {"id": "founder::luis_von_ahn", "label": "Luis von Ahn", "type": "founder", "url": "https://en.wikipedia.org/wiki/Luis_von_Ahn"},
        {"id": "founder::severin_hacker", "label": "Severin Hacker", "type": "founder", "url": "https://en.wikipedia.org/wiki/Severin_Hacker"},

        # Kickstarter
        {"id": "company::kickstarter", "label": "Kickstarter", "type": "company", "url": "https://www.kickstarter.com/"},
        {"id": "founder::perry_chen", "label": "Perry Chen", "type": "founder", "url": "https://en.wikipedia.org/wiki/Kickstarter"},
        {"id": "founder::yancey_strickler", "label": "Yancey Strickler", "type": "founder", "url": "https://en.wikipedia.org/wiki/Yancey_Strickler"},
        {"id": "founder::charles_adler", "label": "Charles Adler", "type": "founder", "url": "https://en.wikipedia.org/wiki/Charles_Adler_(entrepreneur)"},

        # Tumblr
        {"id": "company::tumblr", "label": "Tumblr", "type": "company", "url": "https://www.tumblr.com/"},
        {"id": "founder::david_karp", "label": "David Karp", "type": "founder", "url": "https://en.wikipedia.org/wiki/David_Karp"},

        # Foursquare
        {"id": "company::foursquare", "label": "Foursquare", "type": "company", "url": "https://foursquare.com/"},
        {"id": "founder::dennis_crowley", "label": "Dennis Crowley", "type": "founder", "url": "https://en.wikipedia.org/wiki/Dennis_Crowley"},
        {"id": "founder::naveen_selvadurai", "label": "Naveen Selvadurai", "type": "founder", "url": "https://en.wikipedia.org/wiki/Naveen_Selvadurai"},

        # SoundCloud
        {"id": "company::soundcloud", "label": "SoundCloud", "type": "company", "url": "https://soundcloud.com/"},
        {"id": "founder::alexander_ljung", "label": "Alexander Ljung", "type": "founder", "url": "https://en.wikipedia.org/wiki/SoundCloud"},
        {"id": "founder::eric_wahlforss", "label": "Eric Wahlforss", "type": "founder", "url": "https://en.wikipedia.org/wiki/SoundCloud"},

        # Keep earlier sample investors so the map looks rich
        {"id": "investor::sequoia", "label": "Sequoia Capital", "type": "investor", "url": "https://www.sequoiacap.com/"},
        {"id": "investor::a16z",    "label": "Andreessen Horowitz", "type": "investor", "url": "https://a16z.com/"},
        {"id": "investor::iconiq",  "label": "ICONIQ Capital", "type": "investor", "url": "https://www.iconiqcapital.com/"},
    ],
    "edges": [
        # USV partners -> USV
        {"u": "partner::fred_wilson",    "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::albert_wenger",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::rebecca_kaden",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::nick_grossman",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::andy_weissman",  "v": "investor::usv", "relation": "Partner"},

        # USV -> portfolio
        {"u": "investor::usv", "v": "company::etsy",        "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::twitter",     "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::coinbase",    "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::duolingo",    "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::kickstarter", "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::tumblr",      "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::foursquare",  "relation": "Invested in"},
        {"u": "investor::usv", "v": "company::soundcloud",  "relation": "Invested in"},

        # Companies -> founders
        {"u": "company::etsy",        "v": "founder::rob_kalin",        "relation": "Founded by"},
        {"u": "company::etsy",        "v": "founder::chris_maguire",    "relation": "Founded by"},
        {"u": "company::etsy",        "v": "founder::haim_schoppik",    "relation": "Founded by"},

        {"u": "company::twitter",     "v": "founder::jack_dorsey",      "relation": "Founded by"},
        {"u": "company::twitter",     "v": "founder::biz_stone",        "relation": "Founded by"},
        {"u": "company::twitter",     "v": "founder::ev_williams",      "relation": "Founded by"},
        {"u": "company::twitter",     "v": "founder::noah_glass",       "relation": "Founded by"},

        {"u": "company::coinbase",    "v": "founder::brian_armstrong",  "relation": "Founded by"},
        {"u": "company::coinbase",    "v": "founder::fred_ehrsam",      "relation": "Founded by"},

        {"u": "company::duolingo",    "v": "founder::luis_von_ahn",     "relation": "Founded by"},
        {"u": "company::duolingo",    "v": "founder::severin_hacker",   "relation": "Founded by"},

        {"u": "company::kickstarter", "v": "founder::perry_chen",       "relation": "Founded by"},
        {"u": "company::kickstarter", "v": "founder::yancey_strickler", "relation": "Founded by"},
        {"u": "company::kickstarter", "v": "founder::charles_adler",    "relation": "Founded by"},

        {"u": "company::tumblr",      "v": "founder::david_karp",       "relation": "Founded by"},

        {"u": "company::foursquare",  "v": "founder::dennis_crowley",   "relation": "Founded by"},
        {"u": "company::foursquare",  "v": "founder::naveen_selvadurai","relation": "Founded by"},

        {"u": "company::soundcloud",  "v": "founder::alexander_ljung",  "relation": "Founded by"},
        {"u": "company::soundcloud",  "v": "founder::eric_wahlforss",   "relation": "Founded by"},

        # Sample other investors to keep graph lively (optional)
        {"u": "investor::sequoia", "v": "company::twitter",  "relation": "Investor"},
        {"u": "investor::a16z",    "v": "company::coinbase", "relation": "Investor"},
        {"u": "investor::iconiq",  "v": "company::duolingo", "relation": "Investor"},
    ],
    "sources": {
        "investor::usv": ["https://www.usv.com/team/"],
        "company::etsy": ["https://www.usv.com/portfolio/etsy/", "https://en.wikipedia.org/wiki/Etsy"],
        "company::twitter": ["https://www.usv.com/portfolio/twitter/", "https://en.wikipedia.org/wiki/Twitter"],
        "company::coinbase": ["https://www.usv.com/portfolio/coinbase/", "https://en.wikipedia.org/wiki/Coinbase"],
        "company::duolingo": ["https://www.usv.com/portfolio/duolingo/", "https://en.wikipedia.org/wiki/Duolingo"],
        "company::kickstarter": ["https://www.usv.com/portfolio/kickstarter/", "https://en.wikipedia.org/wiki/Kickstarter"],
        "company::tumblr": ["https://www.usv.com/portfolio/tumblr/", "https://en.wikipedia.org/wiki/Tumblr"],
        "company::foursquare": ["https://www.usv.com/portfolio/foursquare/", "https://en.wikipedia.org/wiki/Foursquare"],
        "company::soundcloud": ["https://www.usv.com/portfolio/soundcloud/", "https://en.wikipedia.org/wiki/SoundCloud"]
    }
}

# =================================================
# Optional Google CSE augmentation (public web only)
# =================================================
@st.cache_data(show_spinner=False, ttl=86400)
def serp(q: str, num: int = 5) -> List[Dict[str, str]]:
    cx = os.getenv("GOOGLE_CSE_ID")
    key = os.getenv("GOOGLE_API_KEY")
    if not cx or not key:
        return []
    num = max(1, min(num, 10))
    resp = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={"q": q, "cx": cx, "key": key, "num": num},
        timeout=15,
    )
    if resp.status_code != 200:
        return [{
            "title": f"Search error {resp.status_code}",
            "snippet": resp.text[:180],
            "link": "https://developers.google.com/custom-search/v1/overview",
        }]
    items = resp.json().get("items") or []
    return [{"title": it.get("title",""),
             "snippet": it.get("snippet",""),
             "link": it.get("link","")} for it in items[:num]]

# =================================================
# Lightweight parsing (heuristics for web augmentation)
# =================================================
VC_KEYWORDS = r"(Capital|Ventures?|Partners?|Fund|Holdings|Management|Investments?)"
LED_BY = re.compile(r"\bled by ([^.;\n]+)", re.I)
INV_LISTY = re.compile(rf"\b([A-Z][\w&'.-]+(?:\s+[A-Z][\w&'.-]+)*)\s+(?:{VC_KEYWORDS})\b", re.I)
FOUNDER_HINTS = re.compile(r"\b(co-?founder|founder|CEO|CTO|CPO|Chief Executive|Chief Technology)\b", re.I)

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def _clean_name(s: str) -> str:
    s = re.sub(r"[\(\)\[\]{}|/]+", " ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    parts = s.split()
    if len(parts) > 5 or len(parts) < 2:
        return ""
    return " ".join(p if p.isupper() and len(p) <= 4 else p.capitalize() for p in parts)

def extract_founders(snips: List[Dict[str, str]]) -> List[Tuple[str,str,str]]:
    found = []
    for hit in snips:
        text = f"{hit.get('title','')} — {hit.get('snippet','')}"
        if not FOUNDER_HINTS.search(text):
            continue
        m = re.findall(r"([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,3})\s+(?:,?\s*)?(?:co-?founder|founder|CEO|CTO|CPO|Chief Executive|Chief Technology)", text)
        for raw in m:
            name = _clean_name(raw)
            if name:
                role = "Founder/Exec"
                role_m = re.search(rf"{re.escape(name)}.*?\b(co-?founder|founder|CEO|CTO|CPO)\b", text, re.I)
                if role_m:
                    role = role_m.group(1).upper()
                found.append((name, role, hit.get("link","")))
    seen = set(); uniq = []
    for n, r, u in found:
        key = (n.lower(), r.lower())
        if key in seen: 
            continue
        seen.add(key); uniq.append((n, r, u))
    return uniq[:12]

def extract_investors(snips: List[Dict[str, str]]) -> List[Tuple[str,str]]:
    invs = []
    for hit in snips:
        text = f"{hit.get('title','')} — {hit.get('snippet','')}"
        led = LED_BY.search(text)
        if led:
            chunk = led.group(1)
            parts = re.split(r"\s+and\s+|,|;|\/", chunk)
            for p in parts:
                p = p.strip()
                if p and re.search(VC_KEYWORDS, p, re.I):
                    invs.append((p, hit.get("link","")))
        for m in INV_LISTY.finditer(text):
            invs.append((m.group(0).strip(), hit.get("link","")))
    seen = set(); uniq=[]
    for n,u in invs:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k); uniq.append((n,u))
    return uniq[:20]

# =================================================
# Graph builders
# =================================================
def build_graph_from_demo() -> Tuple[nx.Graph, Dict[str, Dict[str,Any]], Dict[str, Set[str]]]:
    G = nx.Graph()
    meta: Dict[str, Dict[str,Any]] = {}
    sources_by_node: Dict[str, Set[str]] = defaultdict(set)

    for n in DEMO_GRAPH["nodes"]:
        meta[n["id"]] = {"type": n["type"], "label": n["label"], "url": n.get("url","")}
        G.add_node(n["id"])

    for e in DEMO_GRAPH["edges"]:
        G.add_edge(e["u"], e["v"], relation=e.get("relation",""))

    for nid, urls in (DEMO_GRAPH.get("sources") or {}).items():
        for u in urls:
            sources_by_node[nid].add(u)

    return G, meta, sources_by_node

def build_graph_from_serp(companies: List[str]) -> Tuple[nx.Graph, Dict[str, Dict[str,Any]], Dict[str, Set[str]]]:
    G = nx.Graph()
    meta: Dict[str, Dict[str,Any]] = {}
    sources_by_node: Dict[str, Set[str]] = defaultdict(set)

    for raw_company in companies:
        company = raw_company.strip()
        if not company:
            continue

        founders_hits = serp(f"{company} founders leadership team site:about OR site:team OR founders", 5)
        investors_hits = serp(f"{company} funding investors led by Series round", 5)

        founders = extract_founders(founders_hits)
        investors = extract_investors(investors_hits)

        cid = f"company::{company.lower()}"
        if cid not in meta:
            meta[cid] = {"type":"company","label":company,"url": ""}
            G.add_node(cid)
        for h in founders_hits + investors_hits:
            if h.get("link"):
                sources_by_node[cid].add(h["link"])

        for name, role, url in founders:
            fid = f"founder::{name.lower()}"
            if fid not in meta:
                meta[fid] = {"type":"founder","label":name,"url": url}
                G.add_node(fid)
            G.add_edge(fid, cid, relation=role)
            if url: sources_by_node[fid].add(url)

        for inv, url in investors:
            iid = f"investor::{inv.lower()}"
            if iid not in meta:
                meta[iid] = {"type":"investor","label":inv,"url": url}
                G.add_node(iid)
            G.add_edge(iid, cid, relation="Investor")
            if url: sources_by_node[iid].add(url)

    return G, meta, sources_by_node

# =================================================
# Viz
# =================================================
def render_pyvis(G: nx.Graph, meta: Dict[str, Dict[str,Any]], height: str = "700px",
                 highlight_nodes: Set[str] | None = None, highlight_edges: Set[Tuple[str,str]] | None = None) -> str:
    net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#222")
    net.barnes_hut(spring_length=150, damping=0.85)
    COLORS = {
        "company":"#16a34a",   # green
        "founder":"#2563eb",   # blue
        "investor":"#f97316",  # orange
        "partner":"#7c3aed"    # purple
    }
    for nid, attrs in meta.items():
        if nid not in G:
            continue
        t = attrs["type"]
        label = attrs["label"]
        url = attrs.get("url") or ""
        color = COLORS.get(t, "#64748b")
        title = f"{t.title()}: {label}" + (f"<br><a href='{url}' target='_blank'>{url}</a>" if url else "")
        border = 3 if (highlight_nodes and nid in highlight_nodes) else 1
        net.add_node(nid, label=label, color=color, title=title, borderWidth=border)
    for u, v, d in G.edges(data=True):
        rel = d.get("relation","")
        width = 3 if (highlight_edges and ((u,v) in highlight_edges or (v,u) in highlight_edges)) else 1
        net.add_edge(u, v, title=rel, width=width)
    net.toggle_physics(True)
    return net.generate_html("graph.html")

# =================================================
# Session helpers (prevents “reset to homepage”)
# =================================================
def save_graph_to_session(G, meta, sources):
    st.session_state["_graph"] = G
    st.session_state["_meta"] = meta
    st.session_state["_sources"] = sources
    # Build stable selector labels across reruns
    label_to_id = { f"{meta[n]['label']} ({meta[n]['type']})": n for n in G.nodes() }
    st.session_state["_label_to_id"] = dict(sorted(label_to_id.items(), key=lambda kv: kv[0].lower()))

def load_graph_from_session():
    return (st.session_state.get("_graph"),
            st.session_state.get("_meta"),
            st.session_state.get("_sources"),
            st.session_state.get("_label_to_id"))

# =================================================
# UI – top form builds or rebuilds the graph
# =================================================
with st.form("input"):
    demo_mode = st.checkbox("Use Demo Mode (no web lookups)", value=True)
    companies_raw = st.text_input("Enter up to 5 companies (comma separated)", value="Etsy, Twitter, Coinbase")
    augment = st.checkbox("Augment demo with public web signals (uses your Google CSE quota)", value=False, disabled=not demo_mode)
    submitted = st.form_submit_button("Build / Rebuild network")

if submitted:
    companies = [c.strip() for c in companies_raw.split(",") if c.strip()][:5]
    if not companies:
        st.warning("Please enter at least one company.")
    else:
        with st.spinner("Building graph..."):
            if demo_mode:
                G, meta, sources = build_graph_from_demo()
                # Keep USV + partners always; also keep typed companies and their neighbors
                keep_companies = {f"company::{c.lower()}" for c in companies}
                usv_block = {"investor::usv", "partner::fred_wilson","partner::albert_wenger",
                             "partner::rebecca_kaden","partner::nick_grossman","partner::andy_weissman"}
                to_keep = set(usv_block)
                for nid in G.nodes():
                    if nid in keep_companies or any(nb in keep_companies for nb in G.neighbors(nid)):
                        to_keep.add(nid)
                G = G.subgraph(list(to_keep)).copy()
                meta = {nid: meta[nid] for nid in G.nodes()}
                sources = {nid: set(sources.get(nid, set())) for nid in G.nodes()}
                if augment:
                    G2, meta2, src2 = build_graph_from_serp(companies)
                    for nid, attrs in meta2.items():
                        if nid not in meta:
                            meta[nid] = attrs
                            G.add_node(nid)
                    for u, v, d in G2.edges(data=True):
                        if not G.has_edge(u, v):
                            G.add_edge(u, v, **d)
                    for nid, urls in src2.items():
                        sources.setdefault(nid, set()).update(urls)
            else:
                companies = [c.strip() for c in companies_raw.split(",") if c.strip()][:5]
                G, meta, sources = build_graph_from_serp(companies)

        save_graph_to_session(G, meta, sources)

# If we don’t have a built graph yet, show instructions and exit.
G, META, SOURCES, LABEL2ID = load_graph_from_session()
if G is None or META is None or SOURCES is None or LABEL2ID is None:
    st.info("Build the network first (Demo Mode works instantly). Then use the sidebar to focus on nodes or find warm intro paths.")
    st.stop()

# =================================================
# Sidebar controls (safe across reruns)
# =================================================
st.sidebar.header("Filters")
typ_filter = st.sidebar.multiselect("Node types", ["founder","company","investor","partner"],
                                    default=["founder","company","investor","partner"])
query = st.sidebar.text_input("Search name contains", value="")

st.sidebar.header("Focus")
focus_display = st.sidebar.selectbox("Focus on node", ["(none)"] + list(LABEL2ID.keys()), index=0, key="focus_select")
focus_depth = st.sidebar.slider("Depth (hops)", min_value=1, max_value=2, value=1, key="focus_depth")
apply_focus = st.sidebar.checkbox("Apply focus", value=False, key="apply_focus")

st.sidebar.header("Warm Intro Path")
start_display = st.sidebar.selectbox("From", ["(pick)"] + list(LABEL2ID.keys()), index=0, key="path_from")
end_display   = st.sidebar.selectbox("To",   ["(pick)"] + list(LABEL2ID.keys()), index=0, key="path_to")
find_path = st.sidebar.button("Find shortest path")

# =================================================
# Apply filters/focus safely (no homepage resets)
# =================================================
query_l = (query or "").lower().strip()
visible = []
for nid, attrs in META.items():
    if nid not in G:
        continue
    if attrs["type"] not in typ_filter:
        continue
    if query_l and query_l not in attrs["label"].lower():
        continue
    visible.append(nid)
H = G.subgraph(visible).copy()

if H.number_of_nodes() == 0:
    st.info("No nodes match the current filters. Clear filters or pick another node.")
    st.stop()

highlighted_nodes: Set[str] = set()
highlighted_edges: Set[Tuple[str,str]] = set()

# Focus (ego network)
if apply_focus and focus_display != "(none)":
    fid = LABEL2ID.get(focus_display)
    if fid in H:
        ego_nodes = nx.ego_graph(H, fid, radius=focus_depth).nodes()
        H = H.subgraph(list(ego_nodes)).copy()
        highlighted_nodes = set(H.nodes())
    else:
        st.info("Focused node is not visible under current filters.")

# Warm intro path
path_nodes: List[str] = []
if find_path and start_display != "(pick)" and end_display != "(pick)":
    sid = LABEL2ID.get(start_display)
    tid = LABEL2ID.get(end_display)
    if sid in H and tid in H:
        try:
            path_nodes = nx.shortest_path(H, source=sid, target=tid)
            for u, v in zip(path_nodes, path_nodes[1:]):
                highlighted_edges.add((u, v))
            highlighted_nodes.update(path_nodes)
        except nx.NetworkXNoPath:
            st.warning("No connection found between the selected nodes in the current view.")
    else:
        st.warning("One or both selected nodes are filtered out. Adjust filters or turn off focus.")

# =================================================
# Render graph
# =================================================
html = render_pyvis(H, {nid: META[nid] for nid in H.nodes()},
                    highlight_nodes=highlighted_nodes,
                    highlight_edges=highlighted_edges)
st.components.v1.html(html, height=720, scrolling=True)

# Path explanation
if path_nodes:
    st.markdown("### Warm Intro Path")
    st.write(" → ".join(META[n]["label"] for n in path_nodes))

# Insights
st.markdown("### Insights")
deg = {nid: H.degree(nid) for nid in H.nodes()}
top_nodes = sorted(deg.items(), key=lambda kv: kv[1], reverse=True)[:5]
if top_nodes:
    st.write("Most connected in this view:")
    for nid, d in top_nodes:
        st.write(f"- {META[nid]['label']} ({META[nid]['type']}) — {d} connections")

# Sources
st.markdown("### Sources")
for nid in H.nodes():
    urls = sorted(list(SOURCES.get(nid, [])))
    if not urls:
        continue
    label = META[nid]["label"]
    ntype = META[nid]["type"]
    st.markdown(f"**{label}**  <sub>`{ntype}`</sub>", unsafe_allow_html=True)
    for u in urls:
        st.write(f"- [{urlparse(u).netloc}]({u})")

# Export JSON
payload = {
    "nodes": {nid: {"label": META[nid]["label"], "type": META[nid]["type"], "url": META[nid].get("url","")}
              for nid in H.nodes()},
    "edges": [{"u": u, "v": v, "relation": G.get_edge_data(u,v).get("relation","")} for u,v in H.edges()],
    "sources": {nid: sorted(list(SOURCES.get(nid, []))) for nid in H.nodes()},
}
st.download_button("Download graph JSON", json.dumps(payload, indent=2), file_name="founder_network.json", use_container_width=True)

st.caption("Note: Demo mode uses curated data. Web augmentation uses public SERP heuristics; verify before use.")
