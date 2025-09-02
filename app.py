import streamlit as st
import pandas as pd
import plotly.express as px

# =================================================================================
# 1. PAGE CONFIGURATION
# Set the page to a wide layout and add a title/icon for the browser tab.
# =================================================================================
st.set_page_config(layout="wide", page_title="Анализ успеваемости", page_icon="📊")


# =================================================================================
# 2. DATA LOADING
# This function loads data from a file.
# @st.cache_data decorator ensures the data is loaded only once, improving performance.
# =================================================================================
@st.cache_data
def load_data(file_path="df.xlsx"):
    """
    Loads data from the specified file path.
    Handles potential FileNotFoundError if the file is missing.
    """
    try:
        # If you are using a CSV file, change the line below to:
        # df = pd.read_csv(file_path)
        df = pd.read_excel(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Файл данных не найден. Убедитесь, что '{file_path}' находится в той же папке, что и app.py.")
        return None

# Load the data into the app
df = load_data()

# Stop the app if data could not be loaded to prevent further errors
if df is None:
    st.stop()

# Define the list of columns that the user can select for grouping the data
grouping_columns = ['Область', 'Тип школы', 'Категория', 'Предмет', 'Пол']


# =================================================================================
# 3. SIDEBAR WITH USER CONTROLS
# The sidebar is used for all user inputs and filters.
# =================================================================================
st.sidebar.header("Параметры стратификации")

# --- REFINED: Multi-select for grouping columns ---
group_cols = st.sidebar.multiselect(
    "Шаг 1: Выберите одну или несколько категорий для группировки",
    options=grouping_columns,
    default=['Область', 'Пол'] # Set a useful default
)

# --- REFINED: Dynamic filters based on selected grouping columns ---
st.sidebar.header("Параметры фильтрации")
filters = {}
if not group_cols:
    st.sidebar.info("Выберите категорию для группировки, чтобы отобразить фильтры.")
else:
    for col in group_cols:
        options = sorted(df[col].unique())
        # Use a descriptive label for each filter
        filters[col] = st.sidebar.multiselect(
            f"Фильтр по '{col}'",
            options=options,
            default=options # Default to all options selected
        )


# =================================================================================
# 4. MAIN PANEL WITH VISUALIZATIONS
# This section displays the title and the charts.
# =================================================================================
st.title("Панель для анализа успеваемости по курсу")

# Check if the user has selected any grouping categories
if not group_cols:
    st.info("Пожалуйста, выберите хотя бы одну категорию для группировки в боковой панели.")
    st.stop()

# --- REFINED: Apply all active filters ---
filtered_df = df.copy()
for col, selected_values in filters.items():
    if selected_values: # Only filter if a value is selected
        filtered_df = filtered_df[filtered_df[col].isin(selected_values)]

if filtered_df.empty:
    st.warning("Нет данных, соответствующих выбранным фильтрам. Попробуйте изменить параметры.")
    st.stop()

# --- REFINED: Group by a list of columns ---
avg_scores = filtered_df.groupby(group_cols)['Итоговый балл'].mean().round(2).reset_index()

# --- REFINED: Create a combined label for the bar chart y-axis ---
if len(group_cols) > 1:
    avg_scores['display_label'] = avg_scores[group_cols].apply(lambda row: ' - '.join(row.values.astype(str)), axis=1)
    y_axis_label = 'display_label'
else:
    y_axis_label = group_cols[0]

avg_scores = avg_scores.sort_values('Итоговый балл')

# --- Horizontal Bar Chart ---
st.subheader(f"Средний 'Итоговый балл' по выбранным категориям")
num_bars = len(avg_scores)
bar_chart_height = max(400, num_bars * 35)

bar_fig = px.bar(
    avg_scores,
    x='Итоговый балл',
    y=y_axis_label,
    orientation='h',
    text='Итоговый балл',
    color='Итоговый балл',
    color_continuous_scale=px.colors.sequential.Tealgrn,
    height=bar_chart_height
)
bar_fig.update_layout(xaxis_title="Средний 'Итоговый балл'", yaxis_title="Группы")
st.plotly_chart(bar_fig, use_container_width=True)


# --- Box Plot ---
st.subheader(f"Распределение баллов по выбранным категориям")

# --- REFINED: Use color for the second dimension in the box plot ---
box_color = group_cols[1] if len(group_cols) > 1 else None

box_fig = px.box(
    filtered_df,
    x=group_cols[0],
    y='Итоговый балл',
    color=box_color,
    title=f"Распределение по '{group_cols[0]}' с разбивкой по '{box_color}'" if box_color else f"Распределение по '{group_cols[0]}'"
)
box_fig.update_layout(yaxis_title="'Итоговый балл'", xaxis_title=group_cols[0])
st.plotly_chart(box_fig, use_container_width=True)
