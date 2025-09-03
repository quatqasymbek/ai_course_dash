# app.py (interactive dashboard with filters)
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
# SIDEBAR FILTERS
# =============================================================================
st.sidebar.header("Фильтры")

# Start with a copy of the original dataframe
df_filtered = df.copy()

# Define columns to create filters for
filter_columns = ["Категория", "Должность", "Предмет"]
selections = {}

# Create a multiselect widget for each filter column if it exists
for col in filter_columns:
    if col in df.columns:
        options = sorted(df[col].dropna().unique())
        selections[col] = st.sidebar.multiselect(
            f"Выберите {col}",
            options=options,
            default=options, # By default, all options are selected
            key=f"multiselect_{col}" # Unique key for each widget
        )
        # Apply the filter to the dataframe
        if selections[col]:
            df_filtered = df_filtered[df_filtered[col].isin(selections[col])]

# Stop if filters result in an empty dataframe
if df_filtered.empty:
    st.warning("Нет данных для отображения по выбранным фильтрам. Пожалуйста, измените критерии в боковой панели.")
    st.stop()

# =============================================================================
# TITLE
# =============================================================================
st.title("📊 Анализ успеваемости")
st.markdown("Ниже приведены ключевые статистики по полу, возрасту и областям.")

# =============================================================================
# OVERALL STATS (uses df_filtered)
# =============================================================================
st.header("Общая статистика")
c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Всего записей", f"{len(df_filtered):,}")

with c2:
    # Handle case where there might be no valid scores after filtering
    mean_score = df_filtered[OUTCOME].mean()
    st.metric("Средний балл", f"{mean_score:.2f}" if not pd.isna(mean_score) else "N/A")

with c3:
    median_score = df_filtered[OUTCOME].median()
    st.metric("Медианный балл", f"{median_score:.2f}" if not pd.isna(median_score) else "N/A")

st.markdown("---") # Add a divider

# =============================================================================
# STATIC SECTION 1 — Пол (uses df_filtered)
# =============================================================================
if "Пол" in df_filtered.columns:
    st.header("Статистика по полу")
    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            px.box(df_filtered, x="Пол", y=OUTCOME, color="Пол",
                   title="Распределение итогового балла по полу"),
            use_container_width=True
        )

    with c2:
        avg_gender = df_filtered.groupby("Пол")[OUTCOME].mean().reset_index()
        st.plotly_chart(
            px.bar(avg_gender, x="Пол", y=OUTCOME, color="Пол",
                   title="Средний итоговый балл по полу",
                   color_discrete_sequence=px.colors.sequential.Teal),
            use_container_width=True
        )

# =============================================================================
# STATIC SECTION 2 — Возраст (uses df_filtered)
# =============================================================================
if "Возраст" in df_filtered.columns:
    st.header("Статистика по возрасту")

    # Scatter with rolling mean smoothing
    scatter = go.Scatter(
        x=df_filtered["Возраст"], y=df_filtered[OUTCOME],
        mode="markers", opacity=0.4,
        marker=dict(color="#2a9d8f"),
        name="Наблюдения"
    )

    df_sorted = df_filtered.sort_values("Возраст")
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

if "Возрастная группа" in df_filtered.columns:
    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            px.box(df_filtered, x="Возрастная группа", y=OUTCOME, color="Возрастная группа",
                   title="Распределение итогового балла по возрастным группам"),
            use_container_width=True
        )

    with c2:
        avg_agegrp = df_filtered.groupby("Возрастная группа")[OUTCOME].mean().reset_index()
        st.plotly_chart(
            px.bar(avg_agegrp, x="Возрастная группа", y=OUTCOME,
                   title="Средний итоговый балл по возрастным группам",
                   color=OUTCOME, color_continuous_scale="Tealgrn"),
            use_container_width=True
        )

# =============================================================================
# STATIC SECTION 3 — Области (полный список) (uses df_filtered)
# =============================================================================
if "Область" in df_filtered.columns:
    st.header("Статистика по областям")

    # Get all unique regions from the original dataframe for a complete list
    all_regions = pd.DataFrame({"Область": sorted(df["Область"].unique())})

    # Calculate averages based on the filtered data
    avg_obl = (
        df_filtered.groupby("Область")[OUTCOME]
        .mean()
        .round(2)
        .reset_index()
    )

    # Merge to ensure all regions are shown, even if they have no data after filtering
    avg_obl_full = all_regions.merge(avg_obl, on="Область", how="left")

    st.plotly_chart(
        px.bar(avg_obl_full.sort_values(OUTCOME, na_position="last"),
               x=OUTCOME, y="Область", orientation="h",
               color=OUTCOME, color_continuous_scale="Tealgrn",
               title="Средний итоговый балл по областям"),
        use_container_width=True
    )

