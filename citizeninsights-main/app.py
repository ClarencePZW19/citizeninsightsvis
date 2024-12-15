import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import plotly.express as px
import requests
from requests import Response
import json
from io import BytesIO, StringIO
from shapely import wkt
from shapely.geometry import Point, Polygon

# Define a color palette with colors close to Google colors
COLOR_PALETTE = [
    '#4285F4', '#44A955', '#E24332', '#F5BE14',
    '#34A853', '#FBBC05', '#EA4335', '#F4B400',
    '#0F9D58', '#F4C20D', '#DB4437', '#F09300',
    '#4285F4', '#34A853', '#EA4335', '#FBBC05',
    '#F4B400', '#0F9D58', '#F4C20D', '#DB4437'
]

def datagov_csv_request(dataset_id):
    # Generate the GET Request and return the response as a DataFrame
    url = f"https://data.gov.sg/api/action/datastore_search?resource_id={dataset_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        records = data.get('result', {}).get('records', [])
        df = pd.DataFrame(records)
        return df
    else:
        st.error("Failed to fetch data from data.gov.sg.")
        return None
    
def datagov_geojson_request(dataset_id):
    # dataset_id = "d_930e662ac7e141fe3fd2a6efa5216902"
    url = "https://api-open.data.gov.sg/v1/public/api/datasets/" + dataset_id + "/poll-download"

    response: Response = requests.get(url)
    json_data = response.json()
    if json_data['code'] != 0:
        print(json_data['errMsg'])
        exit(1)

    url = json_data['data']['url']
    response = requests.get(url)
    response_string = response.content.decode('utf-8')

    return response_string

def datagov_xlsx_request(dataset_id):

    url = "https://api-open.data.gov.sg/v1/public/api/datasets/" + dataset_id + "/poll-download"
    response = requests.get(url)
    json_data = response.json()
    if json_data['code'] != 0:
        print(json_data['errMsg'])
        exit(1)
    url = json_data['data']['url']
    response = requests.get(url)
    excel_data = pd.read_excel(BytesIO(response.content),engine='openpyxl',sheet_name=None)
    df_combined = pd.concat(excel_data.values(), ignore_index=True)
    str_data = df_combined.to_string()


    return str_data

def fetch_data_based_on_format(dataset_id):
    url = f"https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/metadata"
    response = requests.get(url)
    
    if response.status_code == 200:
        metadata = response.json()
        format_type = metadata.get('data', {}).get('format', '').lower()
        
        if format_type == 'csv':
            return datagov_csv_request(dataset_id)
        elif format_type == 'geojson':
            geojson_string = datagov_geojson_request(dataset_id)
            return gpd.read_file(StringIO(geojson_string))
        elif format_type == 'xlsx':
            return datagov_xlsx_request(dataset_id)
        else:
            st.error(f"Unsupported data format: {format_type}")
            return None
    else:
        st.error("Failed to fetch metadata from data.gov.sg.")
        return None


# Geographic Data Visualizations

def parse_geometry(geometry_str):
    return wkt.loads(geometry_str)

def point_and_polygon_map(df):
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=11)
    
    point_color = COLOR_PALETTE[1]  # Use a color from your palette for points
    polygon_fill_color = '#EA4335'  # Red fill color for polygons
    polygon_border_color = '#808080'  # Grey border color for polygons

    for _, row in df.iterrows():
        geom = row['geometry']
        
        if isinstance(geom, Point):
            # Add point to the map
            folium.CircleMarker(
                location=(geom.y, geom.x),
                radius=5,
                color=point_color,
                fill=True,
                fill_color=point_color
            ).add_to(m)
        
        elif isinstance(geom, Polygon):
            # Add polygon to the map
            folium.GeoJson(
                geom.__geo_interface__,
                style_function=lambda feature: {
                    'fillColor': polygon_fill_color,
                    'color': polygon_border_color,
                    'weight': 1,
                    'fillOpacity': 0.5
                }
            ).add_to(m)
    
    st_folium(m, width=700, height=500)


def heat_map(df):
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=11)
    heat_data = [
        (geom.y, geom.x) for geom in df['geometry']
        if isinstance(geom, Point)
    ]
    HeatMap(heat_data).add_to(m)
    st_folium(m, width=700, height=500)

def bubble_map(df):
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=11)
    point_color = COLOR_PALETTE[1]  # Use a color from your palette for points
    polygon_fill_color = '#EA4335'  # Red fill color
    polygon_border_color = '#808080'  # Grey border color

    for _, row in df.iterrows():
        geom = row['geometry']
        if isinstance(geom, Point):
            folium.CircleMarker(
                location=(geom.y, geom.x),
                radius=10,  # Adjust size as needed
                color=point_color,
                fill=True,
                fill_color=point_color
            ).add_to(m)
        elif isinstance(geom, Polygon):
            folium.GeoJson(
                geom.__geo_interface__,
                style_function=lambda feature: {
                    'fillColor': polygon_fill_color,
                    'color': polygon_border_color,
                    'weight': 1,
                    'fillOpacity': 0.5
                }
            ).add_to(m)
    st_folium(m, width=700, height=500)

def choropleth_map(df, geojson):
    # Assuming 'Region' and 'Value' columns exist for this function
    if 'Region' not in df.columns or 'Value' not in df.columns:
        st.error("Data must contain 'Region' and 'Value' columns.")
        return
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=11)
    folium.Choropleth(
        geo_data=geojson,
        data=df,
        columns=['Region', 'Value'],
        key_on='feature.properties.Name',  # Adjust this to match your GeoJSON property
        fill_color='YlGnBu',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Value'
    ).add_to(m)
    st_folium(m, width=700, height=500)

# Numerical or Tabular Data Visualizations

def bar_chart(data, x_col='Category', y_col='Value', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}' and '{y_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.bar(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def line_chart(data, x_col='Date', y_col='Value', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}' and '{y_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.line(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def scatter_plot(data, x_col='X', y_col='Y', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}' and '{y_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.scatter(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def histogram(data, x_col='Value', category_col=None):
    if x_col not in data.columns:
        st.error(f"Data must contain '{x_col}' and '{category_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.histogram(data, x=x_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def pie_chart(data, names_col='Category', values_col='Value'):
    if names_col not in data.columns or values_col not in data.columns:
        st.error(f"Data must contain '{names_col}' and '{values_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.pie(data, names=names_col, values=values_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(font=dict(family="Roboto", size=14))
    st.plotly_chart(fig, use_container_width=True)

def box_plot(data, x_col='Category', y_col='Value', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}','{y_col}', '{category_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.box(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def heatmap(data):
    fig = px.imshow(data, color_continuous_scale=COLOR_PALETTE)
    fig.update_layout(font=dict(family="Roboto", size=14))
    st.plotly_chart(fig, use_container_width=True)

def area_chart(data, x_col='Date', y_col='Value', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}','{y_col}', '{category_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.area(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def bubble_chart(data, x_col='X', y_col='Y', size_col='Size', category_col=None):
    if x_col not in data.columns or y_col not in data.columns or size_col not in data.columns:
        st.error(f"Data must contain '{x_col}','{y_col}', '{category_col}', '{size_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.scatter(data, x=x_col, y=y_col, size=size_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

def violin_plot(data, x_col='Category', y_col='Value', category_col=None):
    if x_col not in data.columns or y_col not in data.columns:
        st.error(f"Data must contain '{x_col}','{y_col}', '{category_col}' columns. Available columns: {list(data.columns)}")
        return
    fig = px.violin(data, x=x_col, y=y_col, color=category_col, color_discrete_sequence=COLOR_PALETTE)
    fig.update_layout(
        font=dict(family="Roboto", size=14),
        xaxis_title=x_col,
        yaxis_title=y_col,
        yaxis=dict(autorange=True)
    )
    st.plotly_chart(fig, use_container_width=True)

# Main function to run the app
def main():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

        html, body, .block-container, .main {
            font-family: 'Roboto', sans-serif !important;
            background-color: #f4f3f1 !important;
            color: #262626 !important;
        }

        .title {
            font-weight: 700 !important;
        }

        .stPlotlyChart, .stDataFrame, .stTable, .stMarkdown {
            width: 80% !important;
            margin: auto !important;
        }

        .stPlotlyChart .plotly .modebar {
            color: #262626 !important;
        }

        .stPlotlyChart .plotly .gridlines {
            stroke: #262626 !important;
        }

        .stAlert {
            background-color: #800000 !important;  /* Dark red background */
            color: #ffffff !important;  /* White text */
        }
        </style>
        """, unsafe_allow_html=True)

    # Title with bold font
    st.markdown('<h1 class="title">Key Visualization</h1>', unsafe_allow_html=True)

    # Parse URL parameters
    query_params = st.query_params
    dataset_id = query_params.get("datasetid", None)
    viz_type = query_params.get("viz_type", None)
    x_col = query_params.get("x_col", None)
    y_col = query_params.get("y_col", None)
    category_col = query_params.get("category_col", None)
    size_col = query_params.get("size_col", None)

    if not dataset_id or not viz_type:
        st.error("No visualization available")
        return

    try:
        # Fetch data based on format
        data = fetch_data_based_on_format(dataset_id)
        if data is None:
            st.error("No visualization available")
            return

        # Visualize data based on viz_type
        if viz_type == "bar_chart":
            bar_chart(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "line_chart":
            line_chart(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "scatter_plot":
            scatter_plot(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "histogram":
            histogram(data, x_col=x_col or "x", category_col=category_col)
        elif viz_type == "pie_chart":
            pie_chart(data, names_col=x_col or "Category", values_col=y_col or "Value")
        elif viz_type == "box_plot":
            box_plot(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "heatmap":
            heatmap(data)
        elif viz_type == "area_chart":
            area_chart(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "bubble_chart":
            bubble_chart(data, x_col=x_col or "x", y_col=y_col or "y", size_col=size_col or "size", category_col=category_col)
        elif viz_type == "violin_plot":
            violin_plot(data, x_col=x_col or "x", y_col=y_col or "y", category_col=category_col)
        elif viz_type == "heat_map":
            heat_map(data)
        elif viz_type == "point_and_polygon_map":
            point_and_polygon_map(data)
        elif viz_type == "bubble_map":
            bubble_map(data)
        else:
            st.error("No visualization available")
    except Exception as e:
        st.error("No visualization available")

if __name__ == "__main__":
    main()