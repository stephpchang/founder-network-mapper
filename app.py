# founder_mapper_app.py
import os, re, json, requests, streamlit as st
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict

import networkx as nx
from pyvis.network import Network

# =========================
# App shell
# =========================
st.set_page_config(page_title="Founder Network Mapper", layout="wide")
st.title("Founder Network Mapper")
st.caption("USV demo: reliable warm-intro paths, ranked candidates, path reasons, CSV export. No paid APIs required.")

# =========================
# Curated demo graph (USV)
# =========================
DEMO_GRAPH = {
    "nodes": [
        {"id":"investor::usv","label":"Union Square Ventures","type":"investor","url":"https://www.usv.com/"},
        {"id":"partner::fred_wilson","label":"Fred Wilson","type":"partner","url":"https://www.usv.com/team/fred-wilson/"},
        {"id":"partner::albert_wenger","label":"Albert Wenger","type":"partner","url":"https://www.usv.com/team/albert-wenger/"},
        {"id":"partner::rebecca_kaden","label":"Rebecca Kaden","type":"partner","url":"https://www.usv.com/team/rebecca-kaden/"},
        {"id":"partner::nick_grossman","label":"Nick Grossman","type":"partner","url":"https://www.usv.com/team/nick-grossman/"},
        {"id":"partner::andy_weissman","label":"Andy Weissman","type":"partner","url":"https://www.usv.com/team/andy-weissman/"},
        # portfolio subset + founders
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
        # USV structure
        {"u":"partner::fred_wilson","v":"investor::usv","relation":"Partner"},
        {"u":"partner::albert_wenger","v":"investor::usv","relation":"Partner"},
        {"u":"partner::rebecca_kaden","v":"investor::usv","relation":"Partner"},
        {"u":"partner::nick_grossman","v":"investor::usv","relation":"Partner"},
        {"u":"partner::andy_weissman","v":"investor::usv","relation":"Partner"},
        # USV -> portfolio
        {"u":"investor::usv","v":"company::etsy","relation":"Invested in"},
        {"u":"investor::usv","v":"company::twitter","relation":"Invested in"},
        {"u":"investor::usv","v":"company::coinbase","relation":"Invested in"},
        {"u":"investor::usv","v":"company::duolingo","relation":"Invested in"},
        {"u":"investor::usv","v":"company::kickstarter","relation":"Invested in"},
        {"u":"investor::usv","v":"company::tumblr","relation":"Invested in"},
        {"u":"investor::usv","v":"company::foursquare","relation":"Invested in"},
        {"u":"investor::usv","v":"company::soundcloud","relation":"Invested in"},
        # companies -> founders
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
        # extra investors
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

# =========================
# Build + session
# =========================
def build_demo_graph():
    G = nx.Graph(); meta = {}; src = defaultdict(set)
    for n in DEMO_GRAPH["nodes"]:
        meta[n["id"]] = {"type": n["type"], "label": n["label"], "url": n.get("url","")}
        G.add_node(n["id"])
    for e in DEMO_GRAPH["edges"]:
        G.add_edge(e["u"], e["v"], relation=e.get("relation",""))
    for nid, urls in (DEMO_GRAPH.get("sources") or {}).items():
        for u in urls: src[nid].add(u)
    return G, meta, src

def save_graph(G, META, SOURCES):
    st.session_state.G = G
    st.session_state.META = META
    st.session_state.SOURCES = SOURCES
    st.session_state.LABEL2ID = {f"{META[n]['label']} ({META[n]['type']})": n for n in G.nodes()}

def load_graph():
    return (st.session_state.get("G"), st.session_state.get("META"),
            st.session_state.get("SOURCES"), st.session_state.get("LABEL2ID"))

with st.form("builder"):
    if st.form_submit_button("Load USV Demo Network"):
        G, META, SOURCES = build_demo_graph()
        save_graph(G, META, SOURCES)

G, META, SOURCES, LABEL2ID = load_graph()
if G is None:
    st.info("Click **Load USV Demo Network** to start.")
    st.stop()

# =========================
# Sidebar controls
# =========================
st.sidebar.header("Filters")
typ_filter = st.sidebar.multiselect("Node types", ["founder","company","investor","partner"],
                                    default=["founder","company","investor","partner"])
query = st.sidebar.text_input("Search label contains", "")

st.sidebar.header("Focus")
depth = int(st.sidebar.slider("Depth (hops)", 1, 3, 2))
focus_pick = st.sidebar.selectbox("Focus on node", ["(none)"] + sorted(LABEL2ID.keys()), index=0)
apply_focus = st.sidebar.checkbox("Apply focus", value=True)

st.sidebar.header("Warm Intro Path")
start_pick = st.sidebar.selectbox("From", ["(pick)"] + sorted(LABEL2ID.keys()), index=0)
end_pick   = st.sidebar.selectbox("To",   ["(pick)"] + sorted(LABEL2ID.keys()), index=0)
run_path = st.sidebar.button("Compute path")

# =========================
# Filtering
# =========================
def subgraph_by_filters(G, META, types, q):
    q = (q or "").lower().strip()
    keep = []
    for n,a in META.items():
        if n not in G: continue
        if a["type"] not in types: continue
        if q and q not in a["label"].lower(): continue
        keep.append(n)
    return G.subgraph(keep).copy()

H = subgraph_by_filters(G, META, typ_filter, query)
if H.number_of_nodes() == 0:
    st.info("No nodes match current filters."); st.stop()

# =========================
# Focus by hops (fixed)
# =========================
def ego_subgraph(Gsub: nx.Graph, center: str, radius: int):
    if center not in Gsub: return Gsub.copy(), set(), set()
    ego = nx.ego_graph(Gsub, center, radius=radius, undirected=True)
    return ego.copy(), set(ego.nodes()), set(ego.edges())

highlight_nodes, highlight_edges = set(), set()
if apply_focus and focus_pick != "(none)":
    center = LABEL2ID.get(focus_pick)
    if center in H:
        H, highlight_nodes, highlight_edges = ego_subgraph(H, center, depth)
    else:
        st.info("Focused node is not visible with current filters.")

# =========================
# Render graph
# =========================
def render_pyvis(G, META, highlight_nodes=None, highlight_edges=None):
    net = Network(height="720px", width="100%", bgcolor="#fff", font_color="#222")
    net.barnes_hut(spring_length=150, damping=0.85)
    COLORS = {"company":"#16a34a","founder":"#2563eb","investor":"#f97316","partner":"#7c3aed"}
    hn = highlight_nodes or set(); he = highlight_edges or set()
    for n in G.nodes():
        a = META[n]; color = COLORS.get(a["type"], "#64748b")
        title = f"{a['type'].title()}: {a['label']}" + (f"<br><a href='{a.get('url','')}' target='_blank'>{a.get('url','')}</a>" if a.get("url") else "")
        net.add_node(n, label=a["label"], color=color, title=title, borderWidth=(3 if n in hn else 1))
    for u, v in G.edges():
        rel = G.get_edge_data(u,v).get("relation","")
        net.add_edge(u, v, title=rel, width=(3 if ((u,v) in he or (v,u) in he) else 1))
    net.toggle_physics(True)
    return net.generate_html("g.html")

html = render_pyvis(H, META, highlight_nodes, highlight_edges)
st.components.v1.html(html, height=740, scrolling=True)

# =========================
# Warm Intro Finder (ranked) — USV value
# =========================
st.markdown("## Warm‑Intro Finder (ranked)")

# candidate pool & target
target_choices = sorted([f"{META[n]['label']} ({META[n]['type']})" for n in H.nodes() if META[n]["type"] in ("company","founder")], key=str.lower)
if not target_choices:
    st.info("No companies or founders visible. Adjust filters above.")
else:
    target_pick = st.selectbox("Target company/founder", target_choices, key="warm_target")
    target_id = LABEL2ID[target_pick]

    pool_types = st.multiselect("Who could intro you?", ["partner","investor","founder"], default=["partner","investor"])
    require_usv_partner = st.checkbox("Require path to include a USV partner", value=True,
                                      help="Ensures paths go through Fred/Albert/Rebecca/Nick/Andy (strongest USV signal).")

    # Transparent edge weights (value story)
    EDGE_WEIGHT = {"Partner": 3.0, "Invested in": 2.5, "Investor": 2.2, "Founded by": 2.0}
    TYPE_BONUS = {"partner": 1.5, "investor": 1.2, "founder": 1.0, "company": 0.8}

    # precompute partner IDs for constraint
    USV_PARTNERS = {n for n,a in META.items() if a["type"] == "partner"}

    def path_reason(p: List[str]) -> str:
        hops = []
        for u,v in zip(p,p[1:]):
            rel = H.get_edge_data(u,v,{}).get("relation","")
            hops.append(f"{META[u]['label']} —{rel}→ {META[v]['label']}")
        return " → ".join(hops)

    def path_score(p: List[str]) -> float:
        if len(p) < 2: return 0.0
        s = 0.0
        for u,v in zip(p,p[1:]):
            rel = H.get_edge_data(u,v,{}).get("relation","")
            s += EDGE_WEIGHT.get(rel, 1.0)
        s *= TYPE_BONUS.get(META[p[0]]["type"], 1.0)   # candidate type
        s -= 0.5 * (len(p) - 2)                        # slight penalty for length
        return round(s, 3)

    # candidates from current view
    candidates = [n for n in H.nodes() if META[n]["type"] in pool_types and n != target_id]

    ranked: List[Tuple[float, List[str]]] = []
    for c in candidates:
        try:
            p = nx.shortest_path(H, source=c, target=target_id)
            if require_usv_partner and not any(x in USV_PARTNERS for x in p):
                continue
            ranked.append((path_score(p), p))
        except nx.NetworkXNoPath:
            continue

    ranked.sort(key=lambda x: x[0], reverse=True)
    top_k = st.slider("Show top N", 3, 15, 7)

    if not ranked:
        st.warning("No acceptable warm-intro paths with current constraints. Try turning off the USV-partner requirement or widen filters.")
    else:
        show = ranked[:top_k]
        st.write("**Ranked candidates:**")
        export_rows = []
        for i,(score,p) in enumerate(show, start=1):
            cand = p[0]
            cand_label = META[cand]["label"]; cand_type = META[cand]["type"]
            labels_chain = " → ".join(META[n]["label"] for n in p)
            reason = path_reason(p)

            st.markdown(f"**{i}. {cand_label}**  <sub>`{cand_type}`</sub> — score **{score}**", unsafe_allow_html=True)
            st.caption(reason)

            with st.expander("Email draft"):
                tgt = META[target_id]["label"]
                st.write(
                    f"Subject: Quick intro to {tgt}?\n\n"
                    f"Hi {{FirstName}},\n\n"
                    f"We’re hoping to connect with **{tgt}**. Noticed a path via **{labels_chain}**. "
                    f"If you’re open to it, could you make a brief intro? Happy to send a blurb.\n\n"
                    f"Thanks so much!\n"
                )

            export_rows.append({
                "rank": i,
                "candidate": cand_label,
                "candidate_type": cand_type,
                "score": score,
                "path_labels": labels_chain,
                "path_reason": reason
            })

        # CSV export
        import csv
        from io import StringIO
        buf = StringIO(); w = csv.DictWriter(buf, fieldnames=list(export_rows[0].keys()))
        w.writeheader(); w.writerows(export_rows)
        st.download_button("Download warm‑intro hit list (CSV)", buf.getvalue(),
                           file_name="warm_intro_ranked.csv", use_container_width=True)

# =========================
# Manual Warm Intro Path (debuggable)
# =========================
st.markdown("## Manual Warm Intro Path")
left, right = st.columns(2)
with left:
    s_pick = st.selectbox("From", ["(pick)"] + sorted(LABEL2ID.keys()), index=0, key="manual_from")
with right:
    t_pick = st.selectbox("To", ["(pick)"] + sorted(LABEL2ID.keys()), index=0, key="manual_to")
if st.button("Compute manual path"):
    if s_pick == "(pick)" or t_pick == "(pick)":
        st.warning("Pick both endpoints.")
    else:
        s_id, t_id = LABEL2ID[s_pick], LABEL2ID[t_pick]
        if s_id in H and t_id in H:
            try:
                p = nx.shortest_path(H, source=s_id, target=t_id)
                st.success(" → ".join(META[n]["label"] for n in p))
            except nx.NetworkXNoPath:
                st.warning("No connection in current view.")
        else:
            st.warning("One or both nodes are filtered out. Adjust filters/focus.")

# =========================
# Sources + export
# =========================
st.markdown("## Sources")
for n in H.nodes():
    urls = sorted(list(st.session_state.SOURCES.get(n, [])))
    if not urls: continue
    st.markdown(f"**{META[n]['label']}**  <sub>`{META[n]['type']}`</sub>", unsafe_allow_html=True)
    for u in urls:
        st.write(f"- [{urlparse(u).netloc}]({u})")

payload = {
    "nodes": {n: {"label": META[n]["label"], "type": META[n]["type"], "url": META[n].get("url","")} for n in H.nodes()},
    "edges": [{"u": u, "v": v, "relation": H.get_edge_data(u,v).get("relation","")} for u,v in H.edges()],
    "sources": {n: sorted(list(st.session_state.SOURCES.get(n, []))) for n in H.nodes()},
}
st.download_button("Download current view (JSON)", json.dumps(payload, indent=2), file_name="founder_network.json", use_container_width=True)
