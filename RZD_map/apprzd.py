import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import folium
from streamlit_folium import folium_static,st_folium

st.set_page_config(page_title='Интерактивная карта',page_icon=":bar_chart",layout="wide")

def load_data():

    # Виджет для загрузки файла
    file = st.file_uploader("Загрузите файл", type=["xlsx"])

    # Проверка, загружен ли файл
    if file is not None:
        # Отображение индикатора прогресса загрузки
        progress = st.progress(0)

        # Загрузка данных из файла
        data_speed = pd.read_excel(file)
        data_all_stations = pd.read_csv('Данные_по_станциям.csv')

        data_speed = data_speed.replace({np.nan: "Неизвестно"})
        data_speed['StartStation'] = [i.lower() for i in data_speed['StartStation']]
        data_speed['EndStation'] = [i.lower() for i in data_speed['EndStation']]

        data_geo = data_speed.merge(data_all_stations, how='inner', left_on='StartStation', right_on='Станция')[
            ['Широта', 'Долгота', 'Код', 'Общий балл', 'StartStation', 'EndStation', 'Дорога']]
        data_geo = data_geo.merge(data_all_stations, how='inner', left_on='EndStation', right_on='Станция')[
            ['Широта_x', 'Долгота_x', 'Код_x', 'Широта_y', 'Долгота_y', 'Код_y', 'Общий балл', 'StartStation',
             'EndStation', 'Дорога']]
        data_geo = data_geo.drop_duplicates(subset=['StartStation', 'EndStation'])

        mas_geojson_all = []

        for i in range(len(data_geo)):
            cord_start = [data_geo.iloc[i]['Долгота_x'], data_geo.iloc[i]['Широта_x']]
            cord_end = [data_geo.iloc[i]['Долгота_y'], data_geo.iloc[i]['Широта_y']]

            url = f"http://brouter.de/brouter?lonlats={cord_start[0]},{cord_start[1]}|{cord_end[0]},{cord_end[1]}&profile=rail&alternativeidx=0&format=geojson"
            res = requests.get(url).json()
            res = res['features'][0]['geometry']

            mas_geo = []
            for cord in res['coordinates']:
                mas_geo.append([cord[1], cord[0]])

            mas_geojson_all.append(mas_geo)

        data_geo['путь'] = mas_geojson_all
        data_geo.to_csv("Данные_станций_с_путями")

        # Обновление индикатора прогресса
        progress.progress(100)

def page_one_way():
    data = pd.read_csv('Данные_станций_с_путями')

    st.markdown('<h1 style="font-size: 25px;">Одиночный маршрут</h1>',
                unsafe_allow_html=True)

    category_road = st.sidebar.multiselect(
        "Выберите дорогу:",
        options=data["Дорога"].unique(),
        default=data["Дорога"].unique()
    )

    df_selection = data.query(
        "Дорога == @category_road"
    )

    mas_name_esr_input = [name_begin for name_begin in df_selection['StartStation']]
    mas_esr_input = [esr_begin for esr_begin in df_selection['Код_x']]
    mas_name_esr_input.extend(mas_esr_input)

    input_begin = st.selectbox(
        'Начальная станция или код ЕСР',
        (mas_name_esr_input))

    mas_end_stations = df_selection[(df_selection['StartStation'] == input_begin) | (df_selection['Код_x'] == input_begin)][
        'EndStation'].tolist()
    mas_end_esr = df_selection[(df_selection['StartStation'] == input_begin) | (df_selection['Код_x'] == input_begin)]['Код_y'].tolist()
    mas_end_stations.extend(mas_end_esr)

    input_end = st.selectbox(
        'Конечная станция или код ЕСР',
        (mas_end_stations))

    data_place = df_selection[((df_selection['StartStation'] == input_begin) & (df_selection['EndStation'] == input_end)) | (
                (df_selection['Код_x'] == input_begin) & (df_selection['Код_y'] == input_end)) | (
                                  (df_selection['StartStation'] == input_begin) & (df_selection['Код_y'] == input_end)) | (
                                  (df_selection['Код_x'] == input_begin) & (df_selection['EndStation'] == input_end))].head(1)
    cords = json.loads(data_place['путь'].tolist()[0])
    middle = cords[len(cords) // 2]
    color_line = data_place['Общий балл'].tolist()[0]

    if color_line > 26.2 and color_line < 33:
        color = 'yellow'

    elif color_line > 32:
        color = 'red'

    elif color_line <= 26.2:
        color = 'green'

    m = folium.Map(location=middle, zoom_start=16)

    folium.PolyLine(cords, color=color).add_to(m)

    tooltip = "Нажмите, чтобы узнать скорость!"

    popup_text = f'''
        <h3 style="font-size: 18px;">Данные по маршруту</h3>
        <p style="font-size: 16px;">Индекс интегральной оценки: {color_line}</p>
    '''

    icon = folium.Icon(color='red', icon='info-sign')
    folium.Marker(middle, icon=icon, popup=popup_text, tooltip=tooltip).add_to(m)

    circle_start = folium.Circle(
        location=cords[0],
        radius=100,  # радиус кружка в метрах
        color='blue',  # цвет кружка
        fill=True,  # заполнить кружок цветом
        fill_color='blue',  # цвет заполнения кружка
        fill_opacity=0.6  # прозрачность заполнения кружка
    )

    circle_end = folium.Circle(
        location=cords[-1],
        radius=100,  # радиус кружка в метрах
        color='blue',  # цвет кружка
        fill=True,  # заполнить кружок цветом
        fill_color='blue',  # цвет заполнения кружка
        fill_opacity=0.6  # прозрачность заполнения кружка
    )

    circle_start.add_to(m)
    circle_end.add_to(m)

    st_data = st_folium(m, width=1200)

def page_filter_railway():
    data = pd.read_csv('Данные_станций_с_путями')

    st.markdown('<h1 style="font-size: 25px;">Машруты по определённым дорогам</h1>',
                unsafe_allow_html=True)

    category_road = st.sidebar.multiselect(
        "Выберите дорогу:",
        options=data["Дорога"].unique(),
        default="КРАС"
    )


    try:
        df_selection = data.query(
            "Дорога == @category_road"
        )

        middle = json.loads(df_selection.head(1)['путь'].tolist()[0])[0]
        m = folium.Map(location=middle, zoom_start=16)

        for i in range(len(df_selection)):
            color_line = df_selection.iloc[i]['Общий балл'].tolist()
            cords = json.loads(df_selection.iloc[i]['путь'])
            start_station = df_selection.iloc[i]['StartStation']
            end_station = df_selection.iloc[i]['EndStation']

            if color_line > 26.2 and color_line < 33:
                color = 'yellow'

            elif color_line > 32:
                color = 'red'

            elif color_line <= 26.2:
                color = 'green'

            folium.PolyLine(cords, color=color).add_to(m)

            tooltip = "Нажмите, чтобы узнать скорость!"

            popup_text = f'''
                    <h3 style="font-size: 18px;">Данные по маршруту</h3>
                    <p style="font-size: 16px;">Индекс интегральной оценки: {color_line}</p>
                    <p style="font-size: 16px;">{start_station} - {end_station}</p>
                '''

            icon = folium.Icon(color='red', icon='info-sign')
            folium.Marker(cords[len(cords) // 2], icon=icon, popup=popup_text, tooltip=tooltip).add_to(m)

            circle_start = folium.Circle(
                location=cords[0],
                radius=100,  # радиус кружка в метрах
                color='blue',  # цвет кружка
                fill=True,  # заполнить кружок цветом
                fill_color='blue',  # цвет заполнения кружка
                fill_opacity=0.6  # прозрачность заполнения кружка
            )

            circle_end = folium.Circle(
                location=cords[-1],
                radius=100,  # радиус кружка в метрах
                color='blue',  # цвет кружка
                fill=True,  # заполнить кружок цветом
                fill_color='blue',  # цвет заполнения кружка
                fill_opacity=0.6  # прозрачность заполнения кружка
            )

            circle_start.add_to(m)
            circle_end.add_to(m)

        st_data = st_folium(m, width=1200)

    except IndexError:
        st.write("Выберите дорогу")

# Создание боковой панели для навигации между страницами
page = st.sidebar.selectbox('Выберите страницу', ['Загрузка данных','Одиночный маршрут', 'Машруты по определённым дорогам'])

# Определение логики переходов между страницами
if page == 'Загрузка данных':
    load_data()

elif page == 'Машруты по определённым дорогам':
    page_filter_railway()

elif page == 'Одиночный маршрут':
    page_one_way()
