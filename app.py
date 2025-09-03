# app.py (static-first lightweight dashboard without statsmodels)
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

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
# TITLE
# =============================================================================
st.title("📊 Анализ успеваемости")
st.markdown("Ниже приведены ключевые статистики по полу, возрасту и областям.")

# =============================================================================
# OVERALL STATS
# =============================================================================
st.header("Общая статистика")
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Всего записей", f"{len(df):,}")

with c2:
    st.metric("Средний балл", f"{df[OUTCOME].mean():.2f}")

with c3:
    st.metric("Медианный балл", f"{df[OUTCOME].median():.2f}")

st.markdown("---") # Add a divider

# =============================================================================
# STATIC SECTION 1 — Пол
# =============================================================================
if "Пол" in df.columns:
    st.header("Статистика по полу")
    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            px.box(df, x="Пол", y=OUTCOME, color="Пол",
                   title="Распределение итогового балла по полу"),
            use_container_width=True
        )

    with c2:
        avg_gender = df.groupby("Пол")[OUTCOME].mean().reset_index()
        st.plotly_chart(
            px.bar(avg_gender, x="Пол", y=OUTCOME, color="Пол",
                   title="Средний итоговый балл по полу",
                   color_discrete_sequence=px.colors.sequential.Teal),
            use_container_width=True
        )

# =============================================================================
# STATIC SECTION 2 — Возраст
# =============================================================================
if "Возраст" in df.columns:
    st.header("Статистика по возрасту")

    # Scatter with rolling mean smoothing
    scatter = go.Scatter(
        x=df["Возраст"], y=df[OUTCOME],
        mode="markers", opacity=0.4,
        marker=dict(color="#2a9d8f"),
        name="Наблюдения"
    )

    df_sorted = df.sort_values("Возраст")
    df_sorted["rolling_mean"] = df_sorted[OUTCOME].rolling(window=30, min_periods=1).mean()

    smooth = go.Scatter(
        x=df_sorted["Возраст"], y=df_sorted["rolling_mean"],
        mode="lines", line=dict(color="orange", width=3),
        name="Скользящее среднее (30)"
    )

    fig = go.Figure([scatter, smooth])
    fig.update_layout(title="Возраст и итоговый балл (сглаженный тренд)",
                      xaxis_title="Возраст", yaxis_title=OUTCOME)

    st.plotly_chart(fig, use_container_width=True)

if "Возрастная группа" in df.columns:
    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            px.box(df, x="Возрастная группа", y=OUTCOME, color="Возрастная группа",
                   title="Распределение итогового балла по возрастным группам"),
            use_container_width=True
        )

    with c2:
        avg_agegrp = df.groupby("Возрастная группа")[OUTCOME].mean().reset_index()
        st.plotly_chart(
            px.bar(avg_agegrp, x="Возрастная группа", y=OUTCOME,
                   title="Средний итоговый балл по возрастным группам",
                   color=OUTCOME, color_continuous_scale="Tealgrn"),
            use_container_width=True
        )

# =============================================================================
# STATIC SECTION 3 — Области (полный список)
# =============================================================================
if "Область" in df.columns:
    st.header("Статистика по областям")

    # полный список уникальных областей
    all_regions = pd.DataFrame({"Область": sorted(df["Область"].unique())})

    # средние значения по областям
    avg_obl = (
        df.groupby("Область")[OUTCOME]
        .mean()
        .round(2)
        .reset_index()
    )

    # объединяем, чтобы показать все области (даже без данных)
    avg_obl_full = all_regions.merge(avg_obl, on="Область", how="left")

    st.plotly_chart(
        px.bar(avg_obl_full.sort_values(OUTCOME, na_position="last"),
               x=OUTCOME, y="Область", orientation="h",
               color=OUTCOME, color_continuous_scale="Tealgrn",
               title="Средний итоговый балл по областям"),
        use_container_width=True
    )
