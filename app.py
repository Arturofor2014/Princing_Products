import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="Brand Pricing & Profitability",
    layout="wide",
    page_icon="🏷️",
    initial_sidebar_state="expanded",
)

# ── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main .block-container { max-width: 1600px; padding-top: 1rem; }
.kpi-card {
    background: linear-gradient(135deg,#ffffff 0%,#f5f8ff 100%);
    border-radius: 12px; padding: 16px 10px;
    box-shadow: 0 2px 12px rgba(0,82,255,.08);
    text-align: center; margin-bottom: 10px;
    min-height: 105px; display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    border-top: 3px solid #0052FF;
}
.kpi-card.green  { border-top-color: #00C48C; }
.kpi-card.red    { border-top-color: #EF4444; }
.kpi-card.orange { border-top-color: #F59E0B; }
.kpi-label { font-size:10px; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:1px; }
.kpi-val        { font-size:22px; font-weight:900; color:#0052FF; margin:5px 0 2px; }
.kpi-val.green  { color:#00C48C; }
.kpi-val.red    { color:#EF4444; }
.kpi-val.orange { color:#F59E0B; }
.kpi-sub { font-size:10px; color:#9CA3AF; }
.section-hdr {
    font-size:12px; font-weight:800; color:#0052FF;
    letter-spacing:2px; text-transform:uppercase;
    border-left:4px solid #0052FF; padding-left:10px; margin:18px 0 10px;
}
.page-title { font-size:28px; font-weight:900; color:#111827; }
.page-title span { color:#0052FF; }
.page-sub { font-size:13px; color:#6B7280; margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ── HELPERS ──────────────────────────────────────────────────────────────────
def fusd(v, d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"(${abs(v):,.{d}f})" if v < 0 else f"${v:,.{d}f}"

def fpct(v):
    return f"{v*100:.1f}%" if (v is not None and not np.isnan(v)) else "-"

def kpi_card(label, value, sub="", color="blue"):
    cc = {"blue":"","green":"green","red":"red","orange":"orange"}.get(color,"")
    return (f'<div class="kpi-card {cc}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-val {cc}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div></div>')

def mc(v):
    if v >= 0.40: return "green"
    if v >= 0.20: return "orange"
    return "red"

CATEGORIES = ["Sneakers","Moda / Apparel","Cosméticos","Electrónica","Accesorios","Otro"]
PROD_COLORS = ["#0052FF","#00C48C","#F59E0B","#EF4444","#8B5CF6","#EC4899","#06B6D4","#10B981"]

# ── SIDEBAR: BRAND & SHARED SETTINGS ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏷️ Marca & Configuración")

    brand_name = st.text_input("Nombre de la Marca", "BRAND X")

    st.divider()
    st.markdown("### 🚢 Logística (compartida)")
    freight_pct   = st.slider("Flete % FOB",                 0.0, 50.0, 12.0, 0.5) / 100
    insurance_pct = st.slider("Seguro % FOB",                0.0,  5.0,  0.5, 0.1) / 100
    tariff_pct    = st.slider("Arancel Base % CIF",          0.0, 50.0, 15.0, 0.5) / 100
    local_frt_pct = st.slider("Flete Local % CIF",           0.0, 20.0,  5.0, 0.5) / 100
    broker_fee    = st.number_input("Agente Aduanal (USD/u)",value=1.50, step=0.10, format="%.2f")
    port_misc     = st.number_input("Puerto / Misc (USD/u)", value=0.50, step=0.10, format="%.2f")

    st.divider()
    st.markdown("### 🏢 Costos Operativos (compartidos)")
    royalty_pct   = st.slider("Royalties % Revenue",         0.0, 20.0,  5.0, 0.5) / 100
    marketing_pct = st.slider("Marketing & Ads %",           0.0, 30.0,  8.0, 0.5) / 100
    warehouse_pct = st.slider("Almacén %",                   0.0, 15.0,  3.0, 0.5) / 100
    platform_pct  = st.slider("Comisión Plataforma %",       0.0, 25.0,  0.0, 0.5) / 100
    returns_pct   = st.slider("Devoluciones %",              0.0, 30.0,  5.0, 1.0) / 100
    payment_pct   = st.slider("Procesamiento Pago %",        0.0,  5.0,  2.5, 0.1) / 100
    total_opex_pct = royalty_pct + marketing_pct + warehouse_pct + platform_pct + returns_pct + payment_pct

    st.divider()
    st.markdown("### 🧾 Impuestos")
    vat_pct = st.slider("IVA %",                 0.0, 25.0, 13.0, 0.5) / 100
    isr_pct = st.slider("Impuesto s/ Renta %",   0.0, 40.0, 25.0, 1.0) / 100

# ── HEADER ───────────────────────────────────────────────────────────────────
ct, cd = st.columns([5, 2])
with ct:
    st.markdown(f'<div class="page-title">🏷️ <span>{brand_name}</span> — Portfolio Pricing</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Multi-producto · P&L Consolidado · Comparativa de Márgenes · Análisis de Mix</div>',
                unsafe_allow_html=True)
with cd:
    st.markdown(f"<div style='text-align:right;padding-top:14px;font-size:11px;color:#9CA3AF'>"
                f"v1.0 &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y')}</div>",
                unsafe_allow_html=True)
st.divider()

# ── PRODUCT TABLE ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">PRODUCTOS — Edita · Agrega · Elimina filas</div>',
            unsafe_allow_html=True)

if "products" not in st.session_state:
    st.session_state.products = pd.DataFrame([
        {"Producto": "Sneaker Air Pro X",   "Categoría": "Sneakers",        "FOB (USD)": 45.0,  "Precio (USD)": 120.0, "Descuento %": 0.0,  "Unidades": 500, "Arancel %": tariff_pct * 100},
        {"Producto": "Sandal Urban Slide",  "Categoría": "Moda / Apparel",  "FOB (USD)": 22.0,  "Precio (USD)":  65.0, "Descuento %": 5.0,  "Unidades": 300, "Arancel %": tariff_pct * 100},
        {"Producto": "Cap Logo Premium",    "Categoría": "Accesorios",      "FOB (USD)":  8.0,  "Precio (USD)":  35.0, "Descuento %": 0.0,  "Unidades": 200, "Arancel %": tariff_pct * 100},
        {"Producto": "Hoodie Essential",    "Categoría": "Moda / Apparel",  "FOB (USD)": 18.0,  "Precio (USD)":  80.0, "Descuento %": 10.0, "Unidades": 150, "Arancel %": tariff_pct * 100},
        {"Producto": "Perfume Signature",   "Categoría": "Cosméticos",      "FOB (USD)": 12.0,  "Precio (USD)":  55.0, "Descuento %": 0.0,  "Unidades": 400, "Arancel %": tariff_pct * 100},
    ])

edited_df = st.data_editor(
    st.session_state.products,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    key="product_editor",
    column_config={
        "Producto":     st.column_config.TextColumn("Producto",     width=200),
        "Categoría":    st.column_config.SelectboxColumn("Categoría", options=CATEGORIES, width=160),
        "FOB (USD)":    st.column_config.NumberColumn("FOB (USD)",  format="$%.2f", min_value=0.01, width=110),
        "Precio (USD)": st.column_config.NumberColumn("Precio (USD)", format="$%.2f", min_value=0.01, width=120),
        "Descuento %":  st.column_config.NumberColumn("Descuento %", format="%.1f%%", min_value=0.0, max_value=100.0, width=110),
        "Unidades":     st.column_config.NumberColumn("Unidades",   format="%d", min_value=1, width=100),
        "Arancel %":    st.column_config.NumberColumn("Arancel %",  format="%.1f%%", min_value=0.0, max_value=100.0,
                                                       help="Deja el valor del sidebar o modifica por producto", width=110),
    },
)
st.session_state.products = edited_df
st.caption("💡 Arancel % puede ser diferente por producto (distinto código HS). Las demás tasas son de la marca.")

# ── CALCULATIONS ─────────────────────────────────────────────────────────────
def calc_product(row):
    fob       = float(row.get("FOB (USD)", 0) or 0)
    price     = float(row.get("Precio (USD)", 0) or 0)
    disc      = float(row.get("Descuento %", 0) or 0) / 100
    units     = int(row.get("Unidades", 0) or 0)
    ar_pct    = float(row.get("Arancel %", tariff_pct * 100) or tariff_pct * 100) / 100

    net_price = price * (1 - disc)
    ins       = fob * insurance_pct
    frt       = fob * freight_pct
    cif       = fob + frt + ins
    tariff_a  = cif * ar_pct
    local_frt = cif * local_frt_pct
    lc        = cif + tariff_a + local_frt + broker_fee + port_misc

    gp        = net_price - lc
    gm        = gp / net_price if net_price > 0 else 0

    opex_u    = net_price * total_opex_pct
    ebitda_u  = gp - opex_u
    ebitda_m  = ebitda_u / net_price if net_price > 0 else 0
    isr_a     = max(0.0, ebitda_u * isr_pct)
    net_u     = ebitda_u - isr_a
    nm        = net_u / net_price if net_price > 0 else 0
    mult      = net_price / lc if lc > 0 else 0

    return {
        "fob": fob, "cif": cif, "lc": lc, "net_price": net_price,
        "units": units, "gp": gp, "gm": gm,
        "opex_u": opex_u, "ebitda_u": ebitda_u, "ebitda_m": ebitda_m,
        "isr_a": isr_a, "net_u": net_u, "nm": nm, "mult": mult,
        "rev": net_price * units,
        "total_lc": lc * units,
        "total_gp": gp * units,
        "total_opex": opex_u * units,
        "total_ebitda": ebitda_u * units,
        "total_net": net_u * units,
        "royalty_u": net_price * royalty_pct,
        "marketing_u": net_price * marketing_pct,
        "warehouse_u": net_price * warehouse_pct,
        "platform_u": net_price * platform_pct,
        "returns_u": net_price * returns_pct,
        "payment_u": net_price * payment_pct,
    }

rows_valid = edited_df.dropna(subset=["Producto","FOB (USD)","Precio (USD)","Unidades"])
rows_valid = rows_valid[rows_valid["Unidades"] > 0]

calcs = [calc_product(r) for _, r in rows_valid.iterrows()]
names = rows_valid["Producto"].tolist()
cats  = rows_valid["Categoría"].tolist() if "Categoría" in rows_valid.columns else ["—"] * len(names)

if not calcs:
    st.warning("Agrega al menos un producto para ver el análisis.")
    st.stop()

# Brand totals
brand_rev      = sum(c["rev"] for c in calcs)
brand_lc       = sum(c["total_lc"] for c in calcs)
brand_gp       = sum(c["total_gp"] for c in calcs)
brand_opex     = sum(c["total_opex"] for c in calcs)
brand_ebitda   = sum(c["total_ebitda"] for c in calcs)
brand_net      = sum(c["total_net"] for c in calcs)
brand_units    = sum(c["units"] for c in calcs)
brand_gm       = brand_gp / brand_rev if brand_rev > 0 else 0
brand_ebitda_m = brand_ebitda / brand_rev if brand_rev > 0 else 0
brand_nm       = brand_net / brand_rev if brand_rev > 0 else 0

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Dashboard de Marca",
    "📈  Comparativa de Productos",
    "📋  P&L Consolidado",
    "🔬  Análisis de Mix",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD DE MARCA
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f'<div class="section-hdr">BRAND KPIs — {brand_name.upper()}</div>',
                unsafe_allow_html=True)

    k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
    k1.markdown(kpi_card("Productos",       str(len(calcs)),            f"{brand_units:,} unidades totales"), unsafe_allow_html=True)
    k2.markdown(kpi_card("Revenue Total",   fusd(brand_rev, 0),         "ex-IVA"), unsafe_allow_html=True)
    k3.markdown(kpi_card("Gross Profit",    fusd(brand_gp, 0),          fpct(brand_gm), mc(brand_gm)), unsafe_allow_html=True)
    k4.markdown(kpi_card("Margen Bruto",    fpct(brand_gm),             "brand average", mc(brand_gm)), unsafe_allow_html=True)
    k5.markdown(kpi_card("EBITDA",          fusd(brand_ebitda, 0),      fpct(brand_ebitda_m),
                          "green" if brand_ebitda >= 0 else "red"), unsafe_allow_html=True)
    k6.markdown(kpi_card("Utilidad Neta",   fusd(brand_net, 0),         fpct(brand_nm),
                          "green" if brand_net >= 0 else "red"), unsafe_allow_html=True)
    best_idx = max(range(len(calcs)), key=lambda i: calcs[i]["nm"])
    k7.markdown(kpi_card("Mejor Producto",  names[best_idx],            f"Net: {fpct(calcs[best_idx]['nm'])}", "green"), unsafe_allow_html=True)

    st.divider()

    cl, cr = st.columns(2)

    # Revenue & Net Profit by product — grouped bar
    with cl:
        st.markdown('<div class="section-hdr">REVENUE VS UTILIDAD NETA POR PRODUCTO</div>',
                    unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Revenue", x=names,
            y=[c["rev"] for c in calcs],
            marker_color=[PROD_COLORS[i % len(PROD_COLORS)] for i in range(len(calcs))],
            opacity=0.75,
            hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<extra></extra>",
        ))
        fig_bar.add_trace(go.Bar(
            name="Utilidad Neta", x=names,
            y=[c["total_net"] for c in calcs],
            marker_color=["#00C48C" if c["total_net"] >= 0 else "#EF4444" for c in calcs],
            hovertemplate="%{x}<br>Utilidad: $%{y:,.0f}<extra></extra>",
        ))
        fig_bar.update_layout(
            height=360, barmode="group",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0,r=0,t=10,b=60),
            yaxis=dict(title="USD", gridcolor="#F3F4F6", tickformat="$,.0f"),
            xaxis=dict(tickangle=-20, tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.22),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Margin comparison — horizontal bar
    with cr:
        st.markdown('<div class="section-hdr">MÁRGENES POR PRODUCTO</div>', unsafe_allow_html=True)
        fig_mg = go.Figure()
        fig_mg.add_trace(go.Bar(
            name="Margen Bruto",
            y=names, x=[c["gm"] * 100 for c in calcs],
            orientation="h",
            marker_color="#93C5FD",
            hovertemplate="%{y}<br>Margen Bruto: %{x:.1f}%<extra></extra>",
        ))
        fig_mg.add_trace(go.Bar(
            name="Margen Neto",
            y=names, x=[c["nm"] * 100 for c in calcs],
            orientation="h",
            marker_color=["#00C48C" if c["nm"] >= 0 else "#EF4444" for c in calcs],
            hovertemplate="%{y}<br>Margen Neto: %{x:.1f}%<extra></extra>",
        ))
        fig_mg.add_vline(x=brand_gm * 100, line_dash="dash", line_color="#0052FF",
                         annotation_text=f"Brand GM: {brand_gm*100:.1f}%",
                         annotation_font_size=9)
        fig_mg.update_layout(
            height=360, barmode="group",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0,r=20,t=10,b=30),
            xaxis=dict(title="Margen %", gridcolor="#F3F4F6", ticksuffix="%"),
            yaxis=dict(tickfont=dict(size=10)),
            legend=dict(orientation="h", y=-0.12),
        )
        st.plotly_chart(fig_mg, use_container_width=True)

    # Revenue mix pie
    st.divider()
    c_pie1, c_pie2 = st.columns(2)

    with c_pie1:
        st.markdown('<div class="section-hdr">MIX DE REVENUE POR PRODUCTO</div>', unsafe_allow_html=True)
        fig_p1 = go.Figure(go.Pie(
            labels=names, values=[c["rev"] for c in calcs],
            hole=0.50,
            marker=dict(colors=PROD_COLORS[:len(calcs)]),
            textinfo="label+percent",
            textfont=dict(size=10),
            hovertemplate="%{label}<br>Revenue: $%{value:,.0f} (%{percent})<extra></extra>",
        ))
        fig_p1.update_layout(
            height=320, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="white",
            legend=dict(orientation="v", font=dict(size=9), x=1.02),
            annotations=[dict(text=f"<b>{fusd(brand_rev, 0)}</b>", x=0.5, y=0.5,
                               font_size=13, showarrow=False)],
        )
        st.plotly_chart(fig_p1, use_container_width=True)

    with c_pie2:
        st.markdown('<div class="section-hdr">CONTRIBUCIÓN A UTILIDAD NETA</div>', unsafe_allow_html=True)
        pos_calcs = [(n, c) for n, c in zip(names, calcs) if c["total_net"] > 0]
        if pos_calcs:
            fig_p2 = go.Figure(go.Pie(
                labels=[n for n, _ in pos_calcs],
                values=[c["total_net"] for _, c in pos_calcs],
                hole=0.50,
                marker=dict(colors=PROD_COLORS[:len(pos_calcs)]),
                textinfo="label+percent",
                textfont=dict(size=10),
                hovertemplate="%{label}<br>Utilidad: $%{value:,.0f} (%{percent})<extra></extra>",
            ))
            fig_p2.update_layout(
                height=320, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="white",
                legend=dict(orientation="v", font=dict(size=9), x=1.02),
                annotations=[dict(text=f"<b>{fusd(brand_net, 0)}</b>", x=0.5, y=0.5,
                                   font_size=13, showarrow=False)],
            )
            st.plotly_chart(fig_p2, use_container_width=True)
        else:
            st.info("Sin productos con utilidad neta positiva.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARATIVA DE PRODUCTOS
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-hdr">COMPARATIVA DETALLADA — TODOS LOS PRODUCTOS</div>',
                unsafe_allow_html=True)

    # Summary table
    rows_comp = []
    for name, cat, c in zip(names, cats, calcs):
        rows_comp.append({
            "Producto":         name,
            "Categoría":        cat,
            "FOB":              fusd(c["fob"]),
            "Landed Cost":      fusd(c["lc"]),
            "Precio Neto":      fusd(c["net_price"]),
            "Multiplicador":    f"{c['mult']:.2f}x",
            "Margen Bruto":     fpct(c["gm"]),
            "EBITDA / u":       fusd(c["ebitda_u"]),
            "Margen Neto":      fpct(c["nm"]),
            "Unidades":         f"{c['units']:,}",
            "Revenue Total":    fusd(c["rev"], 0),
            "Utilidad Neta":    fusd(c["total_net"], 0),
        })

    df_comp = pd.DataFrame(rows_comp)

    def hl_comp(row):
        idx = df_comp.index.get_loc(row.name)
        c = calcs[idx]
        if c["nm"] == max(cc["nm"] for cc in calcs):
            return ["background-color:#D1FAE5;font-weight:bold"] * len(row)
        if c["nm"] < 0:
            return ["background-color:#FEE2E2"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_comp.style.apply(hl_comp, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Producto": st.column_config.TextColumn("Producto", width=200),
        },
    )
    st.caption("✅ Verde = mayor margen neto  |  🔴 Rojo = margen negativo")

    st.divider()

    # Stacked bar: cost structure per product
    st.markdown('<div class="section-hdr">ESTRUCTURA DE COSTOS POR PRODUCTO (por unidad)</div>',
                unsafe_allow_html=True)

    fig_stack = go.Figure()
    layers = [
        ("FOB",        [c["fob"] for c in calcs],        "#1E3A5F"),
        ("Logística",  [c["lc"] - c["fob"] for c in calcs], "#3B82F6"),
        ("OPEX",       [c["opex_u"] for c in calcs],     "#F59E0B"),
        ("EBITDA",     [max(0, c["ebitda_u"]) for c in calcs], "#00C48C"),
    ]
    for lbl, vals, clr in layers:
        fig_stack.add_trace(go.Bar(
            name=lbl, x=names, y=vals,
            marker_color=clr,
            hovertemplate=f"{lbl}<br>%{{x}}: $%{{y:.2f}}<extra></extra>",
        ))

    fig_stack.add_trace(go.Scatter(
        name="Precio Neto", x=names,
        y=[c["net_price"] for c in calcs],
        mode="markers+lines",
        marker=dict(symbol="diamond", size=10, color="#0052FF"),
        line=dict(dash="dot", color="#0052FF"),
        hovertemplate="Precio Neto<br>%{x}: $%{y:.2f}<extra></extra>",
        yaxis="y",
    ))

    fig_stack.update_layout(
        height=380, barmode="stack",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0,r=0,t=10,b=60),
        yaxis=dict(title="USD / unidad", gridcolor="#F3F4F6", tickformat="$,.0f"),
        xaxis=dict(tickangle=-15, tickfont=dict(size=10)),
        legend=dict(orientation="h", y=-0.22),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

    # Bubble: Revenue vs Net Margin
    st.markdown('<div class="section-hdr">REVENUE vs MARGEN NETO (burbuja = unidades)</div>',
                unsafe_allow_html=True)

    fig_bub = go.Figure()
    for i, (name, cat, c) in enumerate(zip(names, cats, calcs)):
        fig_bub.add_trace(go.Scatter(
            x=[c["rev"]], y=[c["nm"] * 100],
            mode="markers+text",
            name=name,
            text=[name],
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(
                size=max(10, c["units"] / 30),
                color=PROD_COLORS[i % len(PROD_COLORS)],
                opacity=0.8,
                line=dict(width=1, color="white"),
            ),
            hovertemplate=(f"<b>{name}</b><br>Revenue: $%{{x:,.0f}}<br>"
                           f"Margen Neto: %{{y:.1f}}%<br>Unidades: {c['units']:,}<extra></extra>"),
        ))

    fig_bub.add_hline(y=brand_nm * 100, line_dash="dash", line_color="#0052FF",
                      annotation_text=f"Brand avg: {brand_nm*100:.1f}%", annotation_font_size=9)
    fig_bub.add_hline(y=0, line_color="#EF4444", line_width=1)
    fig_bub.update_layout(
        height=380,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0,r=0,t=10,b=0),
        xaxis=dict(title="Revenue Total (USD)", gridcolor="#F3F4F6", tickformat="$,.0f"),
        yaxis=dict(title="Margen Neto %", gridcolor="#F3F4F6", ticksuffix="%"),
        showlegend=False,
    )
    st.plotly_chart(fig_bub, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — P&L CONSOLIDADO
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-hdr">P&L CONSOLIDADO — TODOS LOS PRODUCTOS</div>',
                unsafe_allow_html=True)

    DARK  = "background-color:#1E3A5F;color:white;font-weight:bold"
    MID   = "background-color:#DBEAFE;font-weight:bold"
    GREEN = "background-color:#D1FAE5;font-weight:bold"
    RED   = "background-color:#FEE2E2;font-weight:bold"
    SEP   = "background-color:#F9FAFB;color:#D1D5DB"

    def pnl_row(concepto, vals, totals, style=""):
        d = {"Concepto": concepto, "_style": style}
        for n, v in zip(names, vals):
            d[n] = v
        d["🏷️ TOTAL MARCA"] = totals
        return d

    def sep_row():
        return pnl_row("", [""] * len(calcs), "", SEP)

    pnl_rows = [
        pnl_row("📦  FOB",               [fusd(c["fob"]) for c in calcs],          fusd(sum(c["fob"]*c["units"] for c in calcs),0)),
        pnl_row("🚢  Flete + Seguro",    [fusd(c["cif"]-c["fob"]) for c in calcs], fusd(sum((c["cif"]-c["fob"])*c["units"] for c in calcs),0)),
        pnl_row("   CIF",               [fusd(c["cif"]) for c in calcs],           fusd(sum(c["cif"]*c["units"] for c in calcs),0), MID),
        pnl_row("📋  Arancel + Logística Local", [fusd(c["lc"]-c["cif"]) for c in calcs],
                fusd(sum((c["lc"]-c["cif"])*c["units"] for c in calcs),0)),
        pnl_row("   LANDED COST",       [fusd(c["lc"]) for c in calcs],            fusd(brand_lc,0), DARK),
        sep_row(),
        pnl_row("💲  Precio Neto",       [fusd(c["net_price"]) for c in calcs],    fusd(brand_rev,0)),
        pnl_row("   Multiplicador",     [f"{c['mult']:.2f}x" for c in calcs],      ""),
        sep_row(),
        pnl_row("💰  UTILIDAD BRUTA",   [fusd(c["gp"]) for c in calcs],            fusd(brand_gp,0),
                GREEN if brand_gp >= 0 else RED),
        pnl_row("   Margen Bruto %",    [fpct(c["gm"]) for c in calcs],            fpct(brand_gm), MID),
        sep_row(),
        pnl_row("👑  Royalties",         [fusd(c["royalty_u"]) for c in calcs],    fusd(sum(c["royalty_u"]*c["units"] for c in calcs),0)),
        pnl_row("📣  Marketing",         [fusd(c["marketing_u"]) for c in calcs],  fusd(sum(c["marketing_u"]*c["units"] for c in calcs),0)),
        pnl_row("🏭  Almacén",           [fusd(c["warehouse_u"]) for c in calcs],  fusd(sum(c["warehouse_u"]*c["units"] for c in calcs),0)),
        pnl_row("🛒  Plataforma",        [fusd(c["platform_u"]) for c in calcs],   fusd(sum(c["platform_u"]*c["units"] for c in calcs),0)),
        pnl_row("↩️  Devoluciones",      [fusd(c["returns_u"]) for c in calcs],    fusd(sum(c["returns_u"]*c["units"] for c in calcs),0)),
        pnl_row("💳  Pagos",             [fusd(c["payment_u"]) for c in calcs],    fusd(sum(c["payment_u"]*c["units"] for c in calcs),0)),
        pnl_row("   TOTAL OPEX",        [fusd(c["opex_u"]) for c in calcs],        fusd(brand_opex,0), DARK),
        sep_row(),
        pnl_row("📈  EBITDA",            [fusd(c["ebitda_u"]) for c in calcs],     fusd(brand_ebitda,0),
                GREEN if brand_ebitda >= 0 else RED),
        pnl_row("   Margen EBITDA %",   [fpct(c["ebitda_m"]) for c in calcs],      fpct(brand_ebitda_m), MID),
        pnl_row("🧾  ISR",               [fusd(c["isr_a"]) for c in calcs],         fusd(sum(c["isr_a"]*c["units"] for c in calcs),0)),
        pnl_row("✅  UTILIDAD NETA",    [fusd(c["net_u"]) for c in calcs],         fusd(brand_net,0),
                GREEN if brand_net >= 0 else RED),
        pnl_row("   Margen Neto %",     [fpct(c["nm"]) for c in calcs],             fpct(brand_nm), MID),
        sep_row(),
        pnl_row("📦  Unidades",          [f"{c['units']:,}" for c in calcs],        f"{brand_units:,}"),
        pnl_row("💵  Revenue Total",     [fusd(c["rev"],0) for c in calcs],         fusd(brand_rev,0), MID),
        pnl_row("✅  Utilidad Neta Tot.", [fusd(c["total_net"],0) for c in calcs],  fusd(brand_net,0),
                GREEN if brand_net >= 0 else RED),
    ]

    df_pnl = pd.DataFrame(pnl_rows)
    styles_pnl = df_pnl["_style"].tolist()
    df_pnl_disp = df_pnl.drop(columns="_style")

    def apply_pnl_style(row_):
        return [styles_pnl[row_.name]] * len(row_)

    st.dataframe(
        df_pnl_disp.style.apply(apply_pnl_style, axis=1),
        use_container_width=True,
        hide_index=True,
        height=700,
        column_config={
            "Concepto": st.column_config.TextColumn("Concepto", width=240),
            "🏷️ TOTAL MARCA": st.column_config.TextColumn("🏷️ TOTAL MARCA", width=140),
        },
    )

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANÁLISIS DE MIX
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-hdr">ANÁLISIS DE MIX — CONTRIBUCIÓN Y EFICIENCIA</div>',
                unsafe_allow_html=True)

    # Contribution table
    mix_rows = []
    for name, cat, c in zip(names, cats, calcs):
        rev_mix  = c["rev"] / brand_rev * 100 if brand_rev > 0 else 0
        net_mix  = c["total_net"] / brand_net * 100 if brand_net > 0 else 0
        mix_rows.append({
            "Producto":          name,
            "Categoría":         cat,
            "Unidades":          f"{c['units']:,}",
            "Revenue":           fusd(c["rev"], 0),
            "Mix Revenue %":     f"{rev_mix:.1f}%",
            "Utilidad Neta":     fusd(c["total_net"], 0),
            "Contribución Utl %": f"{net_mix:.1f}%",
            "Margen Bruto":      fpct(c["gm"]),
            "Margen Neto":       fpct(c["nm"]),
            "Eficiencia":        f"{(c['total_net'] / c['rev'] * 100):.1f}%" if c["rev"] > 0 else "-",
        })

    df_mix = pd.DataFrame(mix_rows)

    def hl_mix(row):
        idx = df_mix.index.get_loc(row.name)
        if calcs[idx]["nm"] == max(cc["nm"] for cc in calcs):
            return ["background-color:#D1FAE5;font-weight:bold"] * len(row)
        if calcs[idx]["rev"] == max(cc["rev"] for cc in calcs):
            return ["background-color:#DBEAFE;font-weight:bold"] * len(row)
        return [""] * len(row)

    st.dataframe(df_mix.style.apply(hl_mix, axis=1),
                 use_container_width=True, hide_index=True)
    st.caption("✅ Verde = mayor margen neto  |  🔵 Azul = mayor revenue")

    st.divider()

    # Waterfall brand P&L
    st.markdown('<div class="section-hdr">CASCADA P&L — MARCA CONSOLIDADA</div>',
                unsafe_allow_html=True)

    wf_x = ["Revenue", "Landed\nCost", "Royalties", "Marketing", "Almacén",
             "Plataforma", "Pagos", "Devoluciones", "EBITDA", "ISR", "Utilidad\nNeta"]
    wf_y = [brand_rev,
            -brand_lc,
            -sum(c["royalty_u"]   * c["units"] for c in calcs),
            -sum(c["marketing_u"] * c["units"] for c in calcs),
            -sum(c["warehouse_u"] * c["units"] for c in calcs),
            -sum(c["platform_u"]  * c["units"] for c in calcs),
            -sum(c["payment_u"]   * c["units"] for c in calcs),
            -sum(c["returns_u"]   * c["units"] for c in calcs),
            0, 0, 0]
    wf_m = ["absolute","relative","relative","relative","relative",
            "relative","relative","relative","total","relative","total"]
    wf_t = [fusd(brand_rev,0), fusd(brand_lc,0),
            fusd(sum(c["royalty_u"]*c["units"] for c in calcs),0),
            fusd(sum(c["marketing_u"]*c["units"] for c in calcs),0),
            fusd(sum(c["warehouse_u"]*c["units"] for c in calcs),0),
            fusd(sum(c["platform_u"]*c["units"] for c in calcs),0),
            fusd(sum(c["payment_u"]*c["units"] for c in calcs),0),
            fusd(sum(c["returns_u"]*c["units"] for c in calcs),0),
            fusd(brand_ebitda,0),
            fusd(sum(c["isr_a"]*c["units"] for c in calcs),0),
            fusd(brand_net,0)]

    # ISR relative value
    wf_y[9] = -sum(c["isr_a"] * c["units"] for c in calcs)

    fig_wfall = go.Figure(go.Waterfall(
        orientation="v", measure=wf_m,
        x=wf_x, y=wf_y,
        text=wf_t, textposition="outside", textfont=dict(size=9),
        connector=dict(line=dict(color="#E5E7EB", width=1)),
        decreasing=dict(marker=dict(color="#EF4444")),
        increasing=dict(marker=dict(color="#60A5FA")),
        totals=dict(marker=dict(color="#00C48C" if brand_net >= 0 else "#EF4444")),
    ))
    fig_wfall.update_layout(
        height=420, margin=dict(l=0,r=10,t=20,b=0),
        plot_bgcolor="white", paper_bgcolor="white",
        yaxis=dict(title="USD (Marca)", gridcolor="#F3F4F6", tickformat="$,.0f"),
        xaxis=dict(tickfont=dict(size=10)),
        showlegend=False,
    )
    st.plotly_chart(fig_wfall, use_container_width=True)
