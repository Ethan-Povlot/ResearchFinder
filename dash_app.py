import dash
import dash_auth
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from flask import request
import pandas as pd
import numpy as np
from datetime import datetime
import spacy
from collections import Counter
from time import sleep
from waitress import serve

nlp = spacy.load("en_core_web_sm")
df = pd.read_pickle('last_month.pkl') #de_duped, osf_data
pref_df = pd.read_pickle('user_pref.pkl') ##fix this
df_searched = df.copy()
VALID_USERNAME_PASSWORD_PAIRS = {
    'Emory': 'password',
    'GT':'password',
    'Harold':'password'
}
USER_GROUPS={
    None:'All',
    'Emory': 'Emory',
    'GT':'GT',
    'Harold':'GT'
}
UNI_LOGO_URL = {
    'Emory':r'https://1000logos.net/wp-content/uploads/2022/06/Emory-University-Logo.png',
    'GT':r'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Georgia_Tech_seal.svg/1200px-Georgia_Tech_seal.svg.png',
    "None": r'https://upload.wikimedia.org/wikipedia/commons/9/9e/Blank.svg'
}
def get_records_bool(x, uni_lst):
    for name in uni_lst:
        if name in str(x):
            return 'True'
    return 'False'

def get_dropdown_options(lst):
    uni_lst_temp = [item.strip() for val in lst for item in str(val).replace("[", '').replace("]", '').replace("'", "").replace(";", ',').split(',')]
    flat_list = []
    known_schools = {'@emory.edu', '@gatech.edu', 'Georgia Institute of Technology', 'gatech'}

    for item in uni_lst_temp:
        if '@' in item:
            item = item.split('@')[1]
            if '.edu' in item:
                item = "@"+item.split('.edu')[0] + '.edu'
        item = item.strip('"\'').rstrip('.')
        
        if item not in ['Central', 'The U', 'nan'] and len(item) > 2 and item not in known_schools:
            flat_list.append(item)

    counts = Counter(flat_list)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    output = [x[0] for x in sorted_counts]

    return ['All'] + output
uni_init_lst = get_dropdown_options(df['affiliations'].values.tolist())#['All']#
aoi_init_lsr = get_dropdown_options(df['subjects'].values.tolist())#['All']#
def fetch_data(university, area_of_interest):
    global df
    try:
        username = request.authorization['username']
    except:
        username = None
    if university == None or university == []:
        university = ['All']
    if area_of_interest == None or area_of_interest == []:
        area_of_interest = ['All']
    df1 = df.copy()
    if 'Georgia Tech' in university:
        university.append('Georgia Institute of Technology')
        university.append('@gatech')
    if 'Emory' in str(university):
        university.append('@emory')
    if not('All' in university):
        df1['temp'] = df1['affiliations'].apply(get_records_bool, args = [university, ])
        df1 = df1[df1['temp']=='True']
    if not 'All' in area_of_interest:
        df1['temp'] = df1['subjects'].apply(get_records_bool, args = [area_of_interest, ])
        df1 = df1[df1['temp']=='True']
    global df_searched
    global pref_df
    df_searched = df1.copy()
    try:
        if username != None:
            df1 = df1.sort_values(by=[username+'_score'], ascending=False).reset_index(drop=True)
    except:
        pass
    return df1.head(20).to_dict(orient='records')
# Function to generate initial layout
def generate_initial_layout(university=[], area_of_interest=[]):
    data = fetch_data(university, area_of_interest)
    initial_list = []
    for i, entry in enumerate(data):
        new_entry = html.Div([
            html.Div(
                html.A(entry['title'],href=entry['url'],id={'type': 'url-link', 'index': i},className='url-link', style={"text-align": "center", "font-weight": "bold"}
                ),style={"text-align": "center"}),
            dcc.Markdown(entry['abstract'], className='url-abstract', mathjax=True,),
            html.Div([
        html.Div([
            html.Button('Like', id={'type': 'like-button', 'index': i}, className='btn btn-success'),
            html.Button('Dislike', id={'type': 'dislike-button', 'index': i}, className='btn btn-danger', style={"margin-left": "15px"}),
        ], style={"display": "inline-block"}),
        dcc.Markdown(entry['source'], className='url-source', mathjax=False,),
    ], style={"display": "flex", "justify-content": "space-between", "align-items": "center"})

        ], className='url-entry list-group-item', style={'marginBottom':'1%', 'marginRight':'1%', 'marginLeft':'1%'})
        initial_list.append(new_entry)
    return initial_list

app = dash.Dash(__name__, external_stylesheets=['https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css'])
app.title = "Research Finder"
app._favicon = (r"assets\favicon.ico")

@app.callback(
    Output('uni_logo', 'src'),
    [Input('interval-component', 'n_intervals'),]
)
def get_img_url(value):#this both updates the DF on log in just in case
    try:
        user =request.authorization['username']
    except:
        user = "None"
    return UNI_LOGO_URL[USER_GROUPS[user]]
@app.callback(
    [Output('university-input', 'options'),Output('area-of-interest-input', 'options')],
    [Input('url-list', 'children'),]
)
def update_dropdowns(noop):
    global df_searched
    universitys = get_dropdown_options(df_searched['affiliations'].values.tolist())
    areas_of_interest = get_dropdown_options(df_searched['subjects'].values.tolist())
    return universitys, areas_of_interest
app.layout = html.Div([html.Br(),
    html.Img(id ='uni_logo' , style={
      "height": "10%",
      "width": "10%",
      "object-fit": "contain",
      "margin-left": '39%',
      'margin-right':'5px'
    }),
    html.Img(src ='https://upload.wikimedia.org/wikipedia/commons/c/ca/Transparent_X.png?20130727130546' , style={
      "height": "1%",
      "width": "1%",
      "object-fit": "contain",
      "margin-left": "5px"
    }),
    html.Img(src=app.get_asset_url('research_finder_logo.jpg'), style={
      "height": "10%",
      "width": "10%",
      "object-fit": "contain",
      "margin-left": "5px"
    }),html.H2(id='show-output', children='',style={"margin-left": "2%"}), html.Br(),
    
    
    # Search bar for "University"
    html.Div([
    html.Div([
        html.H2("University:", style={"margin-left": "4%"}),
        dcc.Dropdown(id='university-input', options=uni_init_lst, value=['All'], placeholder='All available Universities', multi=True, style={"margin-left": "2%", "margin-right": "3%"})
    ], style={"display": "inline-block", "width": "45%"}),
    html.Div([
        html.H2("Area of Interest:", style={"margin-left": "6%"}),
        dcc.Dropdown(id='area-of-interest-input', options=['All'], value=['All'], placeholder='All available Areas of Interest', multi=True, style={"margin-left": "3%", "margin-right": "3%"})
    ], style={"display": "inline-block", "width": "45%"})
])
,
    
    html.Br(),
    html.Div(
        id='url-list',
        children=generate_initial_layout(),
        className='list-group'
    ),
    html.H4("© Ethan Povlot 2023", style={"margin-left": "10%"}),html.Br(),
    # Hidden div to keep track of clicked URLs
    html.Div(id='clicked-urls', style={'display': 'none'}),
    dcc.Interval(id='interval-component', interval=10, n_intervals=1, max_intervals=1)
    
], style={
    'backgroundColor': '#9fe7e7',
    'position': 'absolute',
    'top': 0,
    'left': 0,
    'right': 0,
    'bottom': 0,
    'overflow': 'auto'
})

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)
@app.callback(
    Output('url-list', 'children'),
    [Input('university-input', 'value'),
     Input('area-of-interest-input', 'value')]
)
def update_url_list(university, area_of_interest):
    return generate_initial_layout(university, area_of_interest)


@app.callback(
    [Output(component_id='show-output', component_property='children'),Output('university-input', 'value')],
    [Input('interval-component', 'n_intervals'),]
)
def update_output_div(n_clicks):
    logged_username = request.authorization['username']
    if n_clicks:
        user_group_to_name = {'Emory':'Emory University', 'GT':'Georgia Tech'}
        return '  Hello '+logged_username+', welcome to Research Finder', [user_group_to_name[USER_GROUPS[logged_username]]]
    else:
        return '', ['All']

app.scripts.config.serve_locally = True
@app.callback(
    [Output('clicked-urls', 'children'),Output({'type': 'like-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Output({'type': 'dislike-button', 'index': dash.dependencies.ALL}, 'n_clicks')],
    Input({'type': 'url-link', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input({'type': 'like-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input({'type': 'dislike-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('clicked-urls', 'children'),
    prevent_initial_call=True
)
def update_clicked_urls(n_clicks, likes,dislikes, clicked_urls):
    global df_searched
    username = request.authorization['username']
    global pref_df
    if username == None or username =="":
        return clicked_urls, [None]*len(likes), [None]*len(dislikes)
    if not(username in str(pref_df.columns)):
        pref_df[username+'_weight'] = 0
        pref_df[username+'_dateClicked'] = ''
    if n_clicks != [None]*len(n_clicks):
        for i, clicks in enumerate(n_clicks):
            if clicks:
                clicked_paper_id = df_searched.iloc[i]['paper_id']
                clicked_vec = df_searched.iloc[i]['abstract_vec']
                if not(clicked_paper_id in pref_df['paper_id'].values.tolist()):#need to add the vec for this abstract
                    pref_df = pd.concat([pref_df,
                        pd.DataFrame([[clicked_paper_id]+[clicked_vec]+ [0] * (len(pref_df.columns) - 2)], columns=pref_df.columns)])
                if pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_weight'][0] != 0:
                    #this is so that click doesn't override like/dislike
                    continue
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_weight']=1
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_dateClicked']=datetime.today().strftime("%Y-%m-%d")
    if likes != [None]*len(n_clicks):        
        for i, clicks in enumerate(likes):
            if clicks:
                clicked_paper_id = df_searched.iloc[i]['paper_id']
                clicked_vec = df_searched.iloc[i]['abstract_vec']
                if not(clicked_paper_id in pref_df['paper_id'].values.tolist()):
                    pref_df = pd.concat([pref_df,
                        pd.DataFrame([[clicked_paper_id]+[clicked_vec]+ [0] * (len(pref_df.columns) - 2)], columns=pref_df.columns)])
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_weight']=4
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_dateClicked']=datetime.today().strftime("%Y-%m-%d")

    if dislikes != [None]*len(n_clicks):
        for i, clicks in enumerate(dislikes):
            if clicks:
                clicked_paper_id = df_searched.iloc[i]['paper_id']
                clicked_vec = df_searched.iloc[i]['abstract_vec']
                if clicked_paper_id in likes:
                    likes.remove(clicked_paper_id)
                if not(clicked_paper_id in pref_df['paper_id'].values.tolist()):
                    pref_df = pd.concat([pref_df,
                        pd.DataFrame([[clicked_paper_id]+[clicked_vec]+ [0] * (len(pref_df.columns) - 2)], columns=pref_df.columns)])
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_weight']=-2
                pref_df.loc[pref_df['paper_id']==str(clicked_paper_id), username+'_dateClicked']=datetime.today().strftime("%Y-%m-%d")
    pref_df.to_pickle('user_pref.pkl')
    return clicked_urls, [None]*len(likes), [None]*len(dislikes)



if __name__ == '__main__':
    #cmd ipconfig them
    #Wireless LAN adapter Wi-Fi:  IPv4 Address. . . . . . . . . . . : 10.91.6.65 so thus is the host
    #host='10.91.6.65',
        app.run_server(host='128.61.105.126', port='80', debug=False)
#       serve(app, host='10.91.125.61', port=80, url_scheme='https')
# add filter for which sources
# flexible filtering
# add columns for search dropdowns
# add dates as a filter
#maybe advaced search for dates and full search
#maybe pagination
# store last date used to compute score as num days that they looked at not just num days ago