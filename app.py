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
st.caption("MVP: public-web signals only (no CSV, no proprietary data)")

# -------------------------------------------------
# Cached Google CSE search (reuse your existing secrets)
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
    out = []
    for it in items[:num]:
        out.append({
            "title": it.get("title",""),
            "snippet": it.get("snippet",""),
            "link": it.get("link",""),
        })
    return out

# -------------------------------------------------
# Parsing helpers (lightweight heuristics)
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
    # keep names like "John Smith" / "Mary-Jane Lee"
    parts = s.split()
    if len(parts) > 5 or len(parts) < 2:
        return ""
    # Title case likely names
    return " ".join(p if p.isupper() and len(p) <= 4 else p.capitalize() for p in parts)

def extract_founders(snips: List[Dict[str, str]]) -> List[Tuple[str,str,str]]:
    """Returns list of (name, role_or_hint, source_url)"""
    found = []
    for hit in snips:
        text = f"{hit.get('title','')} — {hit.get('snippet','')}"
        if not FOUNDER_HINTS.search(text):
            continue
        # naive name capture preceding founder/CEO terms
        m = re.findall(r"([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,3})\s+(?:,?\s*)?(?:co-?founder|founder|CEO|CTO|CPO|Chief Executive|Chief Technology)", text)
        for raw in m:
            name = _clean_name(raw)
            if name:
                # try to extract role word nearby
                role = "Founder/Exec"
                role_m = re.search(rf"{re.escape(name)}.*?\b(co-?founder|founder|CEO|CTO|CPO)\b", text, re.I)
                if role_m:
                    role = role_m.group(1).upper()
                found.append((name, role, hit.get("link","")))
    # de-dup
    seen = set(); uniq = []
    for n, r, u in found:
        key = (n.lower(), r.lower())
        if key in seen: 
            continue
        seen.add(key); uniq.append((n, r, u))
    return uniq[:12]

def extract_investors(snips: List[Dict[str, str]]) -> List[Tuple[str,str]]:
    """Returns list of (investor_name, source_url)"""
    invs = []
    for hit in snips:
        text = f"{hit.get('title','')} — {hit.get('snippet','')}"
        # "led by X" pattern
        led = LED_BY.search(text)
        if led:
            chunk = led.group(1)
            # split on and/commas
            parts = re.split(r"\s+and\s+|,|;|\/", chunk)
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                # keep likely firm names containing VC_KEYWORDS somewhere
                if re.search(VC_KEYWORDS, p, re.I):
                    invs.append((p, hit.get("link","")))
        # generic "Firm Capital" patterns
        for m in INV_LISTY.finditer(text):
            invs.append((m.group(0).strip(), hit.get("link","")))
    # de-dup by lowercase
    seen = set(); uniq=[]
    for n,u in invs:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k); uniq.append((n,u))
    return uniq[:20]

# -------------------------------------------------
# Build graph
# -------------------------------------------------
def build_graph(companies: List[str]) -> Tuple[nx.Graph, Dict[str, Dict[str,Any]], Dict[str, Set[str]]]:
    """
    Returns:
      G: networkx graph
      meta: node_id -> {"type":"founder|company|investor", "label":str, "url":str|""}
      sources_by_node: node_id -> set(urls)
    """
    G = nx.Graph()
    meta: Dict[str, Dict[str,Any]] = {}
    sources_by_node: Dict[str, Set[str]] = defaultdict(set)

    for raw_company in companies:
        company = raw_company.strip()
        if not company:
            continue

        # Fetch snippets
        founders_hits = serp(f"{company} founders leadership team site:about OR site:team OR founders")
        investors_hits = serp(f"{company} funding investors led by Series round")

        founders = extract_founders(founders_hits)
        investors = extract_investors(investors_hits)

        # Add company node
        cid = f"company::{company.lower()}"
        if cid not in meta:
            meta[cid] = {"type":"company","label":company,"url": ""}
            G.add_node(cid)
        for h in founders_hits + investors_hits:
            if h.get("link"):
                sources_by_node[cid].add(h["link"])

        # Link founders → company
        for name, role, url in founders:
            fid = f"founder::{name.lower()}"
            if fid not in meta:
                meta[fid] = {"type":"founder","label":name,"url": url}
                G.add_node(fid)
            G.add_edge(fid, cid, relation=role)
            if url: sources_by_node[fid].add(url)

        # Link investors → company
        for inv, url in investors:
            iid = f"investor::{inv.lower()}"
            if iid not in meta:
                meta[iid] = {"type":"investor","label":inv,"url": url}
                G.add_node(iid)
            G.add_edge(iid, cid, relation="invested")
            if url: sources_by_node[iid].add(url)

    return G, meta, sources_by_node

# -------------------------------------------------
# Render with PyVis
# -------------------------------------------------
def render_pyvis(G: nx.Graph, meta: Dict[str, Dict[str,Any]], height: str = "700px") -> str:
    net = Network(height=height, width="100%", bgcolor="#ffffff", font_color="#222")
    net.barnes_hut(spring_length=150, damping=0.85)
    # Add nodes with colors by type
    COLORS = {"company":"#16a34a", "founder":"#2563eb", "investor":"#f97316"}  # green, blue, orange
    for nid, attrs in meta.items():
        t = attrs["type"]
        label = attrs["label"]
        url = attrs.get("url") or ""
        color = COLORS.get(t, "#64748b")
        title = f"{t.title()}: {label}" + (f"<br><a href='{url}' target='_blank'>{url}</a>" if url else "")
        net.add_node(nid, label=label, color=color, title=title)
    # Add edges
    for u, v, d in G.edges(data=True):
        rel = d.get("relation","")
        net.add_edge(u, v, title=rel)
    net.toggle_physics(True)
    return net.generate_html("graph.html")  # returns html string

# -------------------------------------------------
# UI
# -------------------------------------------------
with st.form("input"):
    companies_raw = st.text_input("Enter 1–5 company names (comma separated)", value="Anthropic, Plaid")
    submitted = st.form_submit_button("Build network")

if submitted:
    companies = [c.strip() for c in companies_raw.split(",") if c.strip()][:5]
    if not companies:
        st.warning("Please enter at least one company.")
    else:
        with st.spinner("Building graph from public signals..."):
            G, meta, sources_by_node = build_graph(companies)

        # Sidebar filters
        st.sidebar.header("Filters")
        typ_filter = st.sidebar.multiselect("Node types", ["founder","company","investor"], default=["founder","company","investor"])
        query = st.sidebar.text_input("Search name contains", value="")
        query_l = query.lower().strip()

        # Filter nodes
        visible = []
        for nid, attrs in meta.items():
            if attrs["type"] not in typ_filter: 
                continue
            if query_l and query_l not in attrs["label"].lower():
                continue
            visible.append(nid)

        H = G.subgraph(visible).copy()
        # keep neighbors for context (optional)
        # for nid in list(H.nodes()):
        #     H.add_nodes_from(G.neighbors(nid))
        #     for nb in G.neighbors(nid):
        #         H.add_edge(nid, nb, **G.get_edge_data(nid, nb))

        # Render
        html = render_pyvis(H, {nid: meta[nid] for nid in H.nodes()})
        st.components.v1.html(html, height=720, scrolling=True)

        # Sources panel
        st.markdown("### Sources")
        for nid in H.nodes():
            attrs = meta[nid]
            if not sources_by_node.get(nid): 
                continue
            st.markdown(f"**{attrs['label']}**  <sub>`{attrs['type']}`</sub>", unsafe_allow_html=True)
            for u in sorted(sources_by_node[nid]):
                st.write(f"- [{_domain(u)}]({u})")

        # Export JSON
        payload = {
            "companies": companies,
            "nodes": {nid: meta[nid] for nid in H.nodes()},
            "edges": [{"u": u, "v": v, "relation": G.get_edge_data(u,v).get("relation","")} for u,v in H.edges()],
            "sources": {nid: sorted(list(sources_by_node.get(nid, []))) for nid in H.nodes()},
        }
        st.download_button("Download graph JSON", json.dumps(payload, indent=2), file_name="founder_network.json", use_container_width=True)

else:
    st.info("Enter one or more company names above and click **Build network**. We’ll map founders and investors from public web snippets (About/Team pages, press, etc.).")

# Footnote
st.caption("Note: This MVP uses light heuristics from public web snippets. It may miss people or firms; verify before use.")
