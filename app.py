# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =============================================================================
# 1) PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Анализ успеваемости",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global constants
OUTCOME_COL = "Итоговый балл"

# Columns by theme (use only those that exist in df)
GEO_COLS = ["Область", "Район", "Организация"]
DEMOGRAPHIC_COLS = ["Пол", "Национальность", "ethnicity", "Возраст", "Возрастная группа"]
PROF_COLS = ["Курс", "Форма собственности", "Тип школы", "Учёная степень", "Ученая степень", "Категория", "Должность", "Предмет"]

# =============================================================================
# 2) HELPERS
# =============================================================================
def to_str_null(x):
    """Show NaN/None as 'NULL' for categorical display while preserving values for grouping/filters."""
    if pd.isna(x):
        return "NULL"
    return str(x)

def order_degree(series: pd.Series) -> pd.Categorical:
    """
    Ensure proper ordering for academic degree (supports both spellings).
    """
    order = [
        "PhD",
        "кандидат",
        "доктор наук",
        "доктор по профилю",
        "магистр",
        "не имеет степени",
        "Значение не указано",
        "NULL",
    ]
    s = series.astype(str).replace({"nan": "NULL", "None": "NULL"})
    s = s.replace({"Ученая степень": "Учёная степень"})  # light harmonization
    # Normalize common variants (case-insensitive matching)
    s_norm = s.str.strip().str.lower()
    mapping = {
        "phd": "PhD",
        "кандидат": "кандидат",
        "доктор наук": "доктор наук",
        "доктор по профилю": "доктор по профилю",
        "магистр": "магистр",
        "не имеет степени": "не имеет степени",
        "значение не указано": "Значение не указано",
        "null": "NULL",
    }
    s_mapped = s_norm.map(mapping).fillna(s)  # fall back to original if unseen
    cat = pd.Categorical(s_mapped, categories=order, ordered=True)
    return cat

def order_age_group(series: pd.Series) -> pd.Categorical:
    """
    Order age groups like '10-19, 20-29, 30-39 ...' robustly (handles mixed formats).
    """
    s = series.fillna("NULL").astype(str)
    # Extract numeric start of range for sorting; unknown -> large sentinel
    starts = s.str.extract(r"(\d+)\s*-\s*(\d+)")
    starts = starts[0].astype(float)
    order = s.groupby(s).agg(lambda g: g.index.min()).sort_values(key=lambda idx: starts.loc[idx].fillna(1e9)).index.tolist()
    # Put NULL last
    if "NULL" in order:
        order = [x for x in order if x != "NULL"] + ["NULL"]
    return pd.Categorical(s, categories=order, ordered=True)

def numeric_series(df, col):
    try:
        return pd.to_numeric(df[col], errors="coerce")
    except Exception:
        return pd.Series(index=df.index, dtype="float")

@st.cache_data(show_spinner=False)
def load_data(file_path="df.xlsx") -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Файл данных не найден. Убедитесь, что '{file_path}' находится рядом с app.py.")
        return pd.DataFrame()

def available(df, cols):
    return [c for c in cols if c in df.columns]

def apply_geo_cascade(df, sel_obl, sel_rn, sel_org):
    f = df.copy()
    if "Область" in f.columns and sel_obl:
        f = f[f["Область"].astype(str).isin(sel_obl)]
    if "Район" in f.columns and sel_rn:
        f = f[f["Район"].astype(str).isin(sel_rn)]
    if "Организация" in f.columns and sel_org:
        f = f[f["Организация"].astype(str).isin(sel_org)]
    return f

def ensure_outcome(df):
    if OUTCOME_COL not in df.columns:
        st.error(f"В данных отсутствует столбец '{OUTCOME_COL}'.")
        st.stop()
    return df

def with_null_display_options(df, col):
    """Return sorted unique options (with 'NULL' shown) for multiselects."""
    vals = df[col] if col in df.columns else pd.Series([], dtype=object)
    return sorted(to_str_null(v) for v in vals.unique())

def filter_by_multiselect(df, col, chosen):
    if not chosen:
        return df
    # Convert df values to string with NULL for matching
    col_as_str = df[col].apply(to_str_null)
    return df[col_as_str.isin(chosen)]

@st.cache_data(show_spinner=False)
def agg_mean(df, by_cols):
    g = df.groupby(by_cols, dropna=False)[OUTCOME_COL].mean().reset_index()
    g[OUTCOME_COL] = g[OUTCOME_COL].round(2)
    return g

def kpi_card(label, value, help_text=None):
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(label, value)
    if help_text:
        with col2:
            st.caption(help_text)

# =============================================================================
# 3) LOAD + PREP
# =============================================================================
df = load_data()
if df.empty:
    st.stop()

df = ensure_outcome(df)

# Light normalization for degree spelling
if "Ученая степень" in df.columns and "Учёная степень" not in df.columns:
    df.rename(columns={"Ученая степень": "Учёная степень"}, inplace=True)

# Numeric casting
df[OUTCOME_COL] = numeric_series(df, OUTCOME_COL)
if "Возраст" in df.columns:
    df["Возраст"] = numeric_series(df, "Возраст")

# =============================================================================
# 4) SIDEBAR – FILTERS
# =============================================================================
st.sidebar.header("🔎 Фильтры")

# --- Geographic cascading filters ---
geo_cols_present = available(df, GEO_COLS)
if geo_cols_present:
    st.sidebar.subheader("География")
    # Область
    sel_obl = []
    if "Область" in geo_cols_present:
        opts_obl = sorted(df["Область"].dropna().astype(str).unique().tolist())
        sel_obl = st.sidebar.multiselect("Область", options=opts_obl, default=opts_obl)
    # Район depends on область
    filt1 = df if not sel_obl else df[df["Область"].astype(str).isin(sel_obl)]
    sel_rn = []
    if "Район" in geo_cols_present:
        opts_rn = sorted(filt1["Район"].dropna().astype(str).unique().tolist())
        sel_rn = st.sidebar.multiselect("Район", options=opts_rn, default=opts_rn)
    # Организация depends on район
    filt2 = filt1 if not sel_rn else filt1[filt1["Район"].astype(str).isin(sel_rn)]
    sel_org = []
    if "Организация" in geo_cols_present:
        opts_org = sorted(filt2["Организация"].dropna().astype(str).unique().tolist())
        sel_org = st.sidebar.multiselect("Организация", options=opts_org, default=opts_org)
else:
    sel_obl, sel_rn, sel_org = [], [], []

# --- Other filters (nominal/ordinal) ---
st.sidebar.subheader("Демография и профиль")
other_filters = {}
candidate_filters = available(
    df,
    ["Курс", "Форма собственности", "Тип школы", "Пол", "Национальность", "ethnicity",
     "Возрастная группа", "Учёная степень", "Категория", "Должность", "Предмет"]
)
for col in candidate_filters:
    if col == "Возраст":  # numeric; we’ll filter later as a range if needed
        continue
    # Prepare options with NULL visible
    opts = with_null_display_options(df, col)
    # Default = all
    other_filters[col] = st.sidebar.multiselect(col, options=opts, default=opts)

# Optional numeric filters
if "Возраст" in df.columns:
    st.sidebar.subheader("Возраст")
    vmin = int(np.nanmin(df["Возраст"])) if len(df["Возраст"].dropna()) else 0
    vmax = int(np.nanmax(df["Возраст"])) if len(df["Возраст"].dropna()) else 100
    sel_age = st.sidebar.slider("Диапазон возраста", min_value=vmin, max_value=vmax, value=(vmin, vmax))
else:
    sel_age = None

# --- Build filtered dataframe ---
filtered = apply_geo_cascade(df, sel_obl, sel_rn, sel_org)
for col, chosen in other_filters.items():
    filtered = filter_by_multiselect(filtered, col, chosen)

if sel_age and "Возраст" in filtered.columns:
    filtered = filtered[(filtered["Возраст"] >= sel_age[0]) & (filtered["Возраст"] <= sel_age[1])]

# Keep outcome not null
filtered = filtered[filtered[OUTCOME_COL].notna()]

# Guard empty
if filtered.empty:
    st.warning("Нет данных по выбранным фильтрам. Измените параметры слева.")
    st.stop()

# =============================================================================
# 5) HEADER + KPI
# =============================================================================
st.title("📊 Панель анализа успеваемости")
st.caption("Сравнение показателя «Итоговый балл» по различным стратам и иерархиям.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Количество записей", f"{len(filtered):,}".replace(",", " "))
with c2:
    st.metric("Средний итоговый балл", f"{filtered[OUTCOME_COL].mean():.2f}")
with c3:
    st.metric("Медиана", f"{filtered[OUTCOME_COL].median():.2f}")
with c4:
    st.metric("Ст. отклонение", f"{filtered[OUTCOME_COL].std(ddof=1):.2f}")

st.divider()

# =============================================================================
# 6) TABS
# =============================================================================
tab_overview, tab_geo, tab_demo, tab_prof, tab_compare, tab_data = st.tabs(
    ["Обзор", "География", "Демография", "Профиль", "Сравнение", "Данные"]
)

# --------------------------------------
# TAB: OVERVIEW
# --------------------------------------
with tab_overview:
    st.subheader("Распределение результатов")
    cc1, cc2 = st.columns([2, 1])

    with cc1:
        bins = st.slider("Количество бинов (гистограмма)", 10, 80, 30, key="bins_hist")
        fig_hist = px.histogram(
            filtered, x=OUTCOME_COL, nbins=bins, color_discrete_sequence=["#2a9d8f"]
        )
        fig_hist.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_hist, use_container_width=True)

    with cc2:
        fig_box = px.box(
            filtered, y=OUTCOME_COL, points="outliers", color_discrete_sequence=["#e76f51"]
        )
        fig_box.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("### Рейтинги по категориям")
    # Pick any existing categorical columns for ranking
    cat_cols = available(filtered, ["Курс", "Пол", "Тип школы", "Категория", "Должность", "Предмет", "Национальность", "ethnicity", "Форма собственности", "Возрастная группа"])
    rank_col = st.selectbox("Выберите категорию для ранжирования", options=cat_cols or [None])
    if rank_col:
        # Special ordering for ordinals
        gdf = filtered.copy()
        if rank_col == "Учёная степень":
            gdf[rank_col] = order_degree(gdf[rank_col])
        if rank_col == "Возрастная группа":
            gdf[rank_col] = order_age_group(gdf[rank_col])

        ranked = gdf.groupby(rank_col, dropna=False)[OUTCOME_COL].mean().round(2).reset_index().rename(columns={rank_col: "Группа"})
        ranked["Группа"] = ranked["Группа"].astype(str).replace({"nan": "NULL"})
        ranked = ranked.sort_values(OUTCOME_COL, ascending=True)

        h = max(400, 35 * len(ranked))
        fig_rank = px.bar(
            ranked, x=OUTCOME_COL, y="Группа", orientation="h",
            text=OUTCOME_COL, color=OUTCOME_COL, color_continuous_scale=px.colors.sequential.Tealgrn,
            height=h
        )
        fig_rank.update_layout(xaxis_title="Средний итоговый балл", yaxis_title=rank_col)
        st.plotly_chart(fig_rank, use_container_width=True)

# --------------------------------------
# TAB: GEOGRAPHY
# --------------------------------------
with tab_geo:
    st.subheader("Иерархия: Область → Район → Организация")

    geo_sel_cols = available(filtered, GEO_COLS)
    if not geo_sel_cols:
        st.info("Географические поля отсутствуют в данных.")
    else:
        # Sunburst/Treemap choice
        chart_type = st.radio("Тип диаграммы", ["Sunburst", "Treemap"], horizontal=True)
        path_cols = [c for c in GEO_COLS if c in filtered.columns]
        # convert to str for visual stability
        fgeo = filtered.copy()
        for c in path_cols:
            fgeo[c] = fgeo[c].astype(str).replace({"nan": "NULL"})

        if chart_type == "Sunburst":
            fig_sun = px.sunburst(
                fgeo, path=path_cols, values=None, color=OUTCOME_COL,
                color_continuous_scale=px.colors.sequential.Tealgrn,
                hover_data={OUTCOME_COL: ":.2f"},
            )
            fig_sun.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_sun, use_container_width=True)
        else:
            fig_tree = px.treemap(
                fgeo, path=path_cols, values=None, color=OUTCOME_COL,
                color_continuous_scale=px.colors.sequential.Tealgrn,
                hover_data={OUTCOME_COL: ":.2f"},
            )
            fig_tree.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)

        # Table of top/bottom regions by mean
        st.markdown("#### Средний балл по географии")
        geo_group_level = st.select_slider(
            "Уровень агрегации",
            options=[c for c in GEO_COLS if c in filtered.columns],
            value=path_cols[0] if path_cols else None
        )
        if geo_group_level:
            geo_mean = agg_mean(filtered, [geo_group_level]).sort_values(OUTCOME_COL, ascending=False)
            colA, colB = st.columns(2)
            with colA:
                st.write("**Топ-10**")
                st.dataframe(geo_mean.head(10), use_container_width=True)
            with colB:
                st.write("**Антилидеры-10**")
                st.dataframe(geo_mean.tail(10), use_container_width=True)

# --------------------------------------
# TAB: DEMOGRAPHICS
# --------------------------------------
with tab_demo:
    st.subheader("Демографические разрезы")
    dcols = available(filtered, ["Пол", "Национальность", "ethnicity", "Возрастная группа"])
    if not dcols:
        st.info("Демографические поля отсутствуют.")
    else:
        colX, colY = st.columns(2)
        with colX:
            d1 = st.selectbox("Первая категория", options=dcols, index=0)
        with colY:
            d2 = st.selectbox("Вторая категория (опционально)", options=["(нет)"] + dcols, index=0)
            d2 = None if d2 == "(нет)" else d2

        # Prepare ordered categories where needed
        f = filtered.copy()
        if "Возрастная группа" in f.columns:
            f["Возрастная группа"] = order_age_group(f["Возрастная группа"])
        if "Учёная степень" in f.columns:
            f["Учёная степень"] = order_degree(f["Учёная степень"])

        if d2:
            st.markdown("**Тепловая карта средних значений**")
            pivot = f.pivot_table(index=d1, columns=d2, values=OUTCOME_COL, aggfunc="mean")
            fig_hm = go.Figure(data=go.Heatmap(
                z=np.round(pivot.values, 2),
                x=[str(c) for c in pivot.columns],
                y=[str(i) for i in pivot.index],
                colorscale="Tealgrn",
                colorbar=dict(title="Среднее"),
                hoverongaps=False,
            ))
            fig_hm.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.markdown("**Распределение по выбранной категории**")
            fig_violin = px.violin(f, x=d1, y=OUTCOME_COL, box=True, points="all", color=d1)
            fig_violin.update_layout(xaxis_title=d1, yaxis_title=OUTCOME_COL)
            st.plotly_chart(fig_violin, use_container_width=True)

# --------------------------------------
# TAB: PROFESSIONAL
# --------------------------------------
with tab_prof:
    st.subheader("Профессиональные характеристики")
    pcols = available(filtered, ["Курс", "Форма собственности", "Тип школы", "Учёная степень", "Категория", "Должность", "Предмет"])
    if not pcols:
        st.info("Профессиональные поля отсутствуют.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            p1 = st.selectbox("Категория 1", options=pcols, index=0, key="prof1")
        with col2:
            p2 = st.selectbox("Категория 2 (опционально)", options=["(нет)"] + pcols, index=0, key="prof2")
            p2 = None if p2 == "(нет)" else p2

        # Focus/highlight: учитель/преподаватель
        highlight = st.checkbox("Подсветить учитель/преподаватель в графиках (если есть в данных)", value=True)
        f = filtered.copy()
        # order degree
        if "Учёная степень" in f.columns:
            f["Учёная степень"] = order_degree(f["Учёная степень"])

        if p2:
            st.markdown("**Средние по двум измерениям**")
            avg = f.groupby([p1, p2], dropna=False)[OUTCOME_COL].mean().round(2).reset_index()
            fig = px.bar(
                avg, x=p1, y=OUTCOME_COL, color=p2, barmode="group",
                text=OUTCOME_COL, color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("**Распределение/коробчатая диаграмма**")
            fig = px.box(f, x=p1, y=OUTCOME_COL, color=p1)
            st.plotly_chart(fig, use_container_width=True)

        # Dedicated view for Должность with highlight
        if "Должность" in f.columns:
            st.markdown("#### Должности — средний итоговый балл")
            avg_pos = f.groupby("Должность", dropna=False)[OUTCOME_COL].mean().round(2).reset_index()
            avg_pos["Должность"] = avg_pos["Должность"].astype(str).replace({"nan": "NULL"})
            avg_pos = avg_pos.sort_values(OUTCOME_COL)
            h = max(400, 30 * len(avg_pos))
            figp = px.bar(avg_pos, x=OUTCOME_COL, y="Должность", orientation="h",
                          text=OUTCOME_COL, color=OUTCOME_COL, color_continuous_scale=px.colors.sequential.Tealgrn, height=h)
            if highlight:
                # Add vertical line or bold annotation for учитель/преподаватель
                mask = avg_pos["Должность"].str.lower().str.contains("учитель|преподаватель", na=False)
                if mask.any():
                    y_vals = avg_pos.loc[mask, "Должность"].tolist()
                    for yv in y_vals:
                        figp.add_shape(type="rect", x0=avg_pos[OUTCOME_COL].min(), x1=avg_pos[OUTCOME_COL].max(),
                                       y0=avg_pos.index[avg_pos["Должность"] == yv][0] - 0.5,
                                       y1=avg_pos.index[avg_pos["Должность"] == yv][0] + 0.5,
                                       fillcolor="rgba(231, 111, 81, 0.15)", line_width=0)
            st.plotly_chart(figp, use_container_width=True)

# --------------------------------------
# TAB: COMPARISON
# --------------------------------------
with tab_compare:
    st.subheader("Сравнение двух страт")

    # Choose a primary dimension and two levels to compare
    all_cat_cols = available(filtered, list(set(cat_cols + pcols)) if 'cat_cols' in locals() and 'pcols' in locals() else available(filtered, DEMOGRAPHIC_COLS + PROF_COLS))
    if not all_cat_cols:
        st.info("Недостаточно категориальных полей для сравнения.")
    else:
        cmp_dim = st.selectbox("Измерение для сравнения", options=all_cat_cols)
        # Levels available (with NULL)
        levels = sorted(filtered[cmp_dim].apply(to_str_null).unique().tolist())
        ccol1, ccol2 = st.columns(2)
        with ccol1:
            lvl_a = st.selectbox("Страта A", options=levels, index=0)
        with ccol2:
            lvl_b = st.selectbox("Страта B", options=levels, index=min(1, len(levels)-1))

        # Secondary breakdown
        second_dim_options = [c for c in all_cat_cols if c != cmp_dim]
        second_dim = st.selectbox("Разбивка по (опционально)", options=["(нет)"] + second_dim_options)
        second_dim = None if second_dim == "(нет)" else second_dim

        def mask_level(dfX, col, lvl):
            return dfX[dfX[col].apply(to_str_null) == lvl]

        A = mask_level(filtered, cmp_dim, lvl_a).assign(_group="A")
        B = mask_level(filtered, cmp_dim, lvl_b).assign(_group="B")
        cmp_df = pd.concat([A, B], ignore_index=True)

        if cmp_df.empty:
            st.info("Нет данных для выбранных страт.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Средний (A)", f"{A[OUTCOME_COL].mean():.2f}")
            with c2:
                st.metric("Средний (B)", f"{B[OUTCOME_COL].mean():.2f}")
            with c3:
                delta = A[OUTCOME_COL].mean() - B[OUTCOME_COL].mean()
                st.metric("Δ A − B", f"{delta:+.2f}")

            if second_dim:
                avg2 = cmp_df.groupby(["_group", second_dim], dropna=False)[OUTCOME_COL].mean().round(2).reset_index()
                fig_cmp = px.bar(avg2, x=second_dim, y=OUTCOME_COL, color="_group", barmode="group",
                                 text=OUTCOME_COL, color_discrete_map={"A": "#2a9d8f", "B": "#e76f51"})
                st.plotly_chart(fig_cmp, use_container_width=True)
            else:
                fig_cmp2 = px.violin(cmp_df, x="_group", y=OUTCOME_COL, box=True, points="all",
                                     color="_group", color_discrete_map={"A": "#2a9d8f", "B": "#e76f51"})
                st.plotly_chart(fig_cmp2, use_container_width=True)

# --------------------------------------
# TAB: DATA & EXPORT
# --------------------------------------
with tab_data:
    st.subheader("Данные (после фильтрации)")
    show_cols = st.multiselect("Показать столбцы", options=list(filtered.columns), default=list(filtered.columns))
    st.dataframe(filtered[show_cols], use_container_width=True, height=450)

    csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Скачать отфильтрованные данные (CSV)",
        data=csv,
        file_name="filtered_data.csv",
        mime="text/csv",
    )

# =============================================================================
# 7) FOOTER NOTE
# =============================================================================
st.caption("💡 Советы: Используйте вкладки для быстрого доступа к нужным разрезам. В географическом разделе поддерживается иерархический drill-down.")
