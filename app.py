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
st.caption("Demo-friendly: curated Demo Mode, Focus on node, Warm Intro Paths, optional web augmentation")

# -------------------------------------------------
# Demo data (curated so you can show functionality without paid APIs)
# Added: USV + partners connected to USV
# -------------------------------------------------
DEMO_GRAPH = {
    "nodes": [
        # Companies
        {"id": "company::anthropic", "label": "Anthropic", "type": "company", "url": "https://www.anthropic.com/"},
        {"id": "company::figma",     "label": "Figma",     "type": "company", "url": "https://www.figma.com/"},
        {"id": "company::plaid",     "label": "Plaid",     "type": "company", "url": "https://plaid.com/"},

        # Founders
        {"id": "founder::dario_amodei",   "label": "Dario Amodei",   "type": "founder", "url": "https://en.wikipedia.org/wiki/Anthropic"},
        {"id": "founder::daniela_amodei", "label": "Daniela Amodei", "type": "founder", "url": "https://en.wikipedia.org/wiki/Anthropic"},
        {"id": "founder::dylan_field",    "label": "Dylan Field",    "type": "founder", "url": "https://en.wikipedia.org/wiki/Dylan_Field"},
        {"id": "founder::evan_wallace",   "label": "Evan Wallace",   "type": "founder", "url": "https://www.figma.com/blog/"},
        {"id": "founder::zach_perret",    "label": "Zach Perret",    "type": "founder", "url": "https://en.wikipedia.org/wiki/Plaid_(company)"},
        {"id": "founder::william_hockey", "label": "William Hockey", "type": "founder", "url": "https://en.wikipedia.org/wiki/Plaid_(company)"},

        # Investors (sample)
        {"id": "investor::spark_capital", "label": "Spark Capital", "type": "investor", "url": "https://www.sparkcapital.com/"},
        {"id": "investor::sequoia",       "label": "Sequoia Capital", "type": "investor", "url": "https://www.sequoiacap.com/"},
        {"id": "investor::a16z",          "label": "Andreessen Horowitz", "type": "investor", "url": "https://a16z.com/"},
        {"id": "investor::iconiq",        "label": "ICONIQ Capital", "type": "investor", "url": "https://www.iconiqcapital.com/"},
        {"id": "investor::index",         "label": "Index Ventures", "type": "investor", "url": "https://www.indexventures.com/"},

        # USV + partners
        {"id": "investor::usv",           "label": "Union Square Ventures", "type": "investor", "url": "https://www.usv.com/"},
        {"id": "partner::fred_wilson",    "label": "Fred Wilson",   "type": "partner", "url": "https://www.usv.com/team/fred-wilson/"},
        {"id": "partner::albert_wenger",  "label": "Albert Wenger", "type": "partner", "url": "https://www.usv.com/team/albert-wenger/"},
        {"id": "partner::rebecca_kaden",  "label": "Rebecca Kaden", "type": "partner", "url": "https://www.usv.com/team/rebecca-kaden/"},
        {"id": "partner::nick_grossman",  "label": "Nick Grossman", "type": "partner", "url": "https://www.usv.com/team/nick-grossman/"},
        {"id": "partner::andy_weissman",  "label": "Andy Weissman", "type": "partner", "url": "https://www.usv.com/team/andy-weissman/"},
    ],
    "edges": [
        # Founder -> Company
        {"u": "founder::dario_amodei",   "v": "company::anthropic", "relation": "Co‑founder"},
        {"u": "founder::daniela_amodei", "v": "company::anthropic", "relation": "Co‑founder"},
        {"u": "founder::dylan_field",    "v": "company::figma",     "relation": "Co‑founder"},
        {"u": "founder::evan_wallace",   "v": "company::figma",     "relation": "Co‑founder"},
        {"u": "founder::zach_perret",    "v": "company::plaid",     "relation": "Co‑founder"},
        {"u": "founder::william_hockey", "v": "company::plaid",     "relation": "Co‑founder"},

        # Investor -> Company (illustrative only)
        {"u": "investor::spark_capital", "v": "company::anthropic", "relation": "Investor"},
        {"u": "investor::sequoia",       "v": "company::figma",     "relation": "Investor"},
        {"u": "investor::a16z",          "v": "company::figma",     "relation": "Investor"},
        {"u": "investor::iconiq",        "v": "company::figma",     "relation": "Investor"},
        {"u": "investor::index",         "v": "company::plaid",     "relation": "Investor"},

        # Partners -> USV
        {"u": "partner::fred_wilson",    "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::albert_wenger",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::rebecca_kaden",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::nick_grossman",  "v": "investor::usv", "relation": "Partner"},
        {"u": "partner::andy_weissman",  "v": "investor::usv", "relation": "Partner"},
    ],
    "sources": {
        "company::anthropic": [
            "https://www.anthropic.com/",
            "https://en.wikipedia.org/wiki/Anthropic"
        ],
        "company::figma": [
            "https://www.figma.com/",
            "https://en.wikipedia.org/wiki/Figma"
        ],
        "company::plaid": [
            "https://plaid.com/",
            "https://en.wikipedia.org/wiki/Plaid_(company)"
        ],
        "investor::usv": ["https://www.usv.com/team/"]
    }
}

# -------------------------------------------------
# Cached Google CSE (optional augmentation)
# -------------------------------------------------
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

# -------------------------------------------------
# Lightweight parsing (heuristics)
# -------------------------------------------------
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

# -------------------------------------------------
# Build graphs
# -------------------------------------------------
def build_graph_from_demo() -> Tuple[nx.Graph, Dict[str, Dict[str,Any]], Dict[str, Set[str]]]:
    G = nx.Graph()
    meta = {}
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
            G.add_edge(iid, cid, relation="invested")
            if url: sources_by_node[iid].add(url)

    return G, meta, sources_by_node

# -------------------------------------------------
# Insights
# -------------------------------------------------
def compute_insights(G: nx.Graph, meta: Dict[str, Dict[str,Any]]) -> Dict[str, Any]:
    deg = {nid: G.degree(nid) for nid in G.nodes()}
    top_nodes = sorted(deg.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top = [{"label": meta[n]["label"], "type": meta[n]["type"], "degree": d} for n, d in top_nodes]

    comp_investors: Dict[str, Set[str]] = defaultdict(set)
    for nid, attrs in meta.items():
        if attrs["type"] != "investor":
            continue
        for nb in G.neighbors(nid):
            if meta[nb]["type"] == "company":
                comp_investors[nb].add(nid)

    shared_list = []
    companies = [nid for nid, a in meta.items() if a["type"] == "company"]
    for i in range(len(companies)):
        for j in range(i+1, len(companies)):
            a, b = companies[i], companies[j]
            shared = comp_investors[a].intersection(comp_investors[b])
            if shared:
                shared_list.append({
                    "companies": (meta[a]["label"], meta[b]["label"]),
                    "shared_investors": [meta[s]["label"] for s in shared]
                })

    return {"top_connectors": top, "shared_investors": shared_list}

# -------------------------------------------------
# Viz
# -------------------------------------------------
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

# -------------------------------------------------
# UI
# -------------------------------------------------
with st.form("input"):
    demo_mode = st.checkbox("Use Demo Mode (no web lookups)", value=True)
    companies_raw = st.text_input("Enter up to 5 companies (comma separated)", value="Anthropic, Figma, Plaid")
    augment = st.checkbox("Augment demo with public web signals (uses your Google CSE quota)", value=False, disabled=not demo_mode)
    submitted = st.form_submit_button("Build network")

if submitted:
    companies = [c.strip() for c in companies_raw.split(",") if c.strip()][:5]
    if not companies:
        st.warning("Please enter at least one company.")
    else:
        with st.spinner("Building graph..."):
            if demo_mode:
                G, meta, sources_by_node = build_graph_from_demo()
                # keep only typed companies and their neighbors, plus USV and its partners so demo always shows them
                keep_companies = {f"company::{c.lower()}" for c in companies}
                usv_block = {"investor::usv", "partner::fred_wilson","partner::albert_wenger",
                             "partner::rebecca_kaden","partner::nick_grossman","partner::andy_weissman"}
                to_keep = set(usv_block)
                for nid in G.nodes():
                    if nid in keep_companies or any(nb in keep_companies for nb in G.neighbors(nid)):
                        to_keep.add(nid)
                G = G.subgraph(list(to_keep)).copy()
                meta = {nid: meta[nid] for nid in G.nodes()}
                sources_by_node = {nid: set(sources_by_node.get(nid, set())) for nid in G.nodes()}
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
                        sources_by_node.setdefault(nid, set()).update(urls)
            else:
                G, meta, sources_by_node = build_graph_from_serp(companies)

        # ---------- Sidebar controls ----------
        st.sidebar.header("Filters")
        typ_filter = st.sidebar.multiselect("Node types", ["founder","company","investor","partner"],
                                            default=["founder","company","investor","partner"])
        query = st.sidebar.text_input("Search name contains", value="")

        # Build stable selector labels to avoid crashes when nodes are filtered
        def _display_label(nid: str) -> str:
            a = meta[nid]
            return f"{a['label']} ({a['type']})"

        all_options = sorted([_display_label(nid) for nid in G.nodes()], key=lambda s: s.lower())
        label_to_id = { _display_label(nid): nid for nid in G.nodes() }

        # Focus on node (ego network)
        st.sidebar.header("Focus")
        focus_display = st.sidebar.selectbox("Focus on node", ["(none)"] + all_options, index=0, key="focus_select")
        focus_depth = st.sidebar.slider("Depth (hops)", min_value=1, max_value=2, value=1, key="focus_depth")
        apply_focus = st.sidebar.checkbox("Apply focus", value=False, key="apply_focus")

        # Warm intro path
        st.sidebar.header("Warm Intro Path")
        start_display = st.sidebar.selectbox("From", ["(pick)"] + all_options, index=0, key="path_from")
        end_display   = st.sidebar.selectbox("To",   ["(pick)"] + all_options, index=0, key="path_to")
        find_path = st.sidebar.button("Find shortest path")

        # ---------- Filtering ----------
        query_l = (query or "").lower().strip()
        visible = []
        for nid, attrs in meta.items():
            if nid not in G:
                continue
            if attrs["type"] not in typ_filter:
                continue
            if query_l and query_l not in attrs["label"].lower():
                continue
            visible.append(nid)
        H = G.subgraph(visible).copy()

        # Safety: if empty after filters, show message instead of crashing to homepage
        if H.number_of_nodes() == 0:
            st.info("No nodes match the current filters/focus. Clear filters or pick another node.")
            st.stop()

        # Apply focus (ego network) with safeguards
        highlighted_nodes: Set[str] = set()
        highlighted_edges: Set[Tuple[str,str]] = set()
        if apply_focus and focus_display != "(none)":
            fid = label_to_id.get(focus_display)
            if fid in H:
                ego_nodes = nx.ego_graph(H, fid, radius=focus_depth).nodes()
                H = H.subgraph(list(ego_nodes)).copy()
                highlighted_nodes = set(H.nodes())
                if H.number_of_nodes() == 0:
                    st.info("Focused node is filtered out by current filters.")
            else:
                st.info("Focused node is not in the current filtered view. Adjust filters or turn off focus.")

        # Warm intro path (shortest path) with safeguards
        path_nodes: List[str] = []
        if find_path and start_display != "(pick)" and end_display != "(pick)":
            sid = label_to_id.get(start_display)
            tid = label_to_id.get(end_display)
            if sid in H and tid in H:
                try:
                    path_nodes = nx.shortest_path(H, source=sid, target=tid)
                    for u, v in zip(path_nodes, path_nodes[1:]):
                        highlighted_edges.add((u, v))
                    highlighted_nodes.update(path_nodes)
                except nx.NetworkXNoPath:
                    st.warning("No connection found between the selected nodes in the current view.")
            else:
                st.warning("One or both selected nodes are not visible under current filters.")

        # ---------- Render main graph ----------
        html = render_pyvis(H, {nid: meta[nid] for nid in H.nodes()},
                            highlight_nodes=highlighted_nodes,
                            highlight_edges=highlighted_edges)
        st.components.v1.html(html, height=720, scrolling=True)

        # Path explanation
        if path_nodes:
            st.markdown("### Warm Intro Path")
            st.write(" → ".join(meta[n]["label"] for n in path_nodes))

        # Insights
        st.markdown("### Insights")
        insights = compute_insights(H, meta)
        top = insights["top_connectors"]
        if top:
            st.write("Most connected in this view:")
            for t in top:
                st.write(f"- {t['label']} ({t['type']}) — {t['degree']} connections")
        shared = insights["shared_investors"]
        if shared:
            st.write("Shared investors between companies:")
            for item in shared:
                a, b = item["companies"]
                st.write(f"- {a} ↔ {b}: " + ", ".join(item["shared_investors"][:6]))

        # Sources
        st.markdown("### Sources")
        for nid in H.nodes():
            urls = sorted(list(sources_by_node.get(nid, [])))
            if not urls:
                continue
            label = meta[nid]["label"]
            ntype = meta[nid]["type"]
            st.markdown(f"**{label}**  <sub>`{ntype}`</sub>", unsafe_allow_html=True)
            for u in urls:
                st.write(f"- [{urlparse(u).netloc}]({u})")

        # Export JSON
        payload = {
            "companies": companies,
            "nodes": {nid: {"label": meta[nid]["label"], "type": meta[nid]["type"], "url": meta[nid].get("url","")}
                      for nid in H.nodes()},
            "edges": [{"u": u, "v": v, "relation": G.get_edge_data(u,v).get("relation","")} for u,v in H.edges()],
            "sources": {nid: sorted(list(sources_by_node.get(nid, []))) for nid in H.nodes()},
        }
        st.download_button("Download graph JSON", json.dumps(payload, indent=2), file_name="founder_network.json", use_container_width=True)

else:
    st.info("Toggle **Demo Mode** to show functionality instantly, or type up to 5 company names and build the network from public web snippets.")

st.caption("Note: Demo mode uses curated sample data. Web-augmented mode uses heuristics from public sources.")
