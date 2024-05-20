import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash import dash_table
import pandas as pd
import http.client
import json
from fpdf import FPDF
import io
from flask import Flask

# Inicialização do servidor Flask
server = Flask(__name__)

# Inicialização do aplicativo Dash
app = dash.Dash(__name__, server=server, url_base_pathname='/dash/')

# Estilos CSS
app.css.append_css({
    'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css'
})
app.css.append_css({
    'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.min.css'
})

# Layout do aplicativo Dash
app.layout = html.Div(style={
    'fontFamily': 'Arial', 
    'backgroundColor': '#f0f2f5', 
    'padding': '20px',
    'maxWidth': '1200px', 
    'margin': 'auto'
}, children=[
    html.H1('Dashboard de Futebol', style={
        'textAlign': 'center', 
        'color': '#003366',
        'marginBottom': '40px'
    }),
    
    html.Div([
        dcc.Dropdown(
            id='dropdown1',
            options=[
                {'label': 'Timezone', 'value': 'timezone'},
                {'label': 'Countries', 'value': 'countries'},
                {'label': 'Leagues', 'value': 'leagues'},
                {'label': 'Teams', 'value': 'teams'}
            ],
            placeholder='Selecione um tópico principal',
            style={'marginBottom': '10px'}
        ),
        dcc.Dropdown(
            id='dropdown2',
            placeholder='Selecione um filtro',
            style={'marginBottom': '20px'}
        ),
        dash_table.DataTable(
            id='datatable',
            columns=[{"name": i, "id": i} for i in ['Coluna 1', 'Coluna 2', 'Coluna 3']],
            data=[],
            editable=True, 
            filter_action='native',  
            sort_action='native',  
            row_selectable='single',  
            selected_rows=[],  
            style_table={'overflowX': 'auto', 'marginBottom': '20px'},  
            style_cell={
                'minWidth': '100px', 
                'maxWidth': '200px',
                'whiteSpace': 'normal',
                'textAlign': 'center',
                'padding': '10px'
            },
            style_header={
                'backgroundColor': '#003366',  
                'color': 'white',  
                'fontWeight': 'bold'
            },
            style_data={
                'backgroundColor': '#ffffff',  
                'color': '#000',  
                'border': '1px solid #ddd'
            }
        ),
        html.Div([
            html.Button('Exportar XLS', id='btn-xls', n_clicks=0, className='button-primary', style={'marginRight': '10px'}),
            html.Button('Exportar PDF', id='btn-pdf', n_clicks=0, className='button-primary', style={'marginRight': '10px'}),
            html.Button('Exportar CSV', id='btn-csv', n_clicks=0, className='button-primary')
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        
        dcc.Download(id="download-dataframe-xls"),
        dcc.Download(id="download-dataframe-pdf"),
        dcc.Download(id="download-dataframe-csv"),
        
        html.Div([
            dcc.Input(id='api-call', type='text', readOnly=True, style={'width': '80%', 'marginRight': '10px'}),
            html.Button('Copiar', id='btn-api-call', n_clicks=0, className='button-primary')
        ], style={'textAlign': 'center'})
    ], style={'width': '100%', 'margin': 'auto'})
])

# Função para fazer a chamada à API
def call_api(endpoint):
    conn = http.client.HTTPSConnection("api-football-v1.p.rapidapi.com")
    headers = {
        'X-RapidAPI-Key': "4cd7ad4655msh50937264e0b791ep1381bdjsn51a1459783f3",
        'X-RapidAPI-Host': "api-football-v1.p.rapidapi.com"
    }
    conn.request("GET", endpoint, headers=headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

# Callback para atualizar o segundo dropdown com base na seleção do primeiro
@app.callback(
    Output('dropdown2', 'options'),
    Input('dropdown1', 'value')
)
def set_dropdown_options(selected_option):
    if selected_option == 'leagues':
        endpoint = "/v3/countries"
        data = call_api(endpoint)
        return [{'label': country['name'], 'value': country['name']} for country in data['response']]
    elif selected_option == 'teams':
        endpoint = "/v3/leagues"
        data = call_api(endpoint)
        return [{'label': league['league']['name'], 'value': league['league']['id']} for league in data['response']]
    return []

# Callback para atualizar a tabela de dados e exibir a chamada da API, e copiar o link para a área de transferência
@app.callback(
    Output('datatable', 'columns'),
    Output('datatable', 'data'),
    Output('api-call', 'value'),
    Input('dropdown2', 'value'),
    Input('btn-api-call', 'n_clicks'),
    State('dropdown1', 'value'),
    State('api-call', 'value')
)
def update_table_and_copy_link(sub_option, n_clicks, main_option, api_call):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    endpoint = ""
    df = pd.DataFrame()
    
    if triggered_id == 'dropdown2':
        if sub_option and main_option:
            if main_option == 'timezone':
                endpoint = "/v3/timezone"
                data = call_api(endpoint)
                df = pd.DataFrame(data['response'], columns=['timezone'])
            elif main_option == 'countries':
                endpoint = "/v3/countries"
                data = call_api(endpoint)
                df = pd.DataFrame(data['response'])
            elif main_option == 'leagues':
                endpoint = f"/v3/leagues?country={sub_option}"
                data = call_api(endpoint)
                leagues_data = []
                for item in data['response']:
                    league_info = item['league']
                    leagues_data.append({
                        'id': league_info['id'],
                        'name': league_info['name'],
                        'type': league_info['type'],
                        'logo': league_info['logo']
                    })
                df = pd.DataFrame(leagues_data)
            elif main_option == 'teams':
                endpoint = f"/v3/teams?league={sub_option}&season=2021"
                data = call_api(endpoint)
                teams_data = []
                for item in data['response']:
                    team_info = item['team']
                    teams_data.append({
                        'id': team_info['id'],
                        'name': team_info['name'],
                        'country': team_info['country'],
                        'logo': team_info['logo']
                    })
                df = pd.DataFrame(teams_data)
            
            # Cria o valor da chamada da API
            api_call_value = f"https://api-football-v1.p.rapidapi.com{endpoint}"
        else:
            api_call_value = ""
        
        return [{"name": i, "id": i} for i in df.columns], df.to_dict('records'), api_call_value
    
    elif triggered_id == 'btn-api-call' and n_clicks > 0:
        script = f"""
        var dummy = document.createElement('textarea');
        document.body.appendChild(dummy);
        dummy.value = '{api_call}';
        dummy.select();
        document.execCommand('copy');
        document.body.removeChild(dummy);
        alert('Link copiado para a área de transferência!');
        """
        return dash.no_update, dash.no_update, api_call
    
    return dash.no_update, dash.no_update, api_call

# Função para exportar dados como XLS
@app.callback(
    Output('download-dataframe-xls', 'data'),
    Input('btn-xls', 'n_clicks'),
    State('datatable', 'data')
)
def export_xls(n_clicks, rows):
    if n_clicks > 0 and rows:
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_excel, "export.xlsx", index=False)
    return None

# Função para exportar dados como CSV
@app.callback(
    Output('download-dataframe-csv', 'data'),
    Input('btn-csv', 'n_clicks'),
    State('datatable', 'data')
)
def export_csv(n_clicks, rows):
    if n_clicks > 0 and rows:
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_csv, "export.csv", index=False)
    return None

# Função para exportar dados como PDF
@app.callback(
    Output('download-dataframe-pdf', 'data'),
    Input('btn-pdf', 'n_clicks'),
    State('datatable', 'data')
)
def export_pdf(n_clicks, rows):
    if n_clicks > 0 and rows:
        df = pd.DataFrame(rows)
        buffer = io.BytesIO()
        pdf = FPDF('L', 'mm', 'A3')  # Orientação paisagem, unidades em milímetros, tamanho A3
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        page_width = pdf.w - 2 * pdf.l_margin  # Largura da página menos margens
        col_width = page_width / len(df.columns)  # Ajustar a largura das colunas
        row_height = pdf.font_size
        
        # Cabeçalho
        pdf.set_fill_color(0, 51, 102)  # Azul escuro
        pdf.set_text_color(255, 255, 255)  # Branco
        for col in df.columns:
            pdf.cell(col_width, row_height, col, border=1, fill=True)
        pdf.ln(row_height)
        
        # Dados
        pdf.set_fill_color(230, 230, 230)  # Cinza claro
        pdf.set_text_color(0, 0, 0)  # Preto
        fill = False
        for i in range(len(df)):
            for col in df.columns:
                pdf.cell(col_width, row_height, str(df.iloc[i][col]), border=1, fill=fill)
            fill = not fill  # Alternar preenchimento para linhas
            pdf.ln(row_height)
        
        pdf_content = pdf.output(dest='S').encode('latin1')  # Obter conteúdo do PDF como bytes
        return dcc.send_bytes(pdf_content, "export.pdf")
    return None

# Executa o servidor do aplicativo
if __name__ == '__main__':
    app.run_server(debug=True)