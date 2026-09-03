# -*- coding: utf-8 -*-

try:
    from dash import Dash, dcc, html, Input, Output
    import plotly.express as px
except ImportError:
    raise ImportError("The 'viz' module requires 'plotly' dependacy, pip install dmanage[plotly]")
    
from dmanage._compat import pd
import numpy as np

# Sample data
np.random.seed(42)
df = pd.DataFrame({
    'Point_ID': [f'Sample_{i}' for i in range(100)],
    'Feature_A': np.random.randn(100),
    'Feature_B': np.random.randn(100) * 5,
    'Weight': np.random.randint(5, 25, 100),
    'Category': np.random.choice(['Group A', 'Group B', 'Group C'], 100),
    'Marker_Type': np.random.choice(['Type X', 'Type Y'], 100)
})




app = Dash(__name__)


def create_sidebar_from_df(df):
    # 1. Filter columns explicitly accounting for modern Pandas string dtypes
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'str', 'string', 'category', 'bool']).columns.tolist()
    all_cols = df.columns.tolist()
    
    # 2. Dynamic defaults
    default_x = numeric_cols[0] if numeric_cols else all_cols[0]
    default_y = numeric_cols[1] if len(numeric_cols) > 1 else default_x
    default_color = categorical_cols[0] if categorical_cols else None
    default_size = numeric_cols[2] if len(numeric_cols) > 2 else None
    default_shape = categorical_cols[1] if len(categorical_cols) > 1 else None
    sidebar_controls = [
        html.H3("Variable Controls"),
        
        html.Label("X Axis"),
        dcc.Dropdown(options=numeric_cols or all_cols, value=default_x, id='x-var', clearable=False),
        
        html.Label("Y Axis"),
        dcc.Dropdown(options=numeric_cols or all_cols, value=default_y, id='y-var', clearable=False),
        
        html.Label("Color Variable"),
        dcc.Dropdown(
            options=[{'label': 'None', 'value': ''}] + [{'label': col, 'value': col} for col in all_cols],
            value=default_color or '',
            id='color-var',
            clearable=False
        ),
        
        html.Label("Marker Size"),
        dcc.Dropdown(
            options=[{'label': 'Uniform Size', 'value': ''}] + [{'label': col, 'value': col} for col in numeric_cols],
            value=default_size or '',
            id='size-var',
            clearable=False
        ),
        
        html.Label("Marker Shape"),
        dcc.Dropdown(
            options=[{'label': 'Uniform Shape', 'value': ''}] + [{'label': col, 'value': col} for col in categorical_cols],
            value=default_shape or '',
            id='shape-var',
            clearable=False
        ),
    ]
    return sidebar_controls
    
sidebar_controls = create_sidebar_from_df(df)
app.layout = html.Div([
    html.Div(sidebar_controls, style={'width': '22%', 'float': 'left', 'padding': '15px', 'backgroundColor': '#f8f9fa'}),
    html.Div([
        dcc.Graph(id='main-scatter'),
        html.Div(id='detail-panel', style={'marginTop': '20px', 'padding': '15px', 'border': '1px solid #ccc'})
    ], style={'width': '73%', 'float': 'right', 'padding': '15px'})
    ])

@app.callback(
    Output('main-scatter', 'figure'),
    [Input('x-var', 'value'),
     Input('y-var', 'value'),
     Input('color-var', 'value'),
     Input('size-var', 'value'),
     Input('shape-var', 'value')]
)
def update_scatter(x, y, color, size, shape):
    return px.scatter(
        df,
        x=x,
        y=y,
        color=color if color else None,
        size=size if size else None,
        symbol=shape if shape else None,
        custom_data=['Point_ID'],
        title="Dynamic Dataset Explorer"
        )

@app.callback(
    Output('detail-panel', 'children'),
    Input('main-scatter', 'clickData')
)
def process_click(clickData):
    if not clickData:
        return "Click any point in the scatter plot to run detail computations."
    
    # Extract selected point ID
    point_id = clickData['points'][0]['customdata'][0]
    row = df[df['Point_ID'] == point_id].iloc[0]
    
    # Heavy backend calculation executed here on demand
    calculated_metric = (row['Feature_A'] ** 2) + (row['Feature_B'] * 10)

    return [
        html.H4(f"Detailed Analysis: {point_id}"),
        html.P(f"Category: {row['Category']} | Weight: {row['Weight']}"),
        html.P(f"Computed Backend Result: {calculated_metric:.4f}")
    ]

if __name__ == '__main__':
    app.run(debug=True)