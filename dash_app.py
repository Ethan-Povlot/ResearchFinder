import dash
import dash_auth
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from flask import request
import pandas as pd
#import modin.pandas as pd
from string import digits
import signal
import numpy as np
from datetime import datetime
import spacy
from collections import Counter
import logging
import os
import re
import dash_daq as daq
import swifter
#import ray
#ray.init(runtime_env={'env_vars': {'__MODIN_AUTOIMPORT_PANDAS__': '1'}})
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
max_pages = 10
nlp = spacy.load("en_core_web_sm")
df = pd.read_pickle('last_month.pkl') #de_duped, osf_data
pref_df = pd.read_pickle('user_pref.pkl') ##fix this
df_searched = df.copy()
user_info_df = pd.read_csv('user_info.csv')
VALID_USERNAME_PASSWORD_PAIRS = dict(zip(user_info_df['Username'].values, user_info_df['password'].values))
USER_GROUPS= dict(zip(user_info_df['Username'].values, user_info_df['User_Group'].values))
USER_GROUPS[None] = 'All'
del user_info_df

UNI_LOGO_URL = {
    'Emory':r'https://1000logos.net/wp-content/uploads/2022/06/Emory-University-Logo.png',
    'GT':r'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Georgia_Tech_seal.svg/1200px-Georgia_Tech_seal.svg.png',
    "None": r'https://upload.wikimedia.org/wikipedia/commons/9/9e/Blank.svg'
}


def get_records_bool(x, uni_lst):
    for name in uni_lst:
        if name.lower() in str(x).lower():
            return 'True'
    return 'False'
def get_dropdown_options(lst):
   
    uni_lst_temp = [item.strip() for val in lst for item in str(val).replace("[", '').replace("]", '').replace("'", "").replace(";", ',').replace(" and ", ',').split(',')]
    flat_list = []
    known_schools = {'@emory.edu', '@gatech.edu', 'Georgia Institute of Technology', 'gatech', 'Emory University'}

    for item in uni_lst_temp:
        item = re.sub(r'\([^)]*\)', '', item).strip()
        if '@' in item:
            item = item.split('@')[1]
            if '.edu' in item:
                item = "@"+item.split('.edu')[0] + '.edu'
        item = item.strip('"\'').rstrip('.')
        
        if item not in ['Central', 'The U', 'nan'] and len(item) > 2 and item not in known_schools:
            flat_list.append(item)
        if item not in known_schools:
            if 'georgia' in str(item).lower() or 'gatech' in  str(item).lower():
                flat_list.append('Georgia Tech')
            if 'emory' in str(item).lower():
                flat_list.append('Emory University')
    counts = Counter(flat_list)
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    output = [x[0].lstrip(digits) for x in sorted_counts]
    if 'Author to whom correspondence should be addressed' in output:
        output.remove('Author to whom correspondence should be addressed')
    if 'Authors to whom correspondence should be addressed' in output:
        output.remove('Authors to whom correspondence should be addressed')
    add_lst = ['All']
    output = add_lst+output
    return output
uni_init_lst = get_dropdown_options(df['affiliations'].values.tolist())[:1000]#['All']#
aoi_init_lsr = get_dropdown_options(df['subjects'].values.tolist())[:1000]#['All']#
def fetch_data(university, area_of_interest, page_num, username, toggle_state,and_uni, search_filter, search_txt):
    global df
    if username == None:
        try:
            username = request.authorization['username']
        except:
            username = None
    text_serarch = True
    # print('search_filter')
    # print(search_filter)
    # print('search_txt')

    # print(search_txt)
    if search_filter in ['', None]:
        search_filter = 'All'
    if search_txt in ['', None]:
        search_txt = ''
        text_serarch = False
    if university == None or university == []:
        university = ['All']
    if area_of_interest == None or area_of_interest == []:
        area_of_interest = ['All']
    if and_uni == None or and_uni == []:
        and_uni = ['All']
    df1 = df.copy()
    if 'Georgia Tech' in university:
        university.append('Georgia Institute of Technology')
        university.append('gatech')
    if 'Emory' in str(university):
        university.append('emory')
    if not ('All' in university):
        df1 = df1[df1['affiliations'].astype(str).str.contains('|'.join(university), regex=True,case=False )]
    if not ('All' in area_of_interest):
        df1 = df1[df1['subjects'].astype(str).str.contains('|'.join(area_of_interest), regex=True,case=False )]
    if toggle_state:#if advance search on
        if not ('All' in and_uni):
            df1 = df1[df1['affiliations'].astype(str).str.contains('|'.join(and_uni), regex=True,case=False )]
    df_out = pd.DataFrame()
    if 'authors' in str(search_filter).lower() and text_serarch:
        df_out=pd.concat([df_out,df1[df1['authors'].astype(str).str.contains(search_txt, case=False)]]) 
    if 'title' in str(search_filter).lower() and text_serarch:
        print('here:title')
        df_out=pd.concat([df_out, df1[df1['title'].astype(str).str.contains(search_txt, case=False)]])
    if 'abstract' in str(search_filter).lower() and text_serarch:
        df_out=pd.concat([df_out, df1[df1['abstract'].astype(str).str.contains(search_txt, case=False)]])
    if 'affiliations' in str(search_filter).lower() and text_serarch:
        df_out=pd.concat([df_out, df1[df1['affiliations'].astype(str).str.contains(search_txt, case=False)]])
    if 'subject' in str(search_filter).lower() and text_serarch:
        df_out=pd.concat([df_out, df1[df1['subjects'].astype(str).str.contains(search_txt, case=False)]])
    global df_searched
    global pref_df
    if not df_out.empty:
        df1= df_out.copy()
        del df_out
    df_searched = df1.copy()
    try:
        if username != None:
            df1 = df1.sort_values(by=[username+'_score'], ascending=False).reset_index(drop=True)
            df1 = pd.concat([df1[df1['source'].astype(str)!='nan'],df1[df1['source'].astype(str)=='nan']])
    except:
        pass
    start_index = 20*(page_num-1)
    end_index = 20*page_num
    global max_pages
    max_pages = -(-df1.shape[0] // 20)
    return df1.iloc[start_index:end_index].to_dict(orient='records')
# Function to generate initial layout
def generate_initial_layout(university=[], area_of_interest=[], page_num=1, username = None, toggle_state =False, and_uni=[],search_filter=None, search_txt=None ):
    data = fetch_data(university, area_of_interest, page_num, username,toggle_state,and_uni, search_filter, search_txt)
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

app = dash.Dash(__name__, external_stylesheets=['https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css', 'https://codepen.io/chriddyp/pen/bWLwgP.css', r'style.css'])
app.title = "Research Finder AI"
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
    [Output('university-input', 'options'),Output('area-of-interest-input', 'options'), Output('and_dropdown', 'options')],
    [Input('url-list', 'children'),],[State('university-input', 'value'),State('area-of-interest-input', 'value')]
)
def update_dropdowns(noop, curr_uni, curr_aoi):
    global df_searched
    universitys = get_dropdown_options(df_searched['affiliations'].values.tolist())
    areas_of_interest = get_dropdown_options(df_searched['subjects'].values.tolist())
    for uni in curr_uni:
        if uni in universitys:
           universitys.remove(uni)
        universitys = [uni]+universitys
    for aoi in curr_aoi:
        if aoi in areas_of_interest:
           areas_of_interest.remove(aoi)
        areas_of_interest = [aoi]+areas_of_interest
    if 'All' in curr_uni:
        universitys = universitys[:1000]
    if 'All' in curr_aoi:
        areas_of_interest = areas_of_interest[:1000]
    return universitys, areas_of_interest, universitys
app.layout = html.Div([html.Br(),
    html.Img(id ='uni_logo' , style={
      "height": "15%",
      "width": "15%",
      "object-fit": "contain",
      "margin-left": '31%',
      'margin-right':'5px'
    }),
    html.Img(src ='https://upload.wikimedia.org/wikipedia/commons/c/ca/Transparent_X.png?20130727130546' , style={
      "height": "1%",
      "width": "1%",
      "object-fit": "contain",
      "margin-left": "5px"
    }),
    html.Img(src=app.get_asset_url('research_finder_ai_1_logo.jpg'), style={
      "height": "15%",
      "width": "15%",
      "object-fit": "contain",
      "margin-left": "5px"
    }),html.H4(id='show-output', children='',style={"margin-left": "2%"}), 
    
   html.Div([
    html.Div([
        html.H4("University:", style={"margin-left": "4%"}),
        dcc.Dropdown(id='university-input', options=uni_init_lst, value=['All'], placeholder='All available Universities', multi=True, style={"margin-left": "2%", "margin-right": "3%"})
    ], style={"display": "inline-block", "width": "40%"}),
    html.Div([
        html.H4("Area of Interest:", style={"margin-left": "6%"}),
        dcc.Dropdown(id='area-of-interest-input', options=['All'], value=['All'], placeholder='All available Areas of Interest', multi=True, style={"margin-left": "3%", "margin-right": "3%"})
    ], style={"display": "inline-block", "width": "40%"}),
    html.Div([
        daq.BooleanSwitch(
            label="Advanced Search",style={"fontSize": "204px"},
            id='toggle-dropdown',
            color="#21e807",
            on=False  # Initial state is Off
        )
    ], style={"display": "inline-block", "width": "15%","margin-left": "3%"})
]),
 html.Div([
    dcc.Markdown("AND University:",id='advance_txt1', style={"margin-left": "2%", "margin-top": "2%","display": "inline-block", "vertical-align": "middle"}),
    dcc.Dropdown(id='and_dropdown', options=['All'], value=['All'], multi=True,  style={"margin-left": "2%", "margin-right": "3%", "width": "34%"}),
        html.Div(id='output-container')
], style={"display": "inline-block", 'width':'38%', "vertical-align": "middle", "margin-left": "2%", "margin-bottom":'2%', "margin-top": "1%"}),
 html.Div([
      html.Div([
        dcc.Dropdown(
            id='search_dropdown',placeholder='Select filter',
            options=['abstract', 'title + abstract', 'title', 'authors', 'affiliations','subject'],
        ),
        ], style={'width': '200px', "margin-left": "3%"}),
        dcc.Input(
            id='search-box',
            type='text',
            placeholder='Enter your search query...'
        ),
    ], style={'display': 'inline-flex'}),
    
    html.Br(),
    html.Div(
        id='url-list',
        children=generate_initial_layout(),
        className='list-group'
    ),
    html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content'),
        html.Div(id='page-buttons-container', children=[
            html.Button('First', id={'type': 'page-button', 'index': 'first'}, style={"backgroundColor": "white", "margin-left": "3%"} ),
            html.Button('Previous', id={'type': 'page-button', 'index': 'previous'}, style={"backgroundColor": "white"}),
            dcc.Input(id='page-input', type='number', value=1, debounce=True, max=max_pages, min =0, style={"width": "100px"}),
            html.Button('Next', id={'type': 'page-button', 'index': 'next'}, style={"backgroundColor": "white"}),
            html.Button('Last', id={'type': 'page-button', 'index': 'last'}, style={"backgroundColor": "white"}),
        ])
    ]),

    html.H4("© Ethan Povlot 2023", style={"margin-left": "10%"}),html.Br(),
    # Hidden div to keep track of clicked URLs
    html.Div(id='clicked-urls', style={'display': 'none'}),dcc.Store(id='previous-value'),dcc.Store(id='username-value'),
    dcc.Interval(id='interval-component', interval=10, n_intervals=1, max_intervals=1)
    
], style={
    'backgroundColor': '#D3D3D3',
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
    [Output('and_dropdown', 'style'),Output('advance_txt1', 'style'),Output('and_dropdown', 'value'), Output('search_dropdown', 'style'), Output('search-box', 'style'),
     Output('search-box', 'value'), Output('search_dropdown', 'value')],
    Input('toggle-dropdown', 'on')
)
def update_dropdown_visibility(is_open):
    dropdown_style = {'display': 'block' if is_open else 'none'}
    return dropdown_style,dropdown_style, ['All'], dropdown_style, dropdown_style, "", ''
@app.callback(
    Output('url-list', 'children'),
    [Input('university-input', 'value'), Input('area-of-interest-input', 'value'), Input('page-input', 'value'), Input('and_dropdown', 'value'),Input('search_dropdown', 'value'),Input('search-box', 'value')], [State('toggle-dropdown', 'on'), State('username-value', 'data')]
)
def update_url_list(university, area_of_interest, page_num, and_uni,search_filter, search_txt, toggle_state, username):
    return generate_initial_layout(university, area_of_interest, page_num, username, toggle_state =toggle_state, and_uni=and_uni, search_filter=search_filter, search_txt=search_txt)


@app.callback(
    [Output(component_id='show-output', component_property='children'),Output('university-input', 'value'), Output('username-value', 'data')],
    [Input('interval-component', 'n_intervals'),]
)
def update_output_div(n_clicks):
    logged_username = request.authorization['username']
    if n_clicks:
        user_group_to_name = {'Emory':'Emory University', 'GT':'Georgia Tech'}
        user_info_df = pd.read_csv('user_info.csv')
        user_info_df['last_login'] = np.where(user_info_df['Username'] == logged_username, datetime.today().strftime('%Y-%m-%d'), user_info_df['last_login'])
        user_info_df.to_csv('user_info.csv', index=False)
        if '@' in logged_username:
            name = logged_username.split('@')[0]
        else:
            name = logged_username
        return '  Hello '+name+', welcome to Research Finder AI', [user_group_to_name[USER_GROUPS[logged_username]]], logged_username
    else:
        return '', ['All'], None

app.scripts.config.serve_locally = True
@app.callback(
    [Output('clicked-urls', 'children'),Output({'type': 'like-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Output({'type': 'dislike-button', 'index': dash.dependencies.ALL}, 'n_clicks')],
    Input({'type': 'url-link', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input({'type': 'like-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input({'type': 'dislike-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    [State('clicked-urls', 'children'),State('username-value', 'data')],
    prevent_initial_call=True
)
def update_clicked_urls(n_clicks, likes,dislikes, clicked_urls, username):
    global df_searched
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


@app.callback(
    [Output('page-input', 'value'),Output('previous-value', 'data')],
    [Input({'type': 'page-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input('page-input', 'value'),Input('university-input', 'value'), Input('area-of-interest-input', 'value'),
    Input('and_dropdown', 'value'),Input('search_dropdown', 'value'),Input('search-box', 'value'), ],
    [State('previous-value', 'data')]
)
def navigate_to_page(page_buttons_clicks, page_input_value,curr1, curr2,curr3, curr4, curr5, old):
    if str(str(curr1)+str(curr2)+str(curr3)+str(curr4)+str(curr5)) !=old:
        return 1, str(str(curr1)+str(curr2)+str(curr3)+str(curr4)+str(curr5))
    triggered_button_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    global max_pages
    new_page_num = 1
    if page_input_value == None:
        page_input_value =1
    if triggered_button_id == 'page-input':
        # When the "Go" button is clicked without clicking a page button
        new_page_num = page_input_value
    else:
        # When a page button is clicked
        current_page_num = page_input_value or 1
        if '"index":"first"'in triggered_button_id:
            new_page_num = 1
        elif '"index":"previous"'in triggered_button_id:
            new_page_num = max(1, current_page_num - 1)
        elif '"index":"next"' in triggered_button_id:
            new_page_num = min(max_pages, current_page_num + 1)
        elif '"index":"last"' in triggered_button_id:
            new_page_num = max_pages
    new_page_num = max(min(new_page_num, max_pages), 1)
    return new_page_num, str(str(curr1)+str(curr2)+str(curr3)+str(curr4)+str(curr5))

   
@app.server.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    #cmd ipconfig them
    #Wireless LAN adapter Wi-Fi:  IPv4 Address. . . . . . . . . . . : 10.91.6.65 so thus is the host
    #host='10.91.6.65',
        app.run_server(host='128.61.105.126', port='80', debug=True)
#       serve(app, host='10.91.125.61', port=80, url_scheme='http')
# add filter for which sources
# flexible filtering
# add columns for search dropdowns
# add dates as a filter
#maybe advaced search for dates and full search
#maybe pagination
# store last date used to compute score as num days that they looked at not just num days ago