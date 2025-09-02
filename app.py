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
st.sidebar.header("Параметры фильтрации")

# Step 1: Dropdown to select the main category for grouping
group_col = st.sidebar.selectbox(
    "Шаг 1: Выберите категорию для группировки",
    options=grouping_columns
)

# Step 2: Multi-select box to choose the specific items to compare
# The options in this box are dynamically updated based on the selection in Step 1.
options = sorted(df[group_col].unique())
filter_values = st.sidebar.multiselect(
    "Шаг 2: Выберите элементы для сравнения",
    options=options,
    default=options[:3]  # Set a default selection of the first three items
)


# =================================================================================
# 4. MAIN PANEL WITH VISUALIZATIONS
# This section displays the title and the charts.
# =================================================================================
st.title("📊 Панель для анализа успеваемости по курсу")

# Check if the user has selected any values in the multiselect box
if not filter_values:
    st.warning("Пожалуйста, выберите хотя бы один элемент для сравнения в боковой панели.")
    st.stop() # Stop the script execution if nothing is selected

# Filter the DataFrame based on the user's selections
filtered_df = df[df[group_col].isin(filter_values)]
avg_scores = filtered_df.groupby(group_col)['Итоговый балл'].mean().round(2).reset_index().sort_values('Итоговый балл')

# --- Horizontal Bar Chart ---
st.subheader(f"Средний 'Итоговый балл' по '{group_col}'")

# Dynamically calculate the chart height based on the number of bars
num_bars = len(avg_scores)
bar_chart_height = max(300, num_bars * 45)

bar_fig = px.bar(
    avg_scores,
    x='Итоговый балл',
    y=group_col,
    orientation='h',
    text='Итоговый балл',
    color='Итоговый балл',
    color_continuous_scale=px.colors.sequential.Tealgrn,
    height=bar_chart_height
)
bar_fig.update_layout(xaxis_title="Средний 'Итоговый балл'", yaxis_title=None)
st.plotly_chart(bar_fig, use_container_width=True)


# --- Box Plot ---
st.subheader(f"Распределение баллов по '{group_col}'")
box_fig = px.box(
    filtered_df,
    x=group_col,
    y='Итоговый балл',
    color=group_col
)
box_fig.update_layout(yaxis_title="'Итоговый балл'", xaxis_title=None)
st.plotly_chart(box_fig, use_container_width=True)
