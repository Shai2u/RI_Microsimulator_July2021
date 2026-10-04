import colorsys
import json
import os
import re
from pathlib import Path

import dash
from dash import dcc, html, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import geopandas as gpd
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / 'assets' / 'legacy_resources'
HSV_RE = re.compile(r'hsv\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)')


def hsv_to_hex(color):
    """Convert 'hsv(h,s%,v%)' strings (no longer accepted by Plotly 7) to hex."""
    match = HSV_RE.fullmatch(str(color).strip())
    if not match:
        return color
    h, s, v = (float(g) for g in match.groups())
    r, g, b = colorsys.hsv_to_rgb(h / 360, s / 100, v / 100)
    return '#{:02x}{:02x}{:02x}'.format(round(r * 255), round(g * 255), round(b * 255))


def read_colors(file_name):
    df = pd.read_excel(DATA_DIR / file_name)
    for col in df.columns[df.columns.str.startswith('colors_')]:
        df[col] = df[col].map(hsv_to_hex)
    return df


# Inserting Color Labels
colorIncomeCensusgroup = read_colors('colorINcomeCensusGroups.xlsx')  # New April 28
censusIncomeDict = dict(
    zip(colorIncomeCensusgroup['label'], colorIncomeCensusgroup['colors_']))
group_color_dict = read_colors('group_color_jan_7.xlsx')  # read color dictionary
color_labels = read_colors('jan_7_color_labels.xlsx')
colorDict = dict(zip(color_labels['label'], color_labels['colors_']))
colorDictMerge = dict(
    zip(group_color_dict['group_name'], group_color_dict['colors_']))
geoJSONloc = DATA_DIR / 'rib_feb_11.geojson'
csvResultsloc = DATA_DIR / 'result_dec_21_955.csv'
jsonBldgs = gpd.read_file(geoJSONloc).to_crs("EPSG:4326")
resData = pd.read_csv(csvResultsloc, low_memory=False)
resData = resData.iloc[:, 1:]
resData['birth_date'] = pd.to_datetime(resData['birth_date'], errors='coerce')
resData = resData[resData['birth_date'].notna()].copy()
resData['move_in'] = pd.to_datetime(resData['move_in'])
resData['move_out'] = pd.to_datetime(resData['move_out'])


incomeSmallCat = group_color_dict[[
    'income', 'income min', 'income max']].drop_duplicates()
incomeSmallCat.set_index('income', inplace=True)
ageSmallCat = group_color_dict[['Age Group',
                                'Age min', 'Age max']].drop_duplicates()
ageSmallCat.set_index('Age Group', inplace=True)
# ageSmallCat['Age max'] =[45,65,85,150]
ageRangeSmall = [0]+ageSmallCat['Age max'].values.tolist()
ageLbaelsSmall = ageSmallCat.index.tolist()
incomeRangeSmall = incomeSmallCat['income max'].values.tolist() + [0]
incomeLabelSmall = incomeSmallCat.index.tolist()
incomeRangeSmall.reverse()
incomeLabelSmall.reverse()
fontSize = 24
yearListSlider = {
    1970: {'label': '1970', 'style': {'font-size': f'{fontSize}px'}},
    1985: {'label': '1985', 'style': {'font-size': f'{fontSize}px'}},
    2000: {'label': '2000', 'style': {'font-size': f'{fontSize}px'}},
    2015: {'label': '2015', 'style': {'font-size': f'{fontSize}px'}},
    2030: {'label': '2030', 'style': {'font-size': f'{fontSize}px'}},
    2045: {'label': '2045', 'style': {'font-size': f'{fontSize}px'}},
    2060: {'label': '2060', 'style': {'font-size': f'{fontSize}px'}},
}

affordColor = color_labels[color_labels['label']
                           == 'Affordable']['colors_'].values[0]
marketColor = color_labels[color_labels['label']
                           == 'Market']['colors_'].values[0]


class bldFunctionality():
    def __init__(self):
        pass

    def filterByFullYear(self, year_):
        sy = pd.to_datetime(str(year_)+"-1-1")
        eoy = pd.to_datetime(str(year_+1)+"-1-1")  # end of year

        filter_ = (self.ds['move_in'] <= sy) & (self.ds['move_out'] > eoy)
        sample_ds = self.ds[filter_].copy()
        return sample_ds

    def filterDisplacedByFullYearDate(self, year_):
        """Households that moved out during the given year."""
        sy = pd.to_datetime(str(year_)+"-1-1")
        eoy = pd.to_datetime(str(year_+1)+"-1-1")  # end of year

        filter_ = (self.ds['move_out'] >= sy) & (self.ds['move_out'] < eoy)
        return self.ds[filter_].copy()


    def getAffordableMarketPerYear3(self, ye_, gr=group_color_dict, gr2=censusIncomeDict):
        '''Recives Results, Year and Color File'''
        res_1 = self.filterByFullYear(ye_)
        res_2 = res_1[['Group', 'Building Name', 'ap_index',
                       'affordable_living', 'income', 'tenant_cycle', 'birth_date']].copy()
        res_2['income_group'] = res_2['income'].apply(
            incomeClass.getIncomeCategory)
        res_2['raw age'] = ye_ - res_2['birth_date'].dt.year
        res_2['get_mid'] = res_2['raw age'].apply(ageClass.getGroupCategory)
        res_2['age_group'] = res_2['get_mid'].apply(
            lambda x: ageClass.mid2Group[x])
        res_2['year'] = ye_
        res_2['ap_class'] = res_2['affordable_living'].apply(
            lambda x: 'Protected' if x == 1 else 'Market')
        res_2.reset_index(inplace=True, drop=True)
        for i in gr.index:
            row_ = gr.loc[i]
            min_age, max_age, min_income, max_income = row_['Age min'], row_[
                'Age max'], row_['income min'], row_['income max']
            age_group, income_group = row_['Age Group'], row_['income']
            gr_name = row_['group_name']
            color_ = row_['colors_']
            age_color = row_['colors_age']
            income_color = row_['colors_income']
            search_ = ((res_2['raw age'] >= min_age) & (res_2['raw age'] <= max_age)) & (
                (res_2['income'] >= min_income) & (res_2['income'] <= max_income))
            # search_ =
            res_2.loc[search_, 'group_name'] = gr_name
            res_2.loc[search_, 'group_color'] = color_
            res_2.loc[search_, 'AgeGroup4'] = age_group
            res_2.loc[search_, 'IncomeGroup4'] = income_group
            res_2.loc[search_, 'age_color'] = age_color
            res_2.loc[search_, 'income_color'] = income_color
        for item in gr2.items():
            res_2.loc[res_2['income_group'] == item[0],
                      'icnome_color_census'] = item[1]
        res_2.loc[res_2['ap_class'] == 'Protected', 'ap_class'] = 'Affordable'

        res_2.rename(columns={'IncomeGroup4': 'Income', 'AgeGroup4': 'Age Group',
                              'tenant_cycle': 'Tenant Cycle', 'ap_index': 'Door Number'}, inplace=True)
        return res_2






class simDataset(bldFunctionality):
    def __init__(self, ds, js_bldgs, option='default'):
        #         ds['birth_date'] = pd.to_datetime(ds['birth_date'],errors='coerce')
        #         ds = ds[ds['birth_date'].notna()].copy()
        #         ds.loc[:,'move_in'] = ds.loc[:,'move_in'].apply(pd.to_datetime)
        #         ds.loc[:,'move_out'] = ds.loc[:,'move_out'].apply(pd.to_datetime)
        if option == 'WIRE':
            ds = ds[ds['Group'] == 'WIRE'].copy()
            js_bldgs = js_bldgs[js_bldgs['Group'] == 'WIRE'].copy()
        bldFunctionality.__init__(self)
        self.ds = ds

        self.json_bldgs = js_bldgs
        self.json_bldgs_slim = js_bldgs[[
            'Bldg Proje', 'bld_key', 'cnstrct_yr', 'Total Unit', 'Category', 'Group', 'geometry']]
        self.bldgs_list = js_bldgs['Bldg Proje'].unique()
        self.bldgs_ids = js_bldgs['bldgs_id'].unique()
        self.bldg_dict = self.json_bldgs[[
            'bldgs_id', 'cnstrct_yr', 'Bldg Proje', 'Category', 'Group']]
        self.bldg_bld_group = self.getBldGroup()
        bg = self.bldg_bld_group
        self.bldgsGroupDict = dict(zip(bg['Buildings'], bg['Group']))
        gb = dict(zip(bg['Buildings'], bg['Group']))  # Reverse Dict
        self.GroupbldgDict = {
            v1: [k1 for k1, v2 in gb.items() if v1 == v2] for v1 in gb.values()}

    def getBldGroup(self):
        bldg_year_ds = self.bldg_dict[['Bldg Proje', 'Group']].drop_duplicates(
        ).sort_values(by='Group').reset_index(drop=True)
        bldg_year_ds.rename(columns={'Bldg Proje': 'Buildings'}, inplace=True)
        bldg_year_ds = bldg_year_ds[bldg_year_ds['Buildings']
                                    != 'The House'].reset_index(drop=True)
        return bldg_year_ds




class ageClass:
    ageGroup2Mid = {'25-35': 30,
                    '36-45': 40,
                    '46-55': 50,
                    '56-60': 58,
                    '61-65': 63,
                    '66-75': 70,
                    '76-85': 80,
                    '90+': 90}
    mid2Group = {value: key for (key, value) in ageGroup2Mid.items()}

    def getGroupCategory(age_):
        """Returns the group Category for a given Age"""
        if (age_ > 85):
            return 90
        elif (age_ > 75):
            return 80
        elif (age_ > 65):
            return 70
        elif (age_ > 60):
            return 63
        elif (age_ > 55):
            return 58
        elif (age_ > 45):
            return 50
        elif(age_ > 35):
            return 40
        else:
            return 30



class incomeClass:
    def getIncomeCategory(x):
        """Returns a income category for a given income"""
        # get tiltes for given income
        # need to add a sort function
        if (x >= 200000):
            return '$200K+'
        elif (x >= 150000):
            return '$150K-199K'
        elif (x >= 100000):
            return '$100K-149K'
        elif (x >= 75000):
            return '$75K-99K'
        elif (x >= 50000):
            return '$50K-74K'
        elif (x >= 35000):
            return '$35K-49K'
        elif (x >= 25000):
            return '$25K-34K'
        elif (x >= 15000):
            return '$15K-24K'
        else:
            return '<$15K'

    mid_income = {'$200K+': 225000,
                  '$150K-199K': 175000,
                  '$100K-149K': 125000,
                  '$75K-99K': 80000,
                  '$50K-74K': 60000,
                  '$35K-49K': 40000,
                  '$25K-34K': 30000,
                  '$15K-24K': 20000,
                  '<$15K': 7500}


class sim_plot:
    tl_width = 1250*1.5
    tl_height = 600 *1.2
    tl_height2 = 600*1.5
    cont_width = 600*1.5
    mapWidth = 600
    mapHeight1 = tl_height2*2-30
    textSize_ = 24
    @staticmethod
    def treeMapBuilding(r, titleText_):
        fig = px.treemap(r, path=['Group', 'Building Name', 'ap_class', 'Door Number'],
                         color='income', color_continuous_scale='oranges', title=titleText_)
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50),
                          width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))

        return fig

    def treeMapIsland(r, titleText_):
        fig = px.treemap(r, path=['Group', 'Building Name', 'ap_class'],
                         color='income', title=titleText_, color_continuous_scale='oranges')
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50),
                          width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def reasulToLeaveByTime(r, titleText_):
        r = r[['Building Name', 'Group', 'cause',
               'stay_go', 'agentID', 'year']].copy()
        r['status'] = r['stay_go']
        r.loc[r['stay_go'] == 'out',
              'status'] = r.loc[r['stay_go'] == 'out', 'cause']
        r2 = r.groupby(['year', 'status']).agg(
            {'agentID': 'count'}).reset_index()
        r2.rename(columns={'agentID': 'Household Agents'}, inplace=True)
        r2 = r2[r2['status'].isin(
            ['Rent Burden', 'death', 'Mortgage Burden', 'Total Burden'])]

        r2.loc[r2['status'] == 'death', 'status'] = 'Death'

        leaveColorDict = {'Rent Burden': 'blue', 'Death': 'red',
                          'Mortgage Burden': 'purple', 'Total Burden': 'green'}

        fig = px.bar(r2, x="year", y="Household Agents",
                     color="status", color_discrete_map=leaveColorDict, title=titleText_, template='plotly_white')
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.tl_width, height=sim_plot.tl_height2, legend=dict(
            yanchor="top", y=0.9, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def averageAgeByTime(r, titleText_):
        r = r[['Building Name', 'Group', 'death_age', 'raw age',
               'income', 'annual_expenses_burden', 'year']].copy()
        r2 = r.groupby(['year']).agg({'raw age': lambda x: round(
            x.mean(), 0), 'death_age': lambda x: round(x.mean(), 0)}).reset_index()
        r2.rename(columns={'agentID': 'Household Agents',
                           'raw age': 'Mean Age', 'death_age': 'Death Age'}, inplace=True)

        fig = px.line(r2, x="year", y=["Mean Age", "Death Age"], title=titleText_,
                      template='plotly_white', labels=dict(value="Age", variable="Legend"))
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.tl_width, height=sim_plot.tl_height2, legend=dict(
            yanchor="top", y=0.9, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def ageGroupTimeGraph(r, titleText_):
        r = r[['Building Name', 'Group', 'age_group_2', 'agentID', 'year']].copy()
        r2 = r.groupby(['year', 'age_group_2']).agg(
            {'agentID': 'count'}).reset_index()
        r2.rename(columns={'agentID': 'Household Agents',
                           'age_group_2': 'Age Group'}, inplace=True)

        fig = px.line(r2, x="year", y="Household Agents",
                      color="Age Group", color_discrete_map=colorDict, title=titleText_, template='plotly_white')
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.tl_width, height=sim_plot.tl_height2, legend=dict(
            yanchor="top", y=1.05, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def incomeGroupTimeGraph(r, titleText_):
        r = r[['Building Name', 'Group', 'income_group_2', 'agentID', 'year']].copy()
        r2 = r.groupby(['year', 'income_group_2']).agg(
            {'agentID': 'count'}).reset_index()
        r2.rename(columns={'agentID': 'Household Agents',
                           'income_group_2': 'Income Group'}, inplace=True)

        fig = px.line(r2, x="year", y="Household Agents", color="Income Group",
                      color_discrete_map=colorDict, title=titleText_, template='plotly_white')

        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.tl_width, height=sim_plot.tl_height2, legend=dict(
            yanchor="top", y=0.9, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def incomeBurdenTime(r, titleText_):
        r = r[['Building Name', 'Group', 'income',
               'annual_expenses', 'year']].copy()
        r2 = r.groupby(['year']).agg({'income': lambda x: round(
            x.mean(), 0), 'annual_expenses': lambda x: round(x.mean(), 1)}).reset_index()
        r2.rename(columns={'income': 'Mean Income',
                           'annual_expenses': 'Man Annual Exprense'}, inplace=True)

        fig = px.line(r2, x="year", y=["Mean Income", "Man Annual Exprense"], title=titleText_,
                      template='ggplot2', labels=dict(value="US Dollars", variable="Expenses"))
        fig.update_layout(margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.tl_width, height=sim_plot.tl_height2, legend=dict(
            yanchor="top", y=0.9, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def ageByGroupFigure(r, year_, titleText_):
        r2 = r.groupby('Age Group').agg({'get_mid': 'count'}).reset_index().rename(
            columns={'get_mid': 'Households'})
        title_ = str(year_)+' '+titleText_ + ' Age Groups'
        fig = px.bar(r2, x='Age Group', y='Households', template='plotly_white', title=title_, color='Age Group',
                     color_discrete_map=colorDict, category_orders={'Age Group': ['18-44', '45-64', '65-84', '85+']})
        fig.update_layout(showlegend=False, margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))
        return fig

    @staticmethod
    def incomeByGroupFigure(r, year_, titleText_):
        r2 = r.groupby('Income').agg({'get_mid': 'count'}).reset_index().rename(
            columns={'Income': 'Income Group', 'get_mid': 'Households'})
        title_ = str(year_)+' '+titleText_ + ' Income Groups'
        fig = px.bar(r2, x='Income Group', y='Households', template='plotly_white', title=title_, color='Income Group',
                     color_discrete_map=colorDict, category_orders={'Income Group': ['Low', 'Moderate', 'Middle', 'Upper']})
        fig.update_layout(showlegend=False, margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))
        return fig

    @staticmethod
    def incomeByGroupFigureCensus(r, year_, titleText_):
        catIncome = list(censusIncomeDict.keys())
        catIncome.reverse()
        r2 = r.groupby('income_group').agg({'get_mid': 'count'}).reset_index().rename(
            columns={'income_group': 'Income Group Census Categories', 'get_mid': 'Households'})
        title_ = str(year_)+' '+titleText_ + ' Income Group Census Categories'
        fig = px.bar(r2, x='Income Group Census Categories', y='Households', template='plotly_white', title=title_,
                     color='Income Group Census Categories', color_discrete_map=censusIncomeDict, category_orders={'Income Group Census Categories': catIncome})
        fig.update_layout(showlegend=False, margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))
        return fig

    @staticmethod
    def bubbleAgeIncomeClass(r, year_, titleText_):
        r2 = r.groupby(['ap_class', 'group_name', 'Age Group', 'Income']).agg(
            {'raw age': 'count'}).reset_index().rename(columns={'raw age': 'count', 'ap_class': 'Ap Type'})

        title_ = str(year_)+' '+titleText_ + ' Age/Income'

        fig = px.scatter(r2, x="Age Group", y="Income",
                         size="count", color="group_name", color_discrete_map=colorDictMerge, facet_col='Ap Type', title=title_, size_max=30,
                         category_orders={"Age Group": ["18-44", "45-64", "65-84", "85+"],
                                          "Income": ['Upper', 'Middle', 'Moderate', 'Low']}, template='ggplot2')
        fig.update_layout(showlegend=False, margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.cont_width, height=sim_plot.tl_height,font=dict(size=sim_plot.textSize_))

        return fig

    @staticmethod
    def sunburstGroupsAffordMarketYearColor3(r, year_, color_field='raw age', colorDict_=colorDict, group_color_dict=group_color_dict):
        title_ = f'{year_} : Market Vs Affordable Units Age/Income in WIRE'
        # color_discrete_map = color_group_map_
        colors_ = group_color_dict['colors_age'].unique().tolist()
        fig = px.sunburst(r, path=['ap_class', 'Age Group', 'Income'],
                          color=color_field, color_continuous_scale=colors_, title=title_,)

        labels_text = fig.data[0].labels.tolist()
        colorLabels = tuple(colorDict_[item] for item in labels_text)
        fig.data[0].marker.colors = colorLabels
        fig.update_traces(textinfo="label+percent entry")
        fig.update_layout(showlegend=False, margin=dict(l=50, r=50, t=100, b=50), legend=dict(
            yanchor="top", y=1, xanchor="left", x=1, orientation="h"), width=sim_plot.cont_width, height=sim_plot.tl_height+50,font=dict(size=sim_plot.textSize_))
        return fig

    @staticmethod
    def getAgentsByRangeAllGroupInOut2(ds, years_range):
        for ye_ in years_range:
            if np.mod(ye_, 10) == 0:
                print('year:', ye_)
            if ye_ == years_range[0]:
                all_years = sim_plot.getAgentYearGroupInOut(ds, ye_).copy()
            else:
                toConcat = sim_plot.getAgentYearGroupInOut(ds, ye_).copy()
                all_years = pd.concat([all_years, toConcat])
        return all_years

    def getAgentYearGroupInOut(ds, ye_):
        ds_fyear = ds.filterByFullYear(ye_)
        ds_moveout = ds.filterDisplacedByFullYearDate(ye_)
        ds_fyear = ds_fyear[['Building Name', 'Group', 'tenant_cycle', 'ApartmentType', 'comment 1', 'affordable_living', 'cause', 'move_in', 'move_out',
                             'birth_date', 'death_age', 'death_date', 'income', 'annual_expenses', 'annual_expenses_burden', 'agentID']].copy()
        ds_moveout = ds_moveout[['Building Name', 'Group', 'tenant_cycle', 'ApartmentType', 'comment 1', 'affordable_living', 'cause', 'move_in', 'move_out',
                                 'birth_date', 'death_age', 'death_date', 'income', 'annual_expenses', 'annual_expenses_burden', 'agentID']].copy()
        ds_fyear['annual_expenses_burden'] = ds_fyear['annual_expenses'] / \
            ds_fyear['income']
        ds_moveout['annual_expenses_burden'] = ds_moveout['annual_expenses'] / \
            ds_moveout['income']
        ds_moveout['stay_go'] = 'out'
        ds_fyear['stay_go'] = 'stay'
        ds_fyear.loc[pd.to_datetime(ds_fyear['move_in']).dt.year == ye_, 'stay_go'] = 'new'
        all_y = pd.concat([ds_fyear, ds_moveout])
        all_y['income_group'] = all_y['income'].apply(
            incomeClass.getIncomeCategory)
        all_y['raw age'] = ye_ - all_y['birth_date'].dt.year
        all_y['get_mid'] = all_y['raw age'].apply(
            ageClass.getGroupCategory)
        all_y['age_group'] = all_y['get_mid'].apply(lambda x:
                                                    ageClass.mid2Group[x])
        all_y['year'] = ye_
        return all_y




    def AgentCycle(r, year_, title_):
        affordCycles = r.loc[r['ap_class'] == 'Affordable', 'Tenant Cycle']
        marketCycles = r.loc[r['ap_class'] == 'Market', 'Tenant Cycle']
        histogramFig = go.Figure()
        histogramFig.add_trace(go.Histogram(
            x=affordCycles, name='Affordable Units'))
        histogramFig.add_trace(go.Histogram(
            x=marketCycles, name='Market Units'))

        # Overlay both histograms
        histogramFig.update_layout(barmode='overlay', title=f'Tenant Cycles {year_} {title_}', template='plotly_white', legend=dict(
            yanchor="top", y=0.85, xanchor="left", x=0.01, orientation="h"), margin=dict(l=50, r=50, t=100, b=50), width=sim_plot.cont_width, height=sim_plot.tl_height)
        # Reduce opacity to see both histograms
        histogramFig.update_traces(opacity=0.75)
        return histogramFig


resData.loc[resData['Building Name'] ==
            'island house', 'Building Name'] = 'Island House'
jsonBldgs.loc[jsonBldgs['Bldg Proje'] ==
              'island house', 'Bldg Proje'] = 'Island House'
jsonBldgs = jsonBldgs.loc[jsonBldgs['Bldg Proje'] != 'The House']
jsonBldgs['Buildings'] = jsonBldgs['Bldg Proje']
rib = jsonBldgs.copy()
resultsAll1 = simDataset(resData, jsonBldgs)


allByYear = sim_plot.getAgentsByRangeAllGroupInOut2(
    resultsAll1, range(1976, 2080))



allByYear['age_group_2'] = pd.cut(
    allByYear['raw age'].values, ageRangeSmall, labels=ageLbaelsSmall)
allByYear['income_group_2'] = pd.cut(
    allByYear['income'].values, incomeRangeSmall, labels=incomeLabelSmall)
# allByYear.groupby('year')
allByYearStay = allByYear[allByYear['stay_go'] != 'out'].copy().reset_index()
# Get a WIRE subset
allByYearWire = allByYearStay.loc[allByYearStay['Group'] == 'WIRE'].copy()
allByYearWire.reset_index(inplace=True, drop=True)

allByYearNotWire = allByYearStay.loc[allByYearStay['Group'] != 'WIRE'].copy()
allByYearNotWire.reset_index(inplace=True, drop=True)


def addAffordableStatistics(r):
    r_dummy = pd.get_dummies(r[['year', 'affordable_living']], columns=[
                             'affordable_living'])
    r_dummy_agg = r_dummy.groupby('year').agg('sum').reset_index()
    r_dummy_agg = r_dummy_agg.rename(columns={
                                     'affordable_living_0': 'Market units', 'affordable_living_1': 'Affordable units'})
    r_dummy_agg['total'] = r_dummy_agg['Market units'] + \
        r_dummy_agg['Affordable units']
    r_dummy_agg['Market Percent'] = r_dummy_agg['Market units'] / \
        r_dummy_agg['total']
    r_dummy_agg['Affordable Percent'] = r_dummy_agg['Affordable units'] / \
        r_dummy_agg['total']
    return r_dummy_agg


def addAffordableStatisticsByBuildings(r):
    r_dummy = pd.get_dummies(
        r[['year', 'Group', 'Building Name', 'affordable_living']], columns=['affordable_living'])
    r_dummy_agg = r_dummy.groupby(
        ['Group', 'Building Name', 'year']).agg('sum').reset_index()
    r_dummy_agg = r_dummy_agg.rename(columns={
                                     'affordable_living_0': 'Market units', 'affordable_living_1': 'Affordable units'})
    r_dummy_agg['total'] = r_dummy_agg['Market units'] + \
        r_dummy_agg['Affordable units']
    r_dummy_agg['Market Percent'] = r_dummy_agg['Market units'] / \
        r_dummy_agg['total']
    r_dummy_agg['Affordable Percent'] = r_dummy_agg['Affordable units'] / \
        r_dummy_agg['total']
    return r_dummy_agg


allAffordableByBldg = addAffordableStatisticsByBuildings(allByYearStay)
NotWireAffordable = addAffordableStatistics(allByYearNotWire)
AllAffordable = addAffordableStatistics(allByYearStay)
WireAffordable = addAffordableStatistics(allByYearWire)


def affordabilityTimeSeriesAgregattedGraph(aw, mC, aC, title_):
    bldgsGroupTitle = title_
    fig = go.Figure()
    line_coop = dict(color=mC, width=3)
    line_rent = dict(color=aC, width=3)
    percent_c = aw['Market Percent']
    percent_r = aw['Affordable Percent']
    fig.add_trace(go.Scatter(x=aw['year'], y=(aw['Market units']),
                             mode='lines',
                             name='Market units',
                             line=line_coop,
                             hovertemplate='<br><b>Market Units</b>:%{y:}<br>' +
                             '<b>Percent:</b> %{text} %',
                             text=['{:.1f}'.format(p*100, 1)
                                   for p in percent_c]
                             ))

    fig.add_trace(go.Scatter(x=aw['year'], y=(aw['Affordable units']),
                             mode='lines',
                             name='Affordable units',
                             line=line_rent,
                             hovertemplate='<br><b>Affordable Units</b> : %{y:}<br>' +
                             '<b>Percent : </b>%{text} %',
                             text=['{:.1f}'.format(p*100, 1)
                                   for p in percent_r],
                             ))

    fig.add_trace(go.Scatter(x=aw['year'], y=(aw['total']),
                             mode='lines',
                             name='Total Units',
                             line=dict(color='hsl(30, 96%, 74%)',
                                       width=2, dash='dash'),
                             hovertemplate='<br><b>Total Units</b> : %{y:}<br>'
                             ))
    maxY = aw['total'].max()
    maxY *= 1.25

    fig.update_xaxes(range=[1976, 2076], showline=True,
                     linecolor='rgb(150,150,150)', title='Year')
    fig.update_yaxes(range=[0, maxY], showline=True,
                     linecolor='rgb(150,150,150)', title='Households')
    fig.update_layout(width=sim_plot.tl_width, height=sim_plot.tl_height2, plot_bgcolor='rgba(255,255,255,0)', legend=dict(yanchor="top", y=0.97, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",
                      margin=dict(l=50, r=50, t=100, b=50), title=bldgsGroupTitle + " Market and Affordable Units Time Series",font=dict(size=sim_plot.textSize_))
    return fig


def baseFigForAffordableTS(title_, ymax, yloc):
    fig = go.Figure()
    fig.update_xaxes(range=[1976, 2076], showline=True,
                     linecolor='rgb(150,150,150)', title='Year')
    fig.update_yaxes(range=[0, ymax], showline=True,
                     linecolor='rgb(150,150,150)', title='Households')
    fig.update_layout(width=sim_plot.tl_width, height=sim_plot.tl_height2, plot_bgcolor='rgba(255,255,255,0)', legend=dict(yanchor="top", y=yloc, xanchor="left", x=0.01, orientation="h"), hoverlabel_align="auto", hovermode="x unified",
                     margin=dict(l=50, r=50, t=100, b=50), title=title_ + " Market and Affordable Units Time Series",font=dict(size=sim_plot.textSize_))
    return fig


def baseFigForAffordableTSAddTrace(fig, r, colx, coly, line_style, hovertext_, name_):
    fig.add_trace(go.Scatter(x=r[colx], y=(r[coly]),
                             mode='lines',
                             name=name_,
                             line=line_style,
                             hovertemplate=hovertext_,
                             legendgroup=name_))
    return fig


def createAffordableInduvidualBldgs(title_, maxY, yloc, year_):
    """Per-building market/affordable time series for the WIRE buildings."""
    fig1 = baseFigForAffordableTS(title_, maxY, yloc)
    r1 = allAffordableByBldg[(allAffordableByBldg['Group'] == 'WIRE')
                             & (allAffordableByBldg['year'] < year_)]
    BldgsList = r1['Building Name'].unique().tolist()
    lineDashl = ['Line', 'dash', 'dot', 'dashdot']
    for i in range(len(BldgsList)):
        bldg = BldgsList[i]
        if i == 0:
            line_style_ = dict(color=marketColor, width=i+1)
        elif i in [1, 4, 8, 12]:
            line_style_ = dict(color=marketColor, width=i+1, dash=lineDashl[1])
        elif i in [2, 5, 9, 13]:
            line_style_ = dict(color=marketColor, width=i+1, dash=lineDashl[2])
        else:
            line_style_ = dict(color=marketColor, width=i+1, dash=lineDashl[3])

        r = r1[r1['Building Name'] == bldg].copy()
        r.reset_index(inplace=True, drop=True)

        hovertext_ = [
            f'<br><b>Market Units</b>:{r.loc[i,"Market units"]}<br><b>Percent:</b> {"{:.1%}".format(r.loc[i,"Market Percent"])}' for i in range(len(r))]
        # ,text = ['{:.1f}'.format(p*100,1) for p in r['Market Percent']]
        fig1 = baseFigForAffordableTSAddTrace(
            fig1, r, colx='year', coly='Market units', line_style=line_style_, hovertext_=hovertext_, name_=bldg)
    r = r1.copy()
    for i in range(len(BldgsList)):
        bldg = BldgsList[i]
        if i == 0:
            line_style_ = dict(color=affordColor, width=i+1)
        elif i in [1, 4, 8, 12]:
            line_style_ = dict(color=affordColor, width=i+1, dash=lineDashl[1])
        elif i in [2, 5, 9, 13]:
            line_style_ = dict(color=affordColor, width=i+1, dash=lineDashl[2])
        else:
            line_style_ = dict(color=affordColor, width=i+1, dash=lineDashl[3])
        r = r1[r1['Building Name'] == bldg].copy()
        r.reset_index(inplace=True, drop=True)
        # line_style_ = dict(color=affordColor, width=i+1)
#         r = allAffordableByBldg[allAffordableByBldg['Building Name']==bldg].copy()
#         r.reset_index(inplace=True,drop=True)

        hovertext_ = [
            f'<br><b>Affordable Units</b>:{r.loc[i,"Affordable units"]}<br><b>Percent:</b> {"{:.1%}".format(r.loc[i,"Affordable Percent"])}' for i in range(len(r))]
        # ,text = ['{:.1f}'.format(p*100,1) for p in r['Market Percent']]
        fig1 = baseFigForAffordableTSAddTrace(
            fig1, r, colx='year', coly='Affordable units', line_style=line_style_, hovertext_=hovertext_, name_=bldg)
    return fig1


def getCurrentScope(r):
    uniqBldgs = r['Building Name'].nunique()
    agentsC = len(r)
    tenantCycle = round(r['Tenant Cycle'].mean(), 1)
    meanAge = round(r['raw age'].mean(), 1)
    meanIncome = round(r['income'].mean(), 0)
    rtText = f"In Scope - Buildings: {uniqBldgs}, HH: {agentsC}, Tenant Cycles: {tenantCycle} Mean Age:{meanAge}, Mean Income:{meanIncome}$"
    return rtText


SCENE_3D_URL = 'https://technion-gis.maps.arcgis.com/apps/instant/3dviewer/index.html?appid=70a5849b08a643e188c1e082cfb579c4'


def getIframeURLfor3D(zoomto='All of The Island'):
    buildingsIframeDict = {
        'base': SCENE_3D_URL,
        'Roosevelt Landings': '&viewpoint=cam:-8232294.14564431,4976971.55542625,188.707,102100;53.45,62.097',
        'Manhattan park': '&viewpoint=cam:-8231926.10204526,4978087.15207409,101.822,102100;149.074,73.52',
        'The Octagon': '&viewpoint=cam:-8231799.25126456,4978433.16302919,116.932,102100;110.548,74.849',
        'Island House': '&viewpoint=cam:-8232262.63739977,4977617.48364878,131.456,102100;153.421,69.801',
        'Rivercross': '&viewpoint=cam:-8232476.22640797,4977191.75742142,116.144,102100;88.42,71.129',
        'Riverwalk Landing': '&viewpoint=cam:-8232744.92622803,4976927.06005498,135.343,102100;127.737,70.598',
        'Riverwalk Point': '&viewpoint=cam:-8232254.75160611,4976616.19499,129.249,102100;5.637,65.816',
        'Westview': '&viewpoint=cam:-8232152.701749,4977766.89078352,122.765,102100;153.421,69.801',
        'Riverwalk place': '&viewpoint=cam:-8232599.54300243,4976981.47710137,178.258,102100;97.706,58.909',
        'Riverwalk Court': '&viewpoint=cam:-8232748.95180919,4976914.78684295,129.03,102100;111.238,71.718',
        'Riverwalk Crossing': '&viewpoint=cam:-8232771.27998685,4976891.42089825,135.343,102100;127.737,70.598',
        '2-4 River Road': '&viewpoint=cam:-8232014.67558545,4977890.22421553,101.822,102100;149.074,73.52',
        'Wire': '&viewpoint=cam:-8232455.27430039,4976611.10725427,942.614,102100;34.366,38.656',
        'All of The Island': '&viewpoint=cam:-8233187.87589454,4975509.19937045,682.802,102100;32.257,68.071',
        'Northtown & Southtown': '&viewpoint=cam:-8233187.87589454,4975509.19937045,682.802,102100;32.257,68.071'}
    viewpoint = buildingsIframeDict.get(zoomto, buildingsIframeDict['All of The Island'])
    return f"{buildingsIframeDict['base']}{viewpoint}"


def boundsCenter(gdf):
    minx, miny, maxx, maxy = gdf.total_bounds
    return (minx + maxx) / 2, (miny + maxy) / 2


def updateMapYear1(value_, rMap, r, cat='aib', zoomto='All of The Island'):

    if zoomto == 'Wire':
        lon_, lat_ = boundsCenter(rib[rib['Group'] == 'WIRE'])
        zoom_ = 16
    elif zoomto in rib['Buildings'].values:
        lon_, lat_ = boundsCenter(rib[rib['Buildings'] == zoomto])
        zoom_ = 17
    else:  # 'All of The Island', 'Northtown & Southtown' and anything unknown
        zoom_ = 14.5
        lat_ = 40.7624
        lon_ = -73.949
    rib_filter = rMap[rMap['cnstrct_yr'] < value_].copy()
    # r2 = r.copy()
    mapAggData = r.groupby('Building Name').agg({'Age Group': lambda x: x.value_counts().index[0], 'Income': lambda x: x.value_counts().index[0], 'group_name': lambda x: x.value_counts(
    ).index[0], 'Tenant Cycle': lambda x: np.round(x.mean(), 1), 'income': lambda x: np.round(x.mean(), 1), 'raw age': lambda x: np.round(x.mean(), 1)}).reset_index()
    mapAggData.rename(columns={'group_name': 'Age Income',
                               'income': 'Mean Income', 'raw age': 'Mean Age'}, inplace=True)
    if ('Market' in r['ap_class'].unique().tolist()):
        affordableMarket = pd.get_dummies(r, columns=['ap_class']).groupby('Building Name').agg(
            {'ap_class_Affordable': 'sum', 'ap_class_Market': 'sum', 'Door Number': 'count'}).reset_index()
        affordableMarket['Affordable Ratio'] = affordableMarket['ap_class_Affordable'] / \
            affordableMarket['Door Number']
    else:
        affordableMarket = pd.get_dummies(r, columns=['ap_class']).groupby('Building Name').agg(
            {'ap_class_Affordable': 'sum', 'Door Number': 'count'}).reset_index()
        affordableMarket['Affordable Ratio'] = 1

    affordableMarket = affordableMarket[['Building Name', 'Affordable Ratio']]
    mapAggData = pd.merge(mapAggData, affordableMarket,
                          on='Building Name', how='left')  # Affordable Ratio
    mapAggData['Affordable Ratio'] = mapAggData['Affordable Ratio'].fillna(0)
    # colorDictMerge
    mapModifed = pd.merge(rib_filter, mapAggData, how='right',
                          left_on='Buildings', right_on='Building Name')

    if cat == 'aib':
        colorCat = 'Age Income'
        discreteMap = colorDictMerge
    elif cat == 'income':
        colorCat = 'Income'
        discreteMap = colorDict
    elif cat == 'meanIncome':
        colorCat = 'Mean Income'
    elif cat == 'meanAge':
        colorCat = 'Mean Age'
    elif cat == 'age':
        colorCat = 'Age Group'
        discreteMap = colorDict
    elif cat == 'apNum':
        colorCat = 'Total Unit'
    elif cat == 'afPercent':
        colorCat = 'Affordable Ratio'
    else:
        colorCat = 'Tenant Cycle'

    if cat in ['cycle', 'apNum', 'afPercent', 'meanIncome', 'meanAge']:
        localCoConColorSclae = {'meanIncome': 'YlOrRd', 'meanAge': ['#e6ad00', '#fefdfc'],
                                'cycle': 'YlOrBr', 'apNum': 'YlOrBr', 'afPercent': 'YlOrBr'}
        rangeColorDict = {'meanIncome': (10000, 350000), 'meanAge': (40, 65),
                          'cycle': (0, 7), 'apNum': (50, 900), 'afPercent': (0, 1)}

        chosenScale = localCoConColorSclae[cat]
        rangeColor_ = rangeColorDict[cat]
        fig_map = px.choropleth_map(mapModifed, geojson=mapModifed.geometry, locations=mapModifed.index, color=colorCat, color_continuous_scale=chosenScale,
                                       map_style="carto-positron",
                                       hover_name='Bldg Proje',
                                       custom_data=['Buildings', 'Group'],
                                       range_color=rangeColor_
                                       )
        fig_map.update_traces(colorbar=dict(
            thickness=5, len=0.25, ticks='inside', showticklabels=False))  # ) #marker_showscale=False
    else:
        fig_map = px.choropleth_map(mapModifed, geojson=mapModifed.geometry, locations=mapModifed.index, color=colorCat, color_discrete_map=discreteMap,
                                       map_style="carto-positron",
                                       hover_name='Bldg Proje',
                                       custom_data=['Buildings', 'Group']
                                       ).update_traces(showlegend=True)
    mapbox_ = dict(bearing=33, pitch=0, zoom=zoom_,
                   center=dict(lat=lat_, lon=lon_))
    fig_map.update_layout(autosize=True, height=sim_plot.mapHeight1, width=sim_plot.mapWidth, map=mapbox_, legend=dict(
        yanchor="top", y=0.1, xanchor="left", x=0.01, orientation="h"),margin=dict(l=0, r=0, t=0, b=0))

    return fig_map


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

valYear = 2000
figAll = affordabilityTimeSeriesAgregattedGraph(
    aw=AllAffordable[AllAffordable['year'] <= valYear], mC=marketColor, aC=affordColor, title_='All of the Island')

cellTimeFigure = dcc.Graph(id='time-graph', figure=figAll)
cellTimeFigureProjDash = dcc.Graph(id='time-graphProjDash', figure=figAll)
currentData = resultsAll1.getAffordableMarketPerYear3(valYear)
figSunBurst = sim_plot.sunburstGroupsAffordMarketYearColor3(
    currentData, valYear)

bubbleFig_ = sim_plot.bubbleAgeIncomeClass(currentData, valYear, 'All')
fig_map = updateMapYear1(valYear, rib.copy(), currentData,
                         'age', zoomto='All of The Island')
mapColorDropDownMenu = dcc.Dropdown(id='mapcolor-menu',
                                    options=[
                                        {'label': 'Age/Income', 'value': 'aib'},
                                        {'label': 'Income Groups',
                                            'value': 'income'},
                                        {'label': 'Mean Income ($)',
                                         'value': 'meanIncome'},
                                        {'label': 'Age Groups', 'value': 'age'},
                                        {'label': 'Mean Age', 'value': 'meanAge'},
                                        {'label': 'Apartment Cycles',
                                            'value': 'cycle'},
                                        {'label': 'Apartment Numbers',
                                            'value': 'apNum'},
                                        {'label': 'Affordable Percent',
                                            'value': 'afPercent'}
                                    ],
                                    value='aib'
                                    )
timeDropDownMenu = dcc.Dropdown(id='time-menu',
                                options=[
                                    {'label': 'Affordable Market', 'value': 'am'},
                                    {'label': 'Leaving', 'value': 'leave'},
                                    {'label': 'Life Expectancy', 'value': 'life'},
                                    {'label': 'Income Expenses', 'value': 'ie'},
                                    {'label': 'Age Groups', 'value': 'ageg'},
                                    {'label': 'Income Groups', 'value': 'ig'},
                                ],
                                value='am'
                                )
col1 = dbc.Card(
    [
        dcc.Dropdown(
            id='scale-observation',
            options=[
                {'label': 'Induvidual Building', 'value': 'ind'},
                {'label': 'Wire All Buildings', 'value': 'wireb'},
                {'label': 'Wire', 'value': 'wire'},
                {'label': 'South/North Town', 'value': 'NotWire'},
                {'label': 'All of the Island', 'value': 'ri'}
            ],
            value='ri'
        ), mapColorDropDownMenu, dcc.Graph(id='map-graph', figure=fig_map)
    ],
    body=True
)
Menu3d = dcc.Dropdown(
    id='menu3D',
    options=[
        {'label': '3D Not Updated', 'value': 'No3D'},
        {'label': '3D Updated', 'value': 'Yes3D'},
    ],
    value='No3D'
)

contextualDropMenu = dcc.Dropdown(id='contextual-menu',
                                  options=[
                                      {'label': 'Age Income Bubbles',
                                          'value': 'aib'},
                                      {'label': 'Income Groups',
                                          'value': 'income'},
                                      {'label': 'Income Groups Census Categories',
                                          'value': 'incomeCensus'},
                                      {'label': 'Age Groups', 'value': 'age'},
                                      {'label': 'Apartment Cycles',
                                          'value': 'cycle'},
                                      {'label': 'Induvidual Apartments',
                                          'value': 'treemap'}
                                  ],
                                  value='aib'
                                  )


contextualCard = dbc.Card([contextualDropMenu, dcc.Graph(
    id='contextual-graph', figure=bubbleFig_)])

contextualCardProjDash = dbc.Card( dcc.Graph(
    id='contextual-graphProDash', figure=bubbleFig_))


sunBurstFigure = dbc.Card([dcc.Graph(id='sunBurst-graph', figure=figSunBurst)])

sunBurstFigureProjDash = dbc.Card(
    [dcc.Graph(id='sunBurst-graphProjDash', figure=figSunBurst)])

touchScreen = html.Div([
                        html.Table(
    [
        html.Tr([
                html.Td([html.Div(dbc.Card(html.H3(id="graph_ri"),
                                           style={'text-align': 'center'}, body=True))]),
                html.Td([html.Div(dbc.Card(html.H3(["Household in scope: Mean Age: Mean Income:"],
                                                   id="executive_sum_text"), style={'text-align': 'center'}, body=True))], colSpan='3')
                # html.Td([dbc.Card(dbc.CardBody([dcc.Input(id='figure_text', value='Figures', type='text'), html.Button('Download Figures', id='downloadB')])
                #                   )], style={'text-align': 'right'})

                ]),
        html.Tr(
            [
                html.Td(
                    [
                        dbc.Card([Menu3d, (html.Iframe(id='ifame-cell', height=f"{sim_plot.mapHeight1+40}px", width=f"{sim_plot.mapWidth}px",
                                                       src=SCENE_3D_URL))], body=True)
                    ], rowSpan='3'),
                html.Td([col1], rowSpan='3', style={
                    'border-style': 'solid', 'border-width': '0px', 'width': '400px'}),
                html.Td([dbc.Card(dbc.CardBody([
                        html.Div(dbc.Card(
                            dcc.Slider(id='year-slider', min=1976, max=2080, step=1, marks=yearListSlider, value=2000), style={"height": "100%"}, body=True),
                            #
                            style={'width': '74.5%','height':'100px', 'display': 'inline-block'}),
                        html.Div(dbc.Card(timeDropDownMenu, style={"height": "100%"}, body=True), style={
                                 'width': '24.5%', 'display': 'inline-block', 'vertical-align': 'top'})

                        ]))], colSpan='2', style={'border-style': 'solid', 'border-width': '0px'})
            ]
        ),
        html.Tr(
            [
                html.Td(dbc.Card(dbc.Card([cellTimeFigure]), body=True), colSpan='2', style={
                    'border-style': 'solid', 'border-width': '0px'})

            ]
        ),
        html.Tr(
            [
                html.Td(dbc.Card(sunBurstFigure, body=True), style={
                    'border-style': 'solid', 'border-width': '0px'}),
                html.Td(dbc.Card(contextualCard, body=True), style={
                    'border-style': 'solid', 'border-width': '0px'})

            ]
        )
    ],
    style={'border-collapse': 'collapse',
           'border-spacing': '0', 'width': '100%','font-size':'24px'}
)

])

projDash = html.Div([
    html.Table(
        [
            html.Tr([
                html.Td([html.Div(dbc.Card(html.H5(['All of the Island:'], id="bldYearProj"),
                                           style={'text-align': 'center'}, body=True))]),
                html.Td([html.Div(dbc.Card(html.H6(["In Score - Buidlings:0, HH:0, Tenant Cycles:0, Mean  Age:0, Mean Income:0"],
                                                   id="executiveSumTextProj"), style={'text-align': 'center'}, body=True))])

            ]),
            html.Tr(
                [
                    html.Td([dbc.Card(dbc.CardBody([
                        html.Div(dbc.Card(
                            dcc.Slider(id='yearSliderProj', min=1976, max=2080, step=1, marks=yearListSlider, value=2000), style={"height": "100%"}, body=True),
                            style={'width': '100%'})
                    ]))], colSpan='2', style={'border-style': 'solid', 'border-width': '0px'})
                ]
            ),
            html.Tr(
                [
                    html.Td(dbc.Card(dbc.Card([cellTimeFigureProjDash]), body=True), colSpan='2', style={
                        'border-style': 'solid', 'border-width': '0px'})
                ]
            ),
            html.Tr(
                [
                    html.Td(dbc.Card(sunBurstFigureProjDash, body=True), style={
                            'border-style': 'solid', 'border-width': '0px'}),
                    html.Td(dbc.Card(contextualCardProjDash, body=True), style={
                            'border-style': 'solid', 'border-width': '0px'})

                ]
            )

        ],
        style={'border-collapse': 'collapse',
               'border-spacing': '0', 'width': '100%'}

    ),
    dcc.Store(id='projDash-state'),
    dcc.Interval(
        id='interval-component_DashProj',
        interval=1*1500,  # in milliseconds
        n_intervals=0
    )

])

proj3D = html.Div([html.Table(
    [
        html.Tr(
            [
                html.Td(
                    [
                        dbc.Card([(html.Iframe(id='ifame-cellProj3D', height="1080px", width="580px",
                                               src=SCENE_3D_URL))], body=True)
                    ]),
                html.Td([dbc.Card(dcc.Graph(id='map-graphProj3D', figure=fig_map), body=True)], style={
                    'border-style': 'solid', 'border-width': '0px', "height":"1080px", 'width': '580px'}),
            ]
        ), dcc.Store(id='proj3D-state'), dcc.Interval(
            id='interval-component_Dash3D',
            interval=1*1500,  # in milliseconds
            n_intervals=0
        )
    ],
    style={'border-collapse': 'collapse',
           'border-spacing': '0', 'width': '100%'}
)
])

Only3D = html.Div([dcc.Store(id='only3D-state'), html.Iframe(id='ifame-cellOnly3D', height="1200px", width="3500px",
                                              src=SCENE_3D_URL),dcc.Interval(
            id='interval_Only3D',
            interval=1*1500,  # in milliseconds
            n_intervals=0)
    ],style={'border-collapse': 'collapse',
          'border-spacing': '0', 'width': '100%'})

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')


])



# ---------------------------------------------------------------------------
# Input validation: every value arriving from the browser is checked against
# a known list before it is used, so crafted requests cannot inject anything.
# ---------------------------------------------------------------------------
YEAR_MIN, YEAR_MAX, YEAR_DEFAULT = 1976, 2080, 2000
RESOLUTIONS = ('ind', 'wireb', 'wire', 'NotWire', 'ri')
CONTEXTS = ('aib', 'income', 'incomeCensus', 'age', 'cycle', 'treemap')
TIME_CATEGORIES = ('am', 'leave', 'life', 'ie', 'ageg', 'ig')
MAP_CATEGORIES = ('aib', 'income', 'meanIncome', 'age',
                  'meanAge', 'cycle', 'apNum', 'afPercent')
MENU_3D = ('No3D', 'Yes3D')
BUILDINGS = frozenset(rib['Buildings'])
ZOOM_TARGETS = BUILDINGS | {'All of The Island', 'Wire', 'Northtown & Southtown'}


def cleanChoice(value, allowed, default):
    return value if value in allowed else default


def cleanYear(value):
    try:
        return min(max(int(value), YEAR_MIN), YEAR_MAX)
    except (TypeError, ValueError):
        return YEAR_DEFAULT


def cleanBuilding(value):
    return value if value in BUILDINGS else 'None'


# ---------------------------------------------------------------------------
# Shared state between the touch screen and the projection pages
# (/ProjDash, /Proj3D, /Only3D poll it). Kept outside the public assets folder
# and written atomically so a reader never sees a half-written file.
# ---------------------------------------------------------------------------
STATE_DIR = Path(__file__).resolve().parent / 'state'
DASH_STATE_FILE = STATE_DIR / 'dashboard.json'
MAP_STATE_FILE = STATE_DIR / 'map.json'
DEFAULT_DASH_STATE = {'BldName': 'None', 'yearValue': YEAR_DEFAULT, 'resolutionValue': 'ri',
                      'contextValue': 'aib', 'timeFigCategory': 'am'}
DEFAULT_MAP_STATE = {'yearValue': YEAR_DEFAULT, 'mapCat': 'aib',
                     'Resolution_': 'All of The Island', 'menu_3d': 'No3D'}


def writeState(path, data):
    STATE_DIR.mkdir(exist_ok=True)
    tmp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)


def readState(path, default):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return dict(default)
    return {key: data.get(key, value) for key, value in default.items()}


# ---------------------------------------------------------------------------
# Dashboard figures for a scope (island / WIRE / Northtown & Southtown / building)
# ---------------------------------------------------------------------------
def resolveScope(BldName, resolutionValue):
    """Returns (scope, header label). A building is only used in 'ind' mode;
    'ind' without a clicked building behaves like 'wireb'."""
    if resolutionValue == 'ri':
        return 'ri', 'All of The Island'
    if resolutionValue == 'NotWire':
        return 'NotWire', 'Northtown & Southtown'
    if resolutionValue == 'ind' and BldName != 'None':
        return 'building', BldName
    return 'wire', 'Wire'


def scopeMask(df, scope, BldName):
    if scope == 'ri':
        return pd.Series(True, index=df.index)
    if scope == 'NotWire':
        return df['Group'] != 'WIRE'
    if scope == 'wire':
        return df['Group'] == 'WIRE'
    return df['Building Name'] == BldName


def timeFigure(scope, BldName, resolutionValue, timeFigCategory, yearValue):
    if timeFigCategory == 'am':
        if scope == 'ri':
            return affordabilityTimeSeriesAgregattedGraph(
                aw=AllAffordable[AllAffordable['year'] <= yearValue], mC=marketColor, aC=affordColor, title_='All of the Island')
        if scope == 'NotWire':
            return affordabilityTimeSeriesAgregattedGraph(
                aw=NotWireAffordable[NotWireAffordable['year'] <= yearValue], mC=marketColor, aC=affordColor, title_='North Town and South Town')
        if scope == 'wire' and resolutionValue == 'wire':
            return affordabilityTimeSeriesAgregattedGraph(
                aw=WireAffordable[WireAffordable['year'] <= yearValue], mC=marketColor, aC=affordColor, title_='Wire')
        if scope == 'wire':
            return createAffordableInduvidualBldgs('Wire', 1500, 0.9, yearValue)
        r = allAffordableByBldg[(allAffordableByBldg['Building Name'] == BldName)
                                & (allAffordableByBldg['year'] <= yearValue)].reset_index(drop=True)
        return affordabilityTimeSeriesAgregattedGraph(aw=r, mC=marketColor, aC=affordColor, title_=BldName)

    scopeName = {'ri': 'all of the Island', 'NotWire': 'Northtown Southtown Buildings',
                 'wire': 'Wire Buildings'}.get(scope, BldName)
    if timeFigCategory == 'leave':
        r = allByYear[(allByYear['year'] <= yearValue) & scopeMask(allByYear, scope, BldName)]
        return sim_plot.reasulToLeaveByTime(r, f'Reason for leaving for {scopeName}')
    r = allByYearStay[(allByYearStay['year'] <= yearValue) & scopeMask(allByYearStay, scope, BldName)]
    if timeFigCategory == 'life':
        return sim_plot.averageAgeByTime(r, f'Average Age and Life Expectancy for {scopeName}')
    if timeFigCategory == 'ie':
        return sim_plot.incomeBurdenTime(r, f'Income and burden for {scopeName}')
    if timeFigCategory == 'ageg':
        return sim_plot.ageGroupTimeGraph(r, f'Age Groups for {scopeName}')
    return sim_plot.incomeGroupTimeGraph(r, f'Income Groups for {scopeName}')


def contextualFigure(scope, data, contextValue, yearValue):
    label = {'ri': 'RI', 'NotWire': 'Northtown Southtown', 'wire': 'Wire'}.get(scope, 'Building')
    if contextValue == 'aib':
        return sim_plot.bubbleAgeIncomeClass(data, yearValue, label)
    if contextValue == 'income':
        return sim_plot.incomeByGroupFigure(data, yearValue, label)
    if contextValue == 'incomeCensus':
        return sim_plot.incomeByGroupFigureCensus(data, yearValue, label)
    if contextValue == 'age':
        return sim_plot.ageByGroupFigure(data, yearValue, label)
    if contextValue == 'cycle':
        return sim_plot.AgentCycle(data, yearValue, label)
    title_ = f'Affordability and Income Agent Scale {yearValue} {label}'
    if scope == 'building':
        return sim_plot.treeMapBuilding(data, title_)
    return sim_plot.treeMapIsland(data, title_)


def TimeSunBurstContextFigure(BldName, yearValue, resolutionValue, contextValue, timeFigCategory):
    """Builds header, time series, sunburst, contextual figure and summary text
    for the current selection, and publishes it for the projection pages."""
    yearValue = cleanYear(yearValue)
    resolutionValue = cleanChoice(resolutionValue, RESOLUTIONS, 'ri')
    contextValue = cleanChoice(contextValue, CONTEXTS, 'aib')
    timeFigCategory = cleanChoice(timeFigCategory, TIME_CATEGORIES, 'am')
    BldName = cleanBuilding(BldName)

    scope, scopeLabel = resolveScope(BldName, resolutionValue)
    currentData_ = resultsAll1.getAffordableMarketPerYear3(yearValue)
    scopeData = currentData_[scopeMask(currentData_, scope, BldName)].copy()

    header = f'{scopeLabel}: {yearValue}'
    fig = timeFigure(scope, BldName, resolutionValue, timeFigCategory, yearValue)
    sunBurstFig = sim_plot.sunburstGroupsAffordMarketYearColor3(scopeData, yearValue)
    figContextual = contextualFigure(scope, scopeData, contextValue, yearValue)
    executiveText = getCurrentScope(scopeData)

    writeState(DASH_STATE_FILE, {
        'BldName': BldName if scope == 'building' else 'None', 'yearValue': yearValue,
        'resolutionValue': resolutionValue, 'contextValue': contextValue, 'timeFigCategory': timeFigCategory})
    return [header, fig, sunBurstFig, figContextual, executiveText]


def scene3DUrl(menu_3d, zoomto):
    return getIframeURLfor3D(zoomto=zoomto) if menu_3d == 'Yes3D' else SCENE_3D_URL


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@app.callback(
    [Output('graph_ri', 'children'), Output('time-graph', 'figure'),
     Output('sunBurst-graph', 'figure'), Output('contextual-graph', 'figure'), Output('executive_sum_text', 'children')],
    [Input('map-graph', 'clickData'), Input('year-slider', 'value'), Input('scale-observation', 'value'),
     Input('contextual-menu', 'value'), Input('time-menu', 'value')])
def update_graph_ri(clickData, yearValue, resolutionValue, contextValue, timeFigCategory):
    try:
        BldName = clickData['points'][0]['customdata'][0]
    except (TypeError, KeyError, IndexError):
        BldName = 'None'
    return TimeSunBurstContextFigure(BldName, yearValue, resolutionValue, contextValue, timeFigCategory)


@app.callback(
    [Output('map-graph', 'figure'), Output('ifame-cell', 'src')],
    [Input('year-slider', 'value'), Input('mapcolor-menu', 'value'), Input('graph_ri', 'children'), Input('menu3D', 'value')])
def update_map2(yearValue, cat, titleText, menu_3d):
    yearValue = cleanYear(yearValue)
    cat = cleanChoice(cat, MAP_CATEGORIES, 'aib')
    menu_3d = cleanChoice(menu_3d, MENU_3D, 'No3D')
    zoomto = cleanChoice(str(titleText).split(':')[0], ZOOM_TARGETS, 'All of The Island')

    r = resultsAll1.getAffordableMarketPerYear3(yearValue)
    mapFigure = updateMapYear1(yearValue, rib.copy(), r, cat, zoomto=zoomto)
    writeState(MAP_STATE_FILE, {'yearValue': yearValue, 'mapCat': cat,
                                'Resolution_': zoomto, 'menu_3d': menu_3d})
    return [mapFigure, scene3DUrl(menu_3d, zoomto)]


# The projection pages poll the shared state and only re-render when it changed.
@app.callback(
    [Output('bldYearProj', 'children'), Output('time-graphProjDash', 'figure'), Output('sunBurst-graphProjDash', 'figure'),
     Output('contextual-graphProDash', 'figure'), Output('executiveSumTextProj', 'children'),
     Output('yearSliderProj', 'value'), Output('projDash-state', 'data')],
    Input('interval-component_DashProj', 'n_intervals'), State('projDash-state', 'data'))
def updateProjDash(n, lastState):
    state = readState(DASH_STATE_FILE, DEFAULT_DASH_STATE)
    if state == lastState:
        raise PreventUpdate
    header, timeFig, sunBurst, figContextual, executiveText = TimeSunBurstContextFigure(
        state['BldName'], state['yearValue'], state['resolutionValue'], state['contextValue'], state['timeFigCategory'])
    return [header, timeFig, sunBurst, figContextual, executiveText, cleanYear(state['yearValue']), state]


@app.callback([Output('map-graphProj3D', 'figure'), Output('ifame-cellProj3D', 'src'), Output('proj3D-state', 'data')],
              Input('interval-component_Dash3D', 'n_intervals'), State('proj3D-state', 'data'))
def updateProj3D(n, lastState):
    state = readState(MAP_STATE_FILE, DEFAULT_MAP_STATE)
    if state == lastState:
        raise PreventUpdate
    yearValue = cleanYear(state['yearValue'])
    zoomto = cleanChoice(state['Resolution_'], ZOOM_TARGETS, 'All of The Island')
    r = resultsAll1.getAffordableMarketPerYear3(yearValue)
    mapFigure = updateMapYear1(yearValue, rib.copy(), r,
                               cleanChoice(state['mapCat'], MAP_CATEGORIES, 'aib'), zoomto=zoomto)
    return [mapFigure, scene3DUrl(state['menu_3d'], zoomto), state]


@app.callback([Output('ifame-cellOnly3D', 'src'), Output('only3D-state', 'data')],
              Input('interval_Only3D', 'n_intervals'), State('only3D-state', 'data'))
def updateOnly3D_1(n, lastState):
    state = readState(MAP_STATE_FILE, DEFAULT_MAP_STATE)
    if state == lastState:
        raise PreventUpdate
    zoomto = cleanChoice(state['Resolution_'], ZOOM_TARGETS, 'All of The Island')
    return [scene3DUrl(state['menu_3d'], zoomto), state]


@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    pages = {'/ProjDash': projDash, '/Proj3D': proj3D, '/Only3D': Only3D}
    return pages.get(pathname, touchScreen)


@server.after_request
def setSecurityHeaders(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return response


if __name__ == '__main__':
    app.run(debug=False)
