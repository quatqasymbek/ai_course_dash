# app.py (lightweight version)
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="Анализ успеваемости", page_icon="📊", layout="wide")

OUTCOME = "Итоговый балл"

@st.cache_data
def load_data(path="df.xlsx"):
    try:
        return pd.read_excel(path)
    except FileNotFoundError:
        st.error(f"Файл {path} не найден.")
        return pd.DataFrame()

df = load_data()
if df.empty or OUTCOME not in df.columns:
    st.stop()

df[OUTCOME] = pd.to_numeric(df[OUTCOME], errors="coerce")

# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
st.sidebar.header("Фильтры")

# Geography cascade
sel_obl, sel_rn, sel_org = [], [], []
if "Область" in df.columns:
    opts = sorted(df["Область"].dropna().unique())
    sel_obl = st.sidebar.multiselect("Область", opts, default=opts)
if "Район" in df.columns and sel_obl:
    opts = sorted(df[df["Область"].isin(sel_obl)]["Район"].dropna().unique())
    sel_rn = st.sidebar.multiselect("Район", opts, default=opts)
if "Организация" in df.columns and sel_rn:
    opts = sorted(df[df["Район"].isin(sel_rn)]["Организация"].dropna().unique())
    sel_org = st.sidebar.multiselect("Организация", opts, default=opts)

# Apply filters
filtered = df.copy()
if sel_obl: filtered = filtered[filtered["Область"].isin(sel_obl)]
if sel_rn: filtered = filtered[filtered["Район"].isin(sel_rn)]
if sel_org: filtered = filtered[filtered["Организация"].isin(sel_org)]

if filtered.empty:
    st.warning("Нет данных для выбранных фильтров.")
    st.stop()

# =============================================================================
# KPIs
# =============================================================================
st.title("📊 Панель анализа успеваемости")

c1, c2, c3 = st.columns(3)
c1.metric("Записей", len(filtered))
c2.metric("Средний балл", f"{filtered[OUTCOME].mean():.2f}")
c3.metric("Медиана", f"{filtered[OUTCOME].median():.2f}")

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Обзор", "География", "Категории", "Сравнение", "Данные"])

# --- TAB 1: OVERVIEW ---
with tab1:
    st.subheader("Распределение баллов")
    c1, c2 = st.columns([2,1])
    with c1:
        st.plotly_chart(px.histogram(filtered, x=OUTCOME, nbins=30, color_discrete_sequence=["#2a9d8f"]), use_container_width=True)
    with c2:
        st.plotly_chart(px.box(filtered, y=OUTCOME, points="all", color_discrete_sequence=["#e76f51"]), use_container_width=True)

    st.subheader("Рейтинг по категории")
    cat_cols = [c for c in df.columns if c not in ["id", OUTCOME, "Область","Район","Организация"]]
    rank_col = st.selectbox("Выберите категорию", options=cat_cols)
    if rank_col:
        avg = filtered.groupby(rank_col)[OUTCOME].mean().reset_index().sort_values(OUTCOME)
        st.plotly_chart(px.bar(avg, x=OUTCOME, y=rank_col, orientation="h", color=OUTCOME, color_continuous_scale="Tealgrn"), use_container_width=True)

# --- TAB 2: GEOGRAPHY ---
with tab2:
    st.subheader("Средний балл по географии")
    geo_col = st.radio("Уровень", [c for c in ["Область","Район","Организация"] if c in filtered.columns])
    if geo_col:
        avg = filtered.groupby(geo_col)[OUTCOME].mean().reset_index().sort_values(OUTCOME)
        st.plotly_chart(px.bar(avg, x=OUTCOME, y=geo_col, orientation="h", color=OUTCOME, color_continuous_scale="Tealgrn"), use_container_width=True)

# --- TAB 3: CATEGORIES ---
with tab3:
    st.subheader("Разрез по категориям")
    col = st.selectbox("Выберите категорию", options=[c for c in df.columns if c not in ["id", OUTCOME]])
    if col:
        st.plotly_chart(px.box(filtered, x=col, y=OUTCOME, color=col), use_container_width=True)

# --- TAB 4: COMPARISON ---
with tab4:
    st.subheader("Сравнение двух страт")
    cmp_col = st.selectbox("Страта", options=[c for c in df.columns if c not in ["id", OUTCOME]])
    if cmp_col:
        levels = filtered[cmp_col].dropna().unique()
        if len(levels) >= 2:
            l1 = st.selectbox("Группа A", options=levels)
            l2 = st.selectbox("Группа B", options=[x for x in levels if x != l1])
            A = filtered[filtered[cmp_col]==l1][OUTCOME]
            B = filtered[filtered[cmp_col]==l2][OUTCOME]
            c1, c2, c3 = st.columns(3)
            c1.metric(f"{l1} среднее", f"{A.mean():.2f}")
            c2.metric(f"{l2} среднее", f"{B.mean():.2f}")
            c3.metric("Разница", f"{A.mean()-B.mean():+.2f}")
            st.plotly_chart(px.box(filtered[filtered[cmp_col].isin([l1,l2])], x=cmp_col, y=OUTCOME, color=cmp_col), use_container_width=True)

# --- TAB 5: DATA ---
with tab5:
    st.subheader("Отфильтрованные данные")
    st.dataframe(filtered, use_container_width=True)
    st.download_button("Скачать CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "filtered.csv", "text/csv")
