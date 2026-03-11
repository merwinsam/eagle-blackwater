"""
Blackwater Legal — Contract Lifecycle Management
"""
import streamlit as st
import json, re, io
from datetime import datetime, date
from openai import OpenAI
import config

CLM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');
.clm-topbar{background:#0e1218;border-bottom:1px solid #1e2a38;padding:0 28px;height:52px;
  display:flex;align-items:center;gap:16px;}
.clm-logo{font-family:'Syne',sans-serif;font-weight:800;font-size:1.1rem;color:#e8c97e;}
.clm-sep{width:1px;height:22px;background:#2a3a4e;}
.clm-sub{font-family:'Space Mono',monospace;font-size:0.63rem;color:#4a6080;
  letter-spacing:0.1em;text-transform:uppercase;}
.kpi-card{background:#0e1218;border:1px solid #1e2a38;border-radius:10px;padding:18px 20px;text-align:center;}
.kpi-label{font-family:'Space Mono',monospace;font-size:0.57rem;color:#4a6080;
  text-transform:uppercase;letter-spacing:0.14em;margin-bottom:8px;}
.kpi-value{font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;color:#e8c97e;line-height:1;}
.kpi-sub{font-size:0.66rem;color:#8a9bb0;margin-top:5px;}
.sec-hdr{font-family:'Space Mono',monospace;font-size:0.63rem;font-weight:700;color:#4a6080;
  text-transform:uppercase;letter-spacing:0.18em;padding:10px 0 7px;
  border-bottom:1px solid #1e2a38;margin-bottom:12px;}
.crow{background:#0e1218;border:1px solid #1e2a38;border-radius:8px;padding:14px 18px;margin-bottom:6px;}
.crow.active{border-left:3px solid #4ade80;}
.crow.expiring{border-left:3px solid #fbbf24;}
.crow.expired{border-left:3px solid #4a6080;}
.cname{font-size:0.88rem;font-weight:600;color:#eef2f7;margin-bottom:5px;}
.cmeta{font-family:'Space Mono',monospace;font-size:0.6rem;color:#4a6080;}
.pill{display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.6rem;
  font-family:'Space Mono',monospace;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;}
.pill-active{background:rgba(74,222,128,0.12);color:#4ade80;border:1px solid rgba(74,222,128,0.3);}
.pill-expiring{background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.3);}
.pill-expired{background:rgba(148,163,184,0.1);color:#94a3b8;border:1px solid rgba(148,163,184,0.2);}
.rbar-wrap{background:#131920;border-radius:4px;height:7px;margin-top:4px;overflow:hidden;}
.rbar-fill{height:100%;border-radius:4px;}
.insight-box{background:#0e1218;border:1px solid #1e2a38;border-left:3px solid #e8c97e;
  border-radius:0 10px 10px 0;padding:14px 18px;font-size:0.8rem;line-height:1.75;
  color:#8a9bb0;white-space:pre-wrap;}
.ext-row{background:#131920;border:1px solid #1e2a38;border-radius:6px;padding:9px 13px;
  margin-bottom:5px;display:flex;justify-content:space-between;align-items:center;}
.ext-lbl{font-size:0.65rem;color:#4a6080;font-family:'Space Mono',monospace;}
.ext-val{font-size:0.75rem;color:#e8c97e;font-family:'Space Mono',monospace;}
</style>
"""

FIELDS = [
    ("counterparty",       "Counterparty Name",          "text",   None),
    ("contract_value",     "Contract Value (INR)",       "number", None),
    ("payment_terms_days", "Payment Terms (days)",       "number", "Days the client has to pay you"),
    ("term_months",        "Term of Agreement (months)", "number", "Total contract duration in months"),
    ("start_date",         "Start Date",                 "date",   None),
    ("termination_days",   "Termination Notice (days)",  "number", "Days notice required to terminate"),
    ("liability_cap_usd",  "Liability Cap (INR)",        "number", "Max $ they can claim against you"),
    ("governing_law",      "Governing Law",              "text",   "e.g. Laws of England & Wales"),
    ("jurisdiction",       "Jurisdiction",               "text",   "e.g. London, Singapore, New York"),
    ("dispute_resolution", "Dispute Resolution",         "select", ["Litigation","Arbitration","Mediation","Negotiation"]),
    ("dispute_cost_usd",   "Est. Dispute Cost (INR)",    "number", "Estimated cost if dispute goes to resolution"),
]


def load_contracts():
    if "clm_contracts" not in st.session_state:
        st.session_state.clm_contracts = []
    return st.session_state.clm_contracts

def save_contracts(c):
    st.session_state.clm_contracts = c

def contract_status(c):
    try:
        from dateutil.relativedelta import relativedelta
        start     = datetime.strptime(str(c.get("start_date", ""))[:10], "%Y-%m-%d").date()
        end       = start + relativedelta(months=int(c.get("term_months", 12) or 12))
        days_left = (end - date.today()).days
        if days_left < 0:   return "expired",  f"Ended {abs(days_left)}d ago"
        if days_left <= 60: return "expiring", f"Expires in {days_left}d"
        return "active", f"{days_left}d remaining"
    except:
        return "active", "—"

def extract_with_ai(text):
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    prompt = (
        "You are a contract analyst. Extract these fields from the contract text.\n"
        "Return ONLY valid JSON with exactly these keys (null if not found):\n"
        "counterparty, contract_value, payment_terms_days, term_months,\n"
        "start_date (YYYY-MM-DD), termination_days, liability_cap_usd,\n"
        "governing_law, jurisdiction,\n"
        "dispute_resolution (one of: Litigation/Arbitration/Mediation/Negotiation),\n"
        "dispute_cost_usd\n\n"
        f"CONTRACT TEXT:\n{text[:6000]}\n\nReturn only JSON, no explanation."
    )
    try:
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=500,
        )
        raw = re.sub(r"```json|```", "", resp.choices[0].message.content.strip()).strip()
        return json.loads(raw)
    except:
        return {}

def gen_insight(contracts):
    if not contracts:
        return "No contracts loaded yet."
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    summary = [{
        "counterparty":  c.get("counterparty"),
        "value":         c.get("contract_value"),
        "payment_days":  c.get("payment_terms_days"),
        "term_months":   c.get("term_months"),
        "termination":   c.get("termination_days"),
        "liability":     c.get("liability_cap_usd"),
        "jurisdiction":  c.get("jurisdiction"),
        "dispute":       c.get("dispute_resolution"),
        "dispute_cost":  c.get("dispute_cost_usd"),
        "status":        contract_status(c)[0],
    } for c in contracts]
    prompt = (
        f"You are a contract risk advisor for Blackwater.\n"
        f"Analyse this portfolio of {len(contracts)} contracts. Give a crisp 6-8 line executive summary:\n"
        f"1. Cash flow risk from payment terms\n"
        f"2. Contracts expiring soon and pipeline gaps\n"
        f"3. Liability exposure concentration\n"
        f"4. Geographic/jurisdictional risk\n"
        f"5. Dispute resolution cost exposure\n"
        f"6. One key recommendation\n"
        f"Be specific with numbers. No fluff.\n\n"
        f"DATA:\n{json.dumps(summary, indent=2)}"
    )
    try:
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate insight: {e}"


def render_clm():
    st.markdown(CLM_CSS, unsafe_allow_html=True)

    # ── Topbar ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="clm-topbar">
      <span style="font-size:1.1rem">⚖️</span>
      <span class="clm-logo">Blackwater Legal</span>
      <div class="clm-sep"></div>
      <span class="clm-sub">Contract Lifecycle Management</span>
      <div style="flex:1"></div>
      <span style="font-family:'Space Mono',monospace;font-size:0.65rem;color:#4a6080">
        {datetime.now().strftime("%b %d %Y")}
      </span>
    </div>
    <div style="height:16px"></div>
    """, unsafe_allow_html=True)

    if st.button("← Back to Blackwater One", key="clm_back"):
        st.session_state.page = "eagle"
        st.rerun()

    contracts = load_contracts()
    total     = len(contracts)

    # ── KPI Dashboard ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-hdr">Dashboard</div>', unsafe_allow_html=True)

    active_n   = sum(1 for c in contracts if contract_status(c)[0] == "active")
    expiring_n = sum(1 for c in contracts if contract_status(c)[0] == "expiring")
    avg_pay    = (sum(float(c.get("payment_terms_days", 0) or 0) for c in contracts) / total) if total else 0
    tot_val    = sum(float(c.get("contract_value",    0) or 0) for c in contracts)
    tot_liab   = sum(float(c.get("liability_cap_usd", 0) or 0) for c in contracts)
    tot_disp   = sum(float(c.get("dispute_cost_usd",  0) or 0) for c in contracts)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    for col, label, value, sub in [
        (k1, "Total Contracts",    str(total),
         f"{active_n} active · {expiring_n} expiring"),
        (k2, "Avg Payment Terms",  f"{avg_pay:.0f}d",
         "Cash flow window"),
        (k3, "Portfolio Value",
         f"${tot_val/1e6:.1f}M" if tot_val >= 1e6 else f"${tot_val:,.0f}",
         "Total contract value"),
        (k4, "Expiring ≤60d",      str(expiring_n),
         "Needs attention"),
        (k5, "Liability Exposure",
         f"${tot_liab/1e6:.1f}M" if tot_liab >= 1e6 else f"${tot_liab:,.0f}",
         "Max cap across portfolio"),
        (k6, "Dispute Cost Pool",  f"${tot_disp:,.0f}",
         "If all disputes litigated"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div>'
                f'<div class="kpi-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    left, mid, right = st.columns([1.2, 1.6, 1.2], gap="medium")

    # ── LEFT — Add Contract ────────────────────────────────────────────────────
    with left:
        st.markdown('<div class="sec-hdr">Add Contract</div>', unsafe_allow_html=True)
        tab_up, tab_man = st.tabs(["📄 Upload & Extract", "✏️ Manual Entry"])

        with tab_up:
            st.markdown("""
            <div style="background:#0e1218;border:1px dashed #2a3a4e;border-radius:10px;
                        padding:20px;text-align:center;margin-bottom:14px">
              <div style="font-size:1.4rem;margin-bottom:6px">📎</div>
              <div style="font-size:0.78rem;color:#8a9bb0">Upload contract PDF or Word doc</div>
              <div style="font-size:0.63rem;color:#4a6080;margin-top:4px">
                Eagle AI extracts all key terms automatically
              </div>
            </div>""", unsafe_allow_html=True)

            uploaded = st.file_uploader(
                "Upload", type=["pdf", "docx", "txt"],
                label_visibility="collapsed", key="clm_upload",
            )

            if uploaded:
                with st.spinner("Eagle reading contract..."):
                    text = ""
                    try:
                        if uploaded.type == "application/pdf":
                            try:
                                import pdfplumber
                                with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
                                    text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                            except Exception:
                                uploaded.seek(0)
                                try:
                                    import PyPDF2
                                    reader = PyPDF2.PdfReader(io.BytesIO(uploaded.read()))
                                    text   = "\n".join(p.extract_text() or "" for p in reader.pages)
                                except Exception:
                                    st.error("Could not read PDF — try copy-pasting text via Manual Entry.")
                        elif uploaded.name.endswith(".docx"):
                            try:
                                import docx as dx
                                doc  = dx.Document(io.BytesIO(uploaded.read()))
                                text = "\n".join(p.text for p in doc.paragraphs)
                            except Exception:
                                st.error("Could not read DOCX — install python-docx.")
                        else:
                            text = uploaded.read().decode("utf-8", errors="ignore")
                    except Exception as e:
                        st.error(f"Read error: {e}")

                    if text.strip():
                        ex = extract_with_ai(text)
                        st.session_state.clm_extracted = ex
                        st.success("✓ Extracted — review and save below")
                    else:
                        st.warning("No text found in file.")

            if st.session_state.get("clm_extracted"):
                ex = st.session_state.clm_extracted
                st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
                for key, label, _, _ in FIELDS:
                    val = ex.get(key)
                    if val and str(val) not in ("null", "None", ""):
                        st.markdown(
                            f'<div class="ext-row">'
                            f'<span class="ext-lbl">{label}</span>'
                            f'<span class="ext-val">{val}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                cname = st.text_input(
                    "Contract name / reference", key="clm_ext_name",
                    placeholder="e.g. MSA – Acme Corp 2025",
                )
                if st.button("✓ Save Contract", use_container_width=True, key="save_ext"):
                    if cname.strip():
                        entry          = dict(ex)
                        entry["name"]  = cname.strip()
                        entry["added"] = str(date.today())
                        contracts.append(entry)
                        save_contracts(contracts)
                        st.session_state.clm_extracted = None
                        st.session_state.clm_insight   = None
                        st.success("Contract saved.")
                        st.rerun()
                    else:
                        st.warning("Enter a contract name first.")

        with tab_man:
            with st.form("clm_form", clear_on_submit=True):
                name = st.text_input("Contract Name *", placeholder="e.g. SLA – TechCorp 2025")
                for key, label, ftype, hint in FIELDS:
                    if hint:
                        st.caption(hint)
                    if ftype == "text":
                        st.text_input(label, key=f"cf_{key}")
                    elif ftype == "number":
                        st.number_input(label, min_value=0, value=0, key=f"cf_{key}")
                    elif ftype == "date":
                        st.date_input(label, key=f"cf_{key}")
                    elif ftype == "select":
                        st.selectbox(label, hint, key=f"cf_{key}")

                if st.form_submit_button("+ Add Contract", use_container_width=True):
                    if not name.strip():
                        st.warning("Contract name required.")
                    else:
                        entry = {"name": name.strip(), "added": str(date.today())}
                        for key, _, ftype, _ in FIELDS:
                            v = st.session_state.get(f"cf_{key}")
                            entry[key] = str(v) if ftype == "date" and v else v
                        contracts.append(entry)
                        save_contracts(contracts)
                        st.session_state.clm_insight = None
                        st.success(f"✓ {name} added.")
                        st.rerun()

    # ── MID — Contract List ────────────────────────────────────────────────────
    with mid:
        st.markdown('<div class="sec-hdr">All Contracts</div>', unsafe_allow_html=True)
        if not contracts:
            st.markdown("""
            <div style="text-align:center;padding:50px 20px;color:#4a6080;
                        font-size:0.78rem;font-family:'Space Mono',monospace">
              No contracts yet.<br>
              <span style="color:#2a3a4e;font-size:0.68rem">
                Upload or add one on the left.
              </span>
            </div>""", unsafe_allow_html=True)
        else:
            ft1, ft2, ft3, ft4 = st.tabs(["All", "Active", "Expiring", "Expired"])
            fmap = {
                "All":      contracts,
                "Active":   [c for c in contracts if contract_status(c)[0] == "active"],
                "Expiring": [c for c in contracts if contract_status(c)[0] == "expiring"],
                "Expired":  [c for c in contracts if contract_status(c)[0] == "expired"],
            }
            for tab, lbl in [(ft1,"All"),(ft2,"Active"),(ft3,"Expiring"),(ft4,"Expired")]:
                with tab:
                    shown = fmap[lbl]
                    if not shown:
                        st.caption("None in this category.")
                    for c in shown:
                        status, stxt = contract_status(c)
                        val  = float(c.get("contract_value",    0) or 0)
                        pay  = c.get("payment_terms_days", "—")
                        jur  = c.get("jurisdiction",       "—")
                        disp = c.get("dispute_resolution", "—")
                        liab = float(c.get("liability_cap_usd", 0) or 0)
                        st.markdown(f"""
                        <div class="crow {status}">
                          <div style="display:flex;justify-content:space-between;
                                      align-items:flex-start;margin-bottom:6px">
                            <div class="cname">{c.get("name","Unnamed")}</div>
                            <span class="pill pill-{status}">{status}</span>
                          </div>
                          <div style="display:flex;gap:18px;flex-wrap:wrap">
                            <div><div class="cmeta">VALUE</div>
                              <div style="font-size:0.76rem;color:#eef2f7;
                                font-family:'Space Mono',monospace">${val:,.0f}</div></div>
                            <div><div class="cmeta">PAYMENT</div>
                              <div style="font-size:0.76rem;color:#eef2f7;
                                font-family:'Space Mono',monospace">{pay}d</div></div>
                            <div><div class="cmeta">LIABILITY CAP</div>
                              <div style="font-size:0.76rem;color:#eef2f7;
                                font-family:'Space Mono',monospace">${liab:,.0f}</div></div>
                            <div><div class="cmeta">JURISDICTION</div>
                              <div style="font-size:0.76rem;color:#eef2f7">{jur}</div></div>
                            <div><div class="cmeta">DISPUTE</div>
                              <div style="font-size:0.76rem;color:#eef2f7">{disp}</div></div>
                            <div><div class="cmeta">STATUS</div>
                              <div style="font-size:0.7rem;color:#8a9bb0">{stxt}</div></div>
                          </div>
                        </div>""", unsafe_allow_html=True)
                        real_idx = contracts.index(c)
                        if st.button("✕ Remove", key=f"del_{real_idx}_{lbl}"):
                            contracts.pop(real_idx)
                            save_contracts(contracts)
                            st.session_state.clm_insight = None
                            st.rerun()

    # ── RIGHT — Analytics ──────────────────────────────────────────────────────
    with right:
        st.markdown('<div class="sec-hdr">Risk Analytics</div>', unsafe_allow_html=True)
        if not contracts:
            st.markdown("""
            <div style="text-align:center;padding:30px;color:#4a6080;
                        font-size:0.75rem;font-family:'Space Mono',monospace">
              Add contracts to see analytics.
            </div>""", unsafe_allow_html=True)
        else:
            def bars(title, items):
                st.markdown(f'<div style="font-size:0.7rem;font-weight:600;color:#8a9bb0;'
                            f'margin-bottom:8px">{title}</div>', unsafe_allow_html=True)
                for label, count, color in items:
                    pct = int((count / total) * 100) if total else 0
                    st.markdown(f"""
                    <div style="margin-bottom:8px">
                      <div style="display:flex;justify-content:space-between;
                                  font-size:0.67rem;color:#8a9bb0;margin-bottom:3px">
                        <span>{label}</span><span>{count} ({pct}%)</span>
                      </div>
                      <div class="rbar-wrap">
                        <div class="rbar-fill" style="width:{pct}%;background:{color}"></div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

            # Payment terms spread — cash flow indicator
            bk = {"≤30d":[0,"#4ade80"],"31–60d":[0,"#fbbf24"],
                  "61–90d":[0,"#fb923c"],">90d":[0,"#f87171"]}
            for c in contracts:
                d = float(c.get("payment_terms_days", 0) or 0)
                if   d <= 30: bk["≤30d"][0]  += 1
                elif d <= 60: bk["31–60d"][0] += 1
                elif d <= 90: bk["61–90d"][0] += 1
                else:         bk[">90d"][0]   += 1
            bars("Payment Terms (Cash Flow)", [(k,v[0],v[1]) for k,v in bk.items()])

            # Jurisdiction concentration
            jc = {}
            for c in contracts:
                j = c.get("jurisdiction", "Unknown") or "Unknown"
                jc[j] = jc.get(j, 0) + 1
            bars("Jurisdiction Concentration",
                 [(j, n, "#60a5fa") for j, n in sorted(jc.items(), key=lambda x: -x[1])[:5]])

            # Dispute resolution mix
            dc, dc_col = {}, {"Litigation":"#f87171","Arbitration":"#fbbf24",
                               "Mediation":"#4ade80","Negotiation":"#60a5fa"}
            for c in contracts:
                d = c.get("dispute_resolution", "Unknown") or "Unknown"
                dc[d] = dc.get(d, 0) + 1
            bars("Dispute Resolution Mix",
                 [(d, n, dc_col.get(d,"#94a3b8")) for d,n in sorted(dc.items(), key=lambda x:-x[1])])

            # Liability heatmap — top 5 by exposure
            st.markdown('<div style="font-size:0.7rem;font-weight:600;color:#8a9bb0;'
                        'margin-bottom:8px">Liability Exposure (Top 5)</div>',
                        unsafe_allow_html=True)
            sc = sorted(contracts,
                        key=lambda x: float(x.get("liability_cap_usd", 0) or 0),
                        reverse=True)
            ml = float(sc[0].get("liability_cap_usd", 1) or 1) if sc else 1
            for c in sc[:5]:
                l   = float(c.get("liability_cap_usd", 0) or 0)
                pct = int((l / ml) * 100) if ml else 0
                col = "#f87171" if pct > 70 else "#fbbf24" if pct > 40 else "#4ade80"
                st.markdown(f"""
                <div style="margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;
                              font-size:0.67rem;color:#8a9bb0;margin-bottom:3px">
                    <span style="color:#eef2f7">{c.get("name","?")[:22]}</span>
                    <span>${l:,.0f}</span>
                  </div>
                  <div class="rbar-wrap">
                    <div class="rbar-fill" style="width:{pct}%;background:{col}"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

            # Term timeline — what's ending soon
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.7rem;font-weight:600;color:#8a9bb0;'
                        'margin-bottom:8px">Contract Timeline</div>', unsafe_allow_html=True)
            sorted_by_end = []
            for c in contracts:
                s, stxt = contract_status(c)
                sorted_by_end.append((c.get("name","?"), s, stxt))
            sorted_by_end = sorted(sorted_by_end, key=lambda x: x[1])
            for name, status, stxt in sorted_by_end[:6]:
                dot_col = {"active":"#4ade80","expiring":"#fbbf24","expired":"#4a6080"}.get(status,"#94a3b8")
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:5px 0;
                            border-bottom:1px solid #131920;font-size:0.72rem">
                  <span style="width:7px;height:7px;border-radius:50%;
                    background:{dot_col};display:inline-block;flex-shrink:0"></span>
                  <span style="color:#eef2f7;flex:1">{name[:24]}</span>
                  <span style="color:#4a6080;font-family:'Space Mono',monospace;
                    font-size:0.62rem">{stxt}</span>
                </div>""", unsafe_allow_html=True)

            st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

            # AI Insight
            st.markdown('<div class="sec-hdr">Eagle Legal Insight</div>',
                        unsafe_allow_html=True)
            if st.button("⚡ Generate AI Insight", use_container_width=True,
                         key="clm_insight_btn"):
                with st.spinner("Analysing contract portfolio..."):
                    st.session_state.clm_insight = gen_insight(contracts)
            if st.session_state.get("clm_insight"):
                st.markdown(
                    f'<div class="insight-box">{st.session_state.clm_insight}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
