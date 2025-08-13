# founder_mapper_app.py
import os, re, json, requests, streamlit as st
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict

import networkx as nx
from pyvis.network import Network

# ---------------- App config ----------------
st.set_page_config(page_title="Founder Network Mapper", layout="wide")
st.title("Founder Network Mapper")
st.caption("Demo mode with USV network, reliable Focus by hops, Node Inspector, shared-investor insights, warm-intro paths.")

# =================================================
# DEMO DATA (USV + partners + representative portfolio)
# =================================================
DEMO_GRAPH = {
    "nodes": [
        {"id":"investor::usv","label":"Union Square Ventures","type":"investor","url":"https://www.usv.com/"},
        {"id":"partner::fred_wilson","label":"Fred Wilson","type":"partner","url":"https://www.usv.com/team/fred-wilson/"},
        {"id":"partner::albert_wenger","label":"Albert Wenger","type":"partner","url":"https://www.usv.com/team/albert-wenger/"},
        {"id":"partner::rebecca_kaden","label":"Rebecca Kaden","type":"partner","url":"https://www.usv.com/team/rebecca-kaden/"},
        {"id":"partner::nick_grossman","label":"Nick Grossman","type":"partner","url":"https://www.usv.com/team/nick-grossman/"},
        {"id":"partner::andy_weissman","label":"Andy Weissman","type":"partner","url":"https://www.usv.com/team/andy-weissman/"},
        # Portfolio + founders
        {"id":"company::etsy","label":"Etsy","type":"company","url":"https://www.etsy.com/"},
        {"id":"founder::rob_kalin","label":"Rob Kalin","type":"founder","url":"https://en.wikipedia.org/wiki/Etsy"},
        {"id":"founder::chris_maguire","label":"Chris Maguire","type":"founder","url":"https://en.wikipedia.org/wiki/Etsy"},
        {"id":"founder::haim_schoppik","label":"Haim Schoppik","type":"founder","url":"https://en.wikipedia.org/wiki/Etsy"},

        {"id":"company::twitter","label":"Twitter (X)","type":"company","url":"https://x.com/"},
        {"id":"founder::jack_dorsey","label":"Jack Dorsey","type":"founder","url":"https://en.wikipedia.org/wiki/Jack_Dorsey"},
        {"id":"founder::biz_stone","label":"Biz Stone","type":"founder","url":"https://en.wikipedia.org/wiki/Biz_Stone"},
        {"id":"founder::ev_williams","label":"Evan Williams","type":"founder","url":"https://en.wikipedia.org/wiki/Evan_Williams_(Internet_entrepreneur)"},
        {"id":"founder::noah_glass","label":"Noah Glass","type":"founder","url":"https://en.wikipedia.org/wiki/Noah_Glass"},

        {"id":"company::coinbase","label":"Coinbase","type":"company","url":"https://www.coinbase.com/"},
        {"id":"founder::brian_armstrong","label":"Brian Armstrong","type":"founder","url":"https://en.wikipedia.org/wiki/Brian_Armstrong"},
        {"id":"founder::fred_ehrsam","label":"Fred Ehrsam","type":"founder","url":"https://en.wikipedia.org/wiki/Fred_Ehrsam"},

        {"id":"company::duolingo","label":"Duolingo","type":"company","url":"https://www.duolingo.com/"},
        {"id":"founder::luis_von_ahn","label":"Luis von Ahn","type":"founder","url":"https://en.wikipedia.org/wiki/Luis_von_Ahn"},
        {"id":"founder::severin_hacker","label":"Severin Hacker","type":"founder","url":"https://en.wikipedia.org/wiki/Severin_Hacker"},

        {"id":"company::kickstarter","label":"Kickstarter","type":"company","url":"https://www.kickstarter.com/"},
        {"id":"founder::perry_chen","label":"Perry Chen","type":"founder","url":"https://en.wikipedia.org/wiki/Kickstarter"},
        {"id":"founder::yancey_strickler","label":"Yancey Strickler","type":"founder","url":"https://en.wikipedia.org/wiki/Yancey_Strickler"},
        {"id":"founder::charles_adler","label":"Charles Adler","type":"founder","url":"https://en.wikipedia.org/wiki/Charles_Adler_(entrepreneur)"},

        {"id":"company::tumblr","label":"Tumblr","type":"company","url":"https://www.tumblr.com/"},
        {"id":"founder::david_karp","label":"David Karp","type":"founder","url":"https://en.wikipedia.org/wiki/David_Karp"},

        {"id":"company::foursquare","label":"Foursquare","type":"company","url":"https://foursquare.com/"},
        {"id":"founder::dennis_crowley","label":"Dennis Crowley","type":"founder","url":"https://en.wikipedia.org/wiki/Dennis_Crowley"},
        {"id":"founder::naveen_selvadurai","label":"Naveen Selvadurai","type":"founder","url":"https://en.wikipedia.org/wiki/Naveen_Selvadurai"},

        {"id":"company::soundcloud","label":"SoundCloud","type":"company","url":"https://soundcloud.com/"},
        {"id":"founder::alexander_ljung","label":"Alexander Ljung","type":"founder","url":"https://en.wikipedia.org/wiki/SoundCloud"},
        {"id":"founder::eric_wahlforss","label":"Eric Wahlforss","type":"founder","url":"https://en.wikipedia.org/wiki/SoundCloud"},

        # extra investors for density
        {"id":"investor::sequoia","label":"Sequoia Capital","type":"investor","url":"https://www.sequoiacap.com/"},
        {"id":"investor::a16z","label":"Andreessen Horowitz","type":"investor","url":"https://a16z.com/"},
        {"id":"investor::iconiq","label":"ICONIQ Capital","type":"investor","url":"https://www.iconiqcapital.com/"},
    ],
    "edges": [
        {"u":"partner::fred_wilson","v":"investor::usv","relation":"Partner"},
        {"u":"partner::albert_wenger","v":"investor::usv","relation":"Partner"},
        {"u":"partner::rebecca_kaden","v":"investor::usv","relation":"Partner"},
        {"u":"partner::nick_grossman","v":"investor::usv","relation":"Partner"},
        {"u":"partner::andy_weissman","v":"investor::usv","relation":"Partner"},

        {"u":"investor::usv","v":"company::etsy","relation":"Invested in"},
        {"u":"investor::usv","v":"company::twitter","relation":"Invested in"},
        {"u":"investor::usv","v":"company::coinbase","relation":"Invested in"},
        {"u":"investor::usv","v":"company::duolingo","relation":"Invested in"},
        {"u":"investor::usv","v":"company::kickstarter","relation":"Invested in"},
        {"u":"investor::usv","v":"company::tumblr","relation":"Invested in"},
        {"u":"investor::usv","v":"company::foursquare","relation":"Invested in"},
        {"u":"investor::usv","v":"company::soundcloud","relation":"Invested in"},

        {"u":"company::etsy","v":"founder::rob_kalin","relation":"Founded by"},
        {"u":"company::etsy","v":"founder::chris_maguire","relation":"Founded by"},
        {"u":"company::etsy","v":"founder::haim_schoppik","relation":"Founded by"},

        {"u":"company::twitter","v":"founder::jack_dorsey","relation":"Founded by"},
        {"u":"company::twitter","v":"founder::biz_stone","relation":"Founded by"},
        {"u":"company::twitter","v":"founder::ev_williams","relation":"Founded by"},
        {"u":"company::twitter","v":"founder::noah_glass","relation":"Founded by"},

        {"u":"company::coinbase","v":"founder::brian_armstrong","relation":"Founded by"},
        {"u":"company::coinbase","v":"founder::fred_ehrsam","relation":"Founded by"},

        {"u":"company::duolingo","v":"founder::luis_von_ahn","relation":"Founded by"},
        {"u":"company::duolingo","v":"founder::severin_hacker","relation":"Founded by"},

        {"u":"company::kickstarter","v":"founder::perry_chen","relation":"Founded by"},
        {"u":"company::kickstarter","v":"founder::yancey_strickler","relation":"Founded by"},
        {"u":"company::kickstarter","v":"founder::charles_adler","relation":"Founded by"},

        {"u":"company::tumblr","v":"founder::david_karp","relation":"Founded by"},

        {"u":"company::foursquare","v":"founder::dennis_crowley","relation":"Founded by"},
        {"u":"company::foursquare","v":"founder::naveen_selvadurai","relation":"Founded by"},

        {"u":"company::soundcloud","v":"founder::alexander_ljung","relation":"Founded by"},
        {"u":"company::soundcloud","v":"founder::eric_wahlforss","relation":"Founded by"},

        {"u":"investor::sequoia","v":"company::twitter","relation":"Investor"},
        {"u":"investor::a16z","v":"company::coinbase","relation":"Investor"},
        {"u":"investor::iconiq","v":"company::duolingo","relation":"Investor"},
    ],
    "sources": {
        "investor::usv": ["https://www.usv.com/team/"],
        "company::etsy": ["https://www.usv.com/portfolio/etsy/","https://en.wikipedia.org/wiki/Etsy"],
        "company::twitter": ["https://www.usv.com/portfolio/twitter/","https://en.wikipedia.org/wiki/Twitter"],
        "company::coinbase": ["https://www.usv.com/portfolio/coinbase/","https://en.wikipedia.org/wiki/Coinbase"],
        "company::duolingo": ["https://www.usv.com/portfolio/duolingo/","https://en.wikipedia.org/wiki/Duolingo"],
        "company::kickstarter": ["https://www.usv.com/portfolio/kickstarter/","https://en.wikipedia.org/wiki/Kickstarter"],
        "company::tumblr": ["https://www.usv.com/portfolio/tumblr/","https://en.wikipedia.org/wiki/Tumblr"],
        "company::foursquare": ["https://www.usv.com/portfolio/foursquare/","https://en.wikipedia.org/wiki/Foursquare"],
        "company::soundcloud": ["https://www.usv.com/portfolio/soundcloud/","https://en.wikipedia.org/wiki/SoundCloud"]
    }
}

# =================================================
# Optional Google CSE (kept for future; not required here)
# =================================================
@st.cache_data(show_spinner=False, ttl=86400)
def serp(q: str, num: int = 5):
    cx, key = os.getenv("GOOGLE_CSE_ID"), os.getenv("GOOGLE_API_KEY")
    if not cx or not key: return []
    num = max(1, min(num, 10))
    r = requests.get("https://www.googleapis.com/customsearch/v1",
                     params={"q": q, "cx": cx, "key": key, "num": num}, timeout=15)
    if r.status_code != 200:
        return [{"title": f"Search error {r.status_code}", "snippet": r.text[:160], "link": ""}]
    items = r.json().get("items") or []
    return [{"title": it.get("title",""), "snippet": it.get("snippet",""), "link": it.get("link","")} for it in items[:num]]

# =================================================
# Graph build & session helpers
# =================================================
def build_demo_graph():
    G = nx.Graph(); meta = {}; sources = defaultdict(set)
    for n in DEMO_GRAPH["nodes"]:
        meta[n["id"]] = {"type": n["type"], "label": n["label"], "url": n.get("url","")}
        G.add_node(n["id"])
    for e in DEMO_GRAPH["edges"]:
        G.add_edge(e["u"], e["v"], relation=e.get("relation",""))
    for nid, urls in (DEMO_GRAPH.get("sources") or {}).items():
        for u in urls: sources[nid].add(u)
    return G, meta, sources

def save_graph(G, meta, sources):
    st.session_state.G = G
    st.session_state.META = meta
    st.session_state.SOURCES = sources
    st.session_state.LABEL2ID = {f"{meta[n]['label']} ({meta[n]['type']})": n for n in G.nodes()}
    if "PATH" not in st.session_state:
        st.session_state.PATH = []  # store the last computed path as a list of node ids

def load_graph():
    return (st.session_state.get("G"), st.session_state.get("META"),
            st.session_state.get("SOURCES"), st.session_state.get("LABEL2ID"))

def set_path(nodes: List[str]):
    st.session_state.PATH = list(nodes or [])

# =================================================
# Visualization
# =================================================
def render_pyvis(G, meta, height="700px", highlight_nodes=None, highlight_edges=None):
    net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#222")
    net.barnes_hut(spring_length=150, damping=0.85)
    COLORS = {"company":"#16a34a","founder":"#2563eb","investor":"#f97316","partner":"#7c3aed"}
    hn = set(highlight_nodes or []); he = set(highlight_edges or [])
    for nid in G.nodes():
        a = meta[nid]; color = COLORS.get(a["type"], "#64748b")
        url = a.get("url","")
        title = f"{a['type'].title()}: {a['label']}" + (f"<br><a href='{url}' target='_blank'>{url}</a>" if url else "")
        net.add_node(nid, label=a["label"], color=color, title=title, borderWidth=(3 if nid in hn else 1))
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, title=d.get("relation",""), width=(3 if ((u,v) in he or (v,u) in he) else 1))
    net.toggle_physics(True)
    return net.generate_html("graph.html")

# =================================================
# Build (demo-only for now)
# =================================================
with st.form("builder"):
    demo_mode = st.checkbox("Use Demo Mode", value=True, help="Curated USV network; great for demos.")
    submitted = st.form_submit_button("Build / Rebuild")
if submitted:
    if not demo_mode:
        st.warning("For now, enable Demo Mode (no paid APIs)."); st.stop()
    G, META, SOURCES = build_demo_graph()
    save_graph(G, META, SOURCES)

G, META, SOURCES, LABEL2ID = load_graph()
if G is None:
    st.info("Click **Build / Rebuild** to load the USV demo network.")
    st.stop()

# =================================================
# Sidebar controls
# =================================================
st.sidebar.header("Filters")
typ_filter = st.sidebar.multiselect("Node types", ["founder","company","investor","partner"],
                                    default=["founder","company","investor","partner"])
query = st.sidebar.text_input("Search name contains", "")

st.sidebar.header("Focus")
usv_focus = st.sidebar.checkbox("USV‑centric view", value=True, help="Keep nodes within N hops of USV.")
depth = int(st.sidebar.slider("Depth (hops)", 1, 3, 2))
focus_display = st.sidebar.selectbox("Or pick a node to focus", ["(none)"] + sorted(LABEL2ID.keys()), index=0, key="focus_pick")
apply_focus = st.sidebar.checkbox("Apply focus", value=True)

st.sidebar.header("Warm Intro Path")
start_display = st.sidebar.selectbox("From", ["(pick)"] + sorted(LABEL2ID.keys()), index=0, key="path_from")
end_display   = st.sidebar.selectbox("To",   ["(pick)"] + sorted(LABEL2ID.keys()), index=0, key="path_to")
find_path = st.sidebar.button("Find shortest path")
warm_to_usv = st.sidebar.button("Find warm intro path → USV")
clear_path = st.sidebar.button("Clear path")

if clear_path:
    set_path([])

# =================================================
# Build base filtered view (before focus) — path uses this!
# =================================================
def subgraph_by_filters(G, META, typ_filter, query):
    q = (query or "").lower().strip()
    keep = []
    for nid, a in META.items():
        if nid not in G: continue
        if a["type"] not in typ_filter: continue
        if q and q not in a["label"].lower(): continue
        keep.append(nid)
    return G.subgraph(keep).copy()

H_base = subgraph_by_filters(G, META, typ_filter, query)
if H_base.number_of_nodes() == 0:
    st.info("No nodes match current filters."); st.stop()

# =================================================
# Compute shortest path on base view and persist it
# =================================================
def shortest_path_safe(Gsub, src, dst) -> List[str]:
    if src not in Gsub or dst not in Gsub:
        return []
    try:
        return nx.shortest_path(Gsub, source=src, target=dst)
    except nx.NetworkXNoPath:
        return []

if find_path and start_display != "(pick)" and end_display != "(pick)":
    sid, tid = LABEL2ID.get(start_display), LABEL2ID.get(end_display)
    path_nodes = shortest_path_safe(H_base, sid, tid)
    if path_nodes:
        set_path(path_nodes)
    else:
        st.warning("No connection found in the current filtered view. Try widening filters or turning off focus.")
elif warm_to_usv and start_display != "(pick)":
    sid = LABEL2ID.get(start_display)
    usv_id = "investor::usv"
    path_nodes = shortest_path_safe(H_base, sid, usv_id)
    if path_nodes:
        set_path(path_nodes)
    else:
        st.warning("No warm intro path to USV in the current filtered view.")

# =================================================
# Now apply focus to the base view (don’t affect computed path)
# =================================================
def ego_focus(Gsub, center_id, radius):
    if center_id not in Gsub: return Gsub.copy()
    return nx.ego_graph(Gsub, center_id, radius=radius, undirected=True).copy()

H = H_base
if apply_focus:
    center = None
    if usv_focus and "investor::usv" in H:
        center = "investor::usv"
    elif focus_display != "(none)":
        cand = LABEL2ID.get(focus_display)
        center = cand if cand in H else None
    if center:
        H = ego_focus(H, center, depth)

# =================================================
# Highlight path (if any), intersected with what’s visible after focus
# =================================================
highlight_nodes: Set[str] = set()
highlight_edges: Set[Tuple[str, str]] = set()
stored_path = st.session_state.get("PATH", [])
if stored_path:
    visible_nodes = set(H.nodes())
    any_hidden = False
    for n in stored_path:
        if n in visible_nodes:
            highlight_nodes.add(n)
        else:
            any_hidden = True
    for u, v in zip(stored_path, stored_path[1:]):
        if H.has_edge(u, v):
            highlight_edges.add((u, v))
        else:
            any_hidden = True
    if any_hidden:
        st.info("A saved path exists, but some nodes are hidden by current focus/filters. Clear focus or widen filters to see the full path.")

# =================================================
# Render graph
# =================================================
html = render_pyvis(H, META, highlight_nodes=highlight_nodes, highlight_edges=highlight_edges)
st.components.v1.html(html, height=720, scrolling=True)

# =================================================
# Node Inspector (useful details)
# =================================================
st.markdown("### Node Inspector")
labels_sorted = sorted([f"{META[n]['label']} ({META[n]['type']})" for n in H.nodes()], key=str.lower)
pick = st.selectbox("Select a node to inspect", labels_sorted, index=0)
nid = st.session_state.LABEL2ID[pick]

def _neighbors_by_type(nid, t):
    return sorted([nb for nb in H.neighbors(nid) if META[nb]["type"] == t], key=lambda x: META[x]["label"].lower())

cols = st.columns(3)
with cols[0]:
    st.write("**Companies**")
    for nb in _neighbors_by_type(nid, "company"):
        st.write(f"- {META[nb]['label']}")
with cols[1]:
    st.write("**Founders/Partners**")
    for t in ("founder","partner"):
        for nb in _neighbors_by_type(nid, t):
            st.write(f"- {META[nb]['label']}")
with cols[2]:
    st.write("**Investors**")
    for nb in _neighbors_by_type(nid, "investor"):
        st.write(f"- {META[nb]['label']}")

urls = sorted(list(st.session_state.SOURCES.get(nid, [])))
if urls:
    st.write("**Sources:**")
    for u in urls:
        st.write(f"- [{urlparse(u).netloc}]({u})")

# =================================================
# Insights
# =================================================
st.markdown("### Insights")
deg = {n: H.degree(n) for n in H.nodes()}
bet = nx.betweenness_centrality(H) if H.number_of_nodes() < 150 else {n: 0 for n in H.nodes()}
top = sorted(H.nodes(), key=lambda n: (deg[n], bet[n]), reverse=True)[:5]
if top:
    st.write("Most connected in this view (degree | betweenness):")
    for n in top:
        st.write(f"- {META[n]['label']} ({META[n]['type']}) — {deg[n]} | {bet[n]:.3f}")

companies = [n for n in H.nodes() if META[n]["type"] == "company"]
inv_by_company = {c: {nb for nb in H.neighbors(c) if META[nb]["type"] == "investor"} for c in companies}
pairs = []
for i in range(len(companies)):
    for j in range(i+1, len(companies)):
        a, b = companies[i], companies[j]
        shared = inv_by_company[a].intersection(inv_by_company[b])
        if shared:
            pairs.append((META[a]["label"], META[b]["label"], sorted(META[s]["label"] for s in shared)))
if pairs:
    st.write("Shared investors between companies:")
    for a, b, lst in pairs[:8]:
        st.write(f"- {a} ↔ {b}: " + ", ".join(lst))

# =================================================
# Export
# =================================================
payload = {
    "nodes": {n: {"label": META[n]["label"], "type": META[n]["type"], "url": META[n].get("url","")} for n in H.nodes()},
    "edges": [{"u": u, "v": v, "relation": G.get_edge_data(u,v).get("relation","")} for u,v in H.edges() if u in H and v in H],
    "sources": {n: sorted(list(st.session_state.SOURCES.get(n, []))) for n in H.nodes()},
}
st.download_button("Download graph JSON", json.dumps(payload, indent=2), file_name="founder_network.json", use_container_width=True)

st.caption("Note: Demo data is curated for presentation. Public web augmentation can be added later; verify before use.")
