# app.py (multi-page static dashboard with global filters)
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
# SIDEBAR: NAVIGATION & FILTERS
# =============================================================================
st.sidebar.title("Навигация")
page = st.sidebar.radio("Выберите страницу", ["Основной анализ", "Детальный анализ", "Карта"])

st.sidebar.title("Фильтры")
df_filtered = df.copy()

# --- Subject Filter ---
if "Предмет" in df.columns:
    subjects = sorted(df['Предмет'].dropna().unique())
    selected_subjects = st.sidebar.multiselect(
        'Фильтр по предмету:',
        options=subjects,
        default=subjects
    )
    if not selected_subjects:
        df_filtered = pd.DataFrame(columns=df.columns)
    else:
        df_filtered = df_filtered[df_filtered['Предмет'].isin(selected_subjects)]

# --- Position Filter (cascading) ---
if "Должность" in df.columns and not df_filtered.empty:
    positions = sorted(df_filtered['Должность'].dropna().unique())
    selected_positions = st.sidebar.multiselect(
        'Фильтр по должности:',
        options=positions,
        default=positions
    )
    if not selected_positions:
        df_filtered = pd.DataFrame(columns=df.columns)
    else:
        df_filtered = df_filtered[df_filtered['Должность'].isin(selected_positions)]

# =============================================================================
# PAGE 1: Основной анализ
# =============================================================================
if page == "Основной анализ":
    st.title("📊 Основной анализ успеваемости")

    if df_filtered.empty:
        st.warning("Нет данных, соответствующих выбранным фильтрам.")
    else:
        st.markdown("Ниже приведены ключевые статистики по полу, возрасту и областям.")
        # --- OVERALL STATS ---
        st.header("Общая статистика")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Всего записей", f"{len(df_filtered):,}")
        with c2:
            st.metric("Средний балл", f"{df_filtered[OUTCOME].mean():.2f}")
        with c3:
            st.metric("Медианный балл", f"{df_filtered[OUTCOME].median():.2f}")
        st.markdown("---")

        # --- GENDER STATS ---
        if "Пол" in df_filtered.columns:
            st.header("Статистика по полу")
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.box(df_filtered, x="Пол", y=OUTCOME, color="Пол", title="Распределение итогового балла по полу"), use_container_width=True)
            with c2:
                avg_gender = df_filtered.groupby("Пол")[OUTCOME].mean().reset_index()
                st.plotly_chart(px.bar(avg_gender, x="Пол", y=OUTCOME, color="Пол", title="Средний итоговый балл по полу", color_discrete_sequence=px.colors.sequential.Teal), use_container_width=True)

        # --- AGE STATS ---
        if "Возраст" in df_filtered.columns:
            st.header("Статистика по возрасту")
            scatter = go.Scatter(x=df_filtered["Возраст"], y=df_filtered[OUTCOME], mode="markers", opacity=0.4, marker=dict(color="#2a9d8f"), name="Наблюдения")
            df_sorted = df_filtered.sort_values("Возраст")
            df_sorted["rolling_mean"] = df_sorted[OUTCOME].rolling(window=50, min_periods=1).mean()
            smooth = go.Scatter(x=df_sorted["Возраст"], y=df_sorted["rolling_mean"], mode="lines", line=dict(color="orange", width=3), name="Скользящее среднее (50)")
            fig = go.Figure([scatter, smooth])
            fig.update_layout(title="Возраст и итоговый балл (сглаженный тренд)", xaxis_title="Возраст", yaxis_title=OUTCOME)
            st.plotly_chart(fig, use_container_width=True)

        if "Возрастная группа" in df_filtered.columns:
            # Define the custom order for age groups
            age_group_order = ['<25', '25-30', '30-35', '35-40', '40-45', '45-50', '50-55', '55-60', '>60']
            
            # Apply the custom order by converting to a categorical type
            df_filtered['Возрастная группа'] = pd.Categorical(df_filtered['Возрастная группа'], categories=age_group_order, ordered=True)

            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.box(df_filtered, x="Возрастная группа", y=OUTCOME, color="Возрастная группа", title="Распределение итогового балла по возрастным группам"), use_container_width=True)
            with c2:
                avg_agegrp = df_filtered.groupby("Возрастная группа")[OUTCOME].mean().reset_index()
                st.plotly_chart(px.bar(avg_agegrp, x="Возрастная группа", y=OUTCOME, title="Средний итоговый балл по возрастным группам", color=OUTCOME, color_continuous_scale="Tealgrn"), use_container_width=True)

        # --- REGION STATS ---
        if "Область" in df_filtered.columns:
            st.header("Статистика по областям")
            all_regions = pd.DataFrame({"Область": sorted(df["Область"].unique())}) # Base on original df to show all regions
            
            agg_obl = df_filtered.groupby("Область").agg(
                avg_score=(OUTCOME, 'mean'),
                count=(OUTCOME, 'size')
            ).reset_index()
            
            avg_obl_full = all_regions.merge(agg_obl, on="Область", how="left")
            avg_obl_full['avg_score'] = avg_obl_full['avg_score'].round(2)
            
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
    
    if df_filtered.empty:
        st.warning("Нет данных, соответствующих выбранным фильтрам.")
    else:
        st.markdown("Статистика успеваемости в разрезе категорий, должностей, предметов и типов школ.")
        analysis_columns = ["Категория", "Должность", "Предмет", "Тип школы"]

        for col in analysis_columns:
            if col in df_filtered.columns:
                st.markdown("---")
                st.header(f"Анализ по '{col}'")
                
                df_cat = df_filtered.dropna(subset=[col])

                if df_cat.empty:
                    st.warning(f"Нет данных для анализа по '{col}' с учетом текущих фильтров.")
                    continue

                # --- Layout specific for 'Категория' ---
                if col == "Категория":
                    c1, c2 = st.columns(2)
                    with c1:
                        fig_box = px.box(df_cat, x=col, y=OUTCOME, color=col, title=f"Распределение баллов по '{col}'")
                        st.plotly_chart(fig_box, use_container_width=True)
                    with c2:
                        avg_cat = df_cat.groupby(col)[OUTCOME].mean().round(2).reset_index().sort_values(OUTCOME, ascending=False)
                        fig_bar_avg = px.bar(avg_cat, x=col, y=OUTCOME, color=col, title=f"Средний балл по '{col}'")
                        fig_bar_avg.update_xaxes(tickangle=-90)
                        st.plotly_chart(fig_bar_avg, use_container_width=True)
                
                # --- Layout for other parameters ---
                else:
                    avg_cat = df_cat.groupby(col)[OUTCOME].mean().round(2).reset_index().sort_values(OUTCOME, ascending=False)
                    fig_bar_avg = px.bar(avg_cat, x=col, y=OUTCOME, color=col, title=f"Средний балл по '{col}'")
                    fig_bar_avg.update_xaxes(tickangle=-90)
                    st.plotly_chart(fig_bar_avg, use_container_width=True)

                # --- Count chart for all parameters ---
                counts = df_cat[col].value_counts().reset_index()
                counts.columns = [col, 'count']
                
                fig_bar_count = px.bar(counts, x=col, y='count', color=col, title=f"Количество респондентов по '{col}'")
                fig_bar_count.update_xaxes(tickangle=-90)
                st.plotly_chart(fig_bar_count, use_container_width=True)
                
            else:
                st.warning(f"Столбец '{col}' не найден в данных.")

# =============================================================================
# PAGE 3: Карта
# =============================================================================
elif page == "Карта":
    st.title("🗺️ Карта успеваемости")

    if df_filtered.empty:
        st.warning("Нет данных, соответствующих выбранным фильтрам.")
    else:
        try:
            with open("kz_mapped.geojson", "r", encoding="utf-8") as f:
                geojson_regions = json.load(f)
        except FileNotFoundError:
            st.error("Файл 'kz_mapped.geojson' не найден. Пожалуйста, убедитесь, что он находится в той же папке, что и app.py.")
            st.stop()

        # --- MAP CHART ---
        st.header("Карта по областям")
        color_by = st.radio(
            "Раскрасить карту по:",
            ('Средний балл', 'Количество записей'),
            horizontal=True
        )

        map_data = df_filtered.groupby('Область').agg(
            avg_score=(OUTCOME, 'mean'),
            count=(OUTCOME, 'size')
        ).reset_index()

        color_map_col = 'avg_score' if color_by == 'Средний балл' else 'count'

        fig_map = px.choropleth(
            map_data,
            geojson=geojson_regions,
            featureidkey="properties.name_ru",
            locations='Область',
            color=color_map_col,
            color_continuous_scale="Tealgrn",
            hover_name='Область',
            hover_data={'avg_score': ':.2f', 'count': True},
            title=f"{color_by} по областям",
            scope="asia" # This ensures the correct projection
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

        # --- DISTRICT (РАЙОН) DRILL-DOWN ---
        st.markdown("---")
        st.header("Детализация по районам")

        # Selectbox to choose a region
        available_regions = sorted(df_filtered['Область'].dropna().unique())
        selected_region = st.selectbox(
            "Выберите область для детализации:",
            options=available_regions,
            index=None, # No default selection
            placeholder="Выберите область..."
        )

        if selected_region:
            if 'Район' in df_filtered.columns:
                district_data = df_filtered[df_filtered['Область'] == selected_region]
                
                # Check if there are any districts for the selected region
                if not district_data['Район'].dropna().empty:
                    district_agg = district_data.groupby('Район').agg(
                        avg_score=(OUTCOME, 'mean'),
                        count=(OUTCOME, 'size')
                    ).round(2).reset_index().sort_values('avg_score', ascending=True)

                    fig_district = px.bar(
                        district_agg,
                        x='avg_score',
                        y='Район',
                        orientation='h',
                        title=f"Средний балл по районам: {selected_region}",
                        labels={'avg_score': 'Средний балл', 'Район': 'Район'},
                        text='avg_score'
                    )
                    fig_district.update_traces(textposition='outside')
                    st.plotly_chart(fig_district, use_container_width=True)
                else:
                    st.info(f"В области '{selected_region}' нет данных по районам для отображения.")
            else:
                st.warning("Столбец 'Район' не найден в данных для детализации.")

