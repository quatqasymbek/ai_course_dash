# app.py (multi-page static dashboard)
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
# PAGE NAVIGATION
# =============================================================================
st.sidebar.title("Навигация")
page = st.sidebar.radio("Выберите страницу", ["Основной анализ", "Детальный анализ"])

# =============================================================================
# PAGE 1: Основной анализ
# =============================================================================
if page == "Основной анализ":
    st.title("📊 Основной анализ успеваемости")
    st.markdown("Ниже приведены ключевые статистики по полу, возрасту и областям.")

    # --- OVERALL STATS ---
    st.header("Общая статистика")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Всего записей", f"{len(df):,}")
    with c2:
        st.metric("Средний балл", f"{df[OUTCOME].mean():.2f}")
    with c3:
        st.metric("Медианный балл", f"{df[OUTCOME].median():.2f}")
    st.markdown("---")

    # --- GENDER STATS ---
    if "Пол" in df.columns:
        st.header("Статистика по полу")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.box(df, x="Пол", y=OUTCOME, color="Пол", title="Распределение итогового балла по полу"), use_container_width=True)
        with c2:
            avg_gender = df.groupby("Пол")[OUTCOME].mean().reset_index()
            st.plotly_chart(px.bar(avg_gender, x="Пол", y=OUTCOME, color="Пол", title="Средний итоговый балл по полу", color_discrete_sequence=px.colors.sequential.Teal), use_container_width=True)

    # --- AGE STATS ---
    if "Возраст" in df.columns:
        st.header("Статистика по возрасту")
        scatter = go.Scatter(x=df["Возраст"], y=df[OUTCOME], mode="markers", opacity=0.4, marker=dict(color="#2a9d8f"), name="Наблюдения")
        df_sorted = df.sort_values("Возраст")
        df_sorted["rolling_mean"] = df_sorted[OUTCOME].rolling(window=30, min_periods=1).mean()
        smooth = go.Scatter(x=df_sorted["Возраст"], y=df_sorted["rolling_mean"], mode="lines", line=dict(color="orange", width=3), name="Скользящее среднее (30)")
        fig = go.Figure([scatter, smooth])
        fig.update_layout(title="Возраст и итоговый балл (сглаженный тренд)", xaxis_title="Возраст", yaxis_title=OUTCOME)
        st.plotly_chart(fig, use_container_width=True)

    if "Возрастная группа" in df.columns:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.box(df, x="Возрастная группа", y=OUTCOME, color="Возрастная группа", title="Распределение итогового балла по возрастным группам"), use_container_width=True)
        with c2:
            avg_agegrp = df.groupby("Возрастная группа")[OUTCOME].mean().reset_index()
            st.plotly_chart(px.bar(avg_agegrp, x="Возрастная группа", y=OUTCOME, title="Средний итоговый балл по возрастным группам", color=OUTCOME, color_continuous_scale="Tealgrn"), use_container_width=True)

    # --- REGION STATS ---
    if "Область" in df.columns:
        st.header("Статистика по областям")
        all_regions = pd.DataFrame({"Область": sorted(df["Область"].unique())})
        
        # Calculate both mean and count
        agg_obl = df.groupby("Область").agg(
            avg_score=(OUTCOME, 'mean'),
            count=(OUTCOME, 'size')
        ).reset_index()
        
        avg_obl_full = all_regions.merge(agg_obl, on="Область", how="left")
        avg_obl_full['avg_score'] = avg_obl_full['avg_score'].round(2)
        
        # Create text for display on bars
        avg_obl_full['bar_text'] = avg_obl_full.apply(lambda row: f"{row['avg_score']} (n={int(row['count'])})" if pd.notna(row['count']) else "N/A", axis=1)

        fig = px.bar(
            avg_obl_full.sort_values("avg_score", na_position="first"),
            x="avg_score", y="Область", orientation="h",
            color="avg_score", color_continuous_scale="Tealgrn",
            text='bar_text',
            title="Средний итоговый балл и количество записей по областям",
            labels={'avg_score': 'Средний итоговый балл', 'Область': 'Область'}
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# PAGE 2: Детальный анализ
# =============================================================================
elif page == "Детальный анализ":
    st.title("🔎 Детальный анализ по категориям")
    st.markdown("Статистика успеваемости в разрезе категорий, должностей и предметов.")

    analysis_columns = ["Категория", "Должность", "Предмет"]

    for col in analysis_columns:
        if col in df.columns:
            st.markdown("---")
            st.header(f"Анализ по '{col}'")
            
            # Drop rows where the category itself is missing
            df_cat = df.dropna(subset=[col])

            if df_cat.empty:
                st.warning(f"Нет данных для анализа по '{col}'.")
                continue

            # Для "Должность" и "Предмет" показываем только гистограмму
            if col in ["Должность", "Предмет"]:
                avg_cat = df_cat.groupby(col)[OUTCOME].mean().round(2).reset_index().sort_values(OUTCOME, ascending=False)
                fig_bar = px.bar(avg_cat, x=col, y=OUTCOME, color=col, title=f"Средний балл по '{col}'")
                st.plotly_chart(fig_bar, use_container_width=True)
            else: # Для "Категория" показываем оба графика
                c1, c2 = st.columns(2)
                
                with c1:
                    # Box plot for distribution
                    fig_box = px.box(df_cat, x=col, y=OUTCOME, color=col, title=f"Распределение баллов по '{col}'")
                    st.plotly_chart(fig_box, use_container_width=True)

                with c2:
                    # Bar chart for average scores
                    avg_cat = df_cat.groupby(col)[OUTCOME].mean().round(2).reset_index().sort_values(OUTCOME, ascending=False)
                    fig_bar = px.bar(avg_cat, x=col, y=OUTCOME, color=col, title=f"Средний балл по '{col}'")
                    st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning(f"Столбец '{col}' не найден в данных.")

