import plotly.graph_objs as go
import pandas as pd
import math
import numpy as np
import copy
import json
from numerize import numerize
from azure.storage.blob import BlobServiceClient
#import cairo
import re
from PIL import Image, ImageDraw, ImageFont
from matplotlib import font_manager
import random
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from .config import storage_account_key, storage_account_name, connection_string, container_name
from datetime import datetime, timedelta
def get_text_dimension(text, font_family, font_size):
    # create a temporary image to draw on
    img = Image.new('RGB', (0, 0), color='white')
    draw = ImageDraw.Draw(img)
    font = font_manager.FontProperties(family=font_family, weight='bold')
    file = font_manager.findfont(font)
    # load the font by font name
    font = ImageFont.truetype(file, font_size)
    # get the text dimensions
    text_width, text_height = draw.textsize(text, font=font)
    return text_width, text_height
    
def unit_of_measurement(value):
    a = numerize.numerize(value)
    unit = ''.join([i for i in a if not i.isdigit()])
    unit = unit.replace('.','')
    return unit
def truncate(data, uom, dc = 0):
    B = 1000000000
    M = 1000000
    K = 1000 
    data = sum(data)
    if uom == 'B':
        value = data/B
    if uom == 'M':
        value = data/M
    if uom == 'K':
        value = data/K
    if dc:
        answer = str(round(value, dc))
        summary_value = str(answer) + uom
        return summary_value
    else:
        list_value = str(value).split('.')
        if float(list_value[-1]) > 50:
            value = int(list_value[0]) + 1
        else:
            value  = int(list_value[0])
        summary_value = str(value) + uom
        return summary_value

def create_plotly_chart(json_data):
    filename = json_data['Project']
    filename =  filename + ".xlsx"
    storage_account_key = storage_account_key
    storage_account_name = storage_account_name
    connection_string = connection_string
    container_name = container_name
    sas = generate_blob_sas(
          account_name = storage_account_name,
          container_name = container_name,
          blob_name = filename,
          account_key = storage_account_key,
          permission = BlobSasPermissions(read=True),
          expiry = datetime.utcnow() + timedelta(hours = 1)
        )
    filename = filename.replace(' ', '%20')
    blob_url = f'https://{storage_account_name}.blob.core.windows.net/{container_name}/{filename}?{sas}'
    filename = filename.replace('%20', ' ')
    df = pd.read_excel(blob_url, skiprows=[0])
    cols = list(df.columns)[3:]
    data = []
    for col in cols:
        if 'Unnamed' in col:
            break
        else:
            data.append(col)
    df = df[data]
    index_break = 0
    for ind in df.index:
        if df['Series Label'][ind] == "RMS":
            index_break = ind
            break
    data = df.iloc[0:int(index_break), :]
    categories = json_data['Data']['CategoryAxis']['categories']
    series = json_data['Data']['CategoryAxis']['series']
    acquisition = json_data['Data']['Acquisition']['Labels']
    rollup_label = json_data['Data']['rollUp']['label']
    rollup_threshold = json_data['Data']['rollUp']['threshold']
    category_threshold = json_data['Data']['rollUp']['category threshold']
    categoryaxisorientation = json_data['Data']['CategoryAxisOrientation']['Label']
    result_data = []

    dataseries = []
    for i in range(len(data)):
        row = data.iloc[i]
        values = [row[j] for j in range(1, len(row))]  # get values for all columns except the first
        dataseries.append({
            'Name': row[0],
            'Values': values
        })
    
    totals = []
    for i in dataseries[0]["Values"]:
        totals.append (0.0)
    for dd in dataseries:
        for i in range(len(totals)):
            totals[i] += dd["Values"][i]
    columns = data.columns.tolist()[1:]

    rollupIndex = None
    for i in range(len(columns)):
        if columns[i] == rollup_label:
            rollupIndex = i
            break
    try:
        exclusion_list = json_data['Data']['rollUp']['updateCompanies']
    except:
        json_data['Data']['rollUp']['updateCompanies'] = []
    def RollupSeries (bucketLabel : str, threshold:float, seriesToInclude:list):
        if threshold <= 0:
            return dataseries
        rollupBucket = None
        for dd in dataseries:
            if dd["Name"] == bucketLabel:
                rollupBucket = dd
        if rollupBucket is None:
            emptyValues = []
            for i in range(len(totals)):
                emptyValues.append (0.0)
            rollupBucket = {"Name" : bucketLabel, "Values" : emptyValues}       

        newSeries = []
        for dd in dataseries:
            if dd["Name"] != rollupBucket["Name"]:
                shouldRollup = (dd["Name"] in seriesToInclude) if (seriesToInclude != None) else True
                if shouldRollup:    
                    if dd["Name"] in exclusion_list:
                        newSeries.append (dd)
                        continue
                    for i in range(len(totals)):
                        xx = dd["Values"][i]/totals[i]
                        
                        if xx < (threshold):
                            rollupBucket["Values"][i] += dd["Values"][i]
                            dd["Values"][i] = 0

                    newSeries.append (dd)

        newSeries.append (rollupBucket)
        return newSeries
    
    categories_toexclude = {}
    def RollupCategories (bucketLabel : str, threshold:float, categoriesToInclude:list):
        if threshold <= 0:
            return

        lastTotalsIndex = len(columns)-1
        if rollupIndex == None:
            columns.append (bucketLabel)
            totals.append (0.0)
            for dd in dataseries:
                dd["Values"].append (0.0)
            lastTotalsIndex += 1
        elif rollupIndex != len(columns)-1:
            for dd in dataseries:
                tempV =  dd["Values"][lastTotalsIndex]
                dd["Values"][lastTotalsIndex] = dd["Values"][rollupIndex]           
                dd["Values"][rollupIndex] = tempV           

        allTotals = sum(totals)

        for i in reversed (range(lastTotalsIndex)):   # omit the last category, which is our rollup bucket
            shouldRollup = (totals[i]/allTotals <= threshold)
            if shouldRollup and categoriesToInclude != None:
                shouldRollup = columns[i] in categoriesToInclude
            if categoriesToInclude and columns[i] in categoriesToInclude and (totals[i]/allTotals > threshold):
                xxxx =totals[i]/allTotals
            
            if shouldRollup:
                totals[lastTotalsIndex] += totals[i]
                categories_toexclude[columns[i]]  = rollup_label
                totals.pop (i)
                columns.pop (i)
                lastTotalsIndex = lastTotalsIndex-1
                for dd in dataseries:
                    values = dd["Values"]
                    v = values.pop (i)
                    values[len(values)-1] += v
                    dd["Values"]= values

        if (totals[lastTotalsIndex] == 0):
            categories.pop ()
            totals.pop ()
            for dd in dataseries:
                dd["Values"].pop ()

    if category_threshold != 0 and category_threshold != '':
        RollupCategories(rollup_label, category_threshold/100, None)
    
    if rollup_threshold != '' and rollup_threshold != 0:
        newSeries = RollupSeries(rollup_label,rollup_threshold/100,None)
    else:
        newSeries = copy.deepcopy(dataseries)

    # Convert the JSON data to a dataframe
    series_list = []
    for item in newSeries:
        series_dict = {'Series Label': item['Name']}
        for i, val in enumerate(item['Values']):
            series_dict[columns[i]] = val
        series_list.append(series_dict)
    data = pd.DataFrame(series_list)

    if categories == "ReverseOrder":
        data = data[data.columns[::-1]]
        first_column = data.pop('Series Label')
        data.insert(0, 'Series Label', first_column)
    else:
        pass
    if series == "ByFirstCategory":
        data = data.sort_values(list(data.columns)[1], ascending = False)
    if series == "ByFirstCategory" or series == "ByEachCategory":
        for col in data.columns:
            dt = {}
            if col != 'Series Label':
                if  series == "ByEachCategory" or series == "":
                    df = data.sort_values(col, ascending = False)
                    df.reset_index(drop=True,inplace=True)
                    # initialize max_value and max_label
                    max_value = 0
                    max_label = ''
                    if rollup_threshold == '' or rollup_threshold == 0:
                        # loop through the labels and compare their Chocolate values
                        if len(acquisition) != 0:
                            for label in acquisition:
                                try:
                                    choc_value = df.loc[df['Series Label'] == label, col].values[0]
                                except:
                                    continue
                                if choc_value > max_value:
                                    max_value = choc_value
                                    max_label = label
                            df2 = df.loc[df['Series Label'].isin(acquisition)]
                            df2 = df2.sort_values(col, ascending = False)
                            df2.reset_index(drop=True,inplace=True)
                            df3 = df.loc[~df['Series Label'].isin(acquisition)]
                            df3.reset_index(drop=True,inplace=True)
                            index = df.index[df['Series Label'] == max_label][0]
                            df = pd.concat([df3.iloc[:index], df2, df3.iloc[index:]])
                else:
                    df = data
                    if rollup_threshold == '' or rollup_threshold == 0:
                        if len(acquisition) != 0:
                            new_list = copy.deepcopy(acquisition)
                            # initialize max_value and max_label
                            max_value = 0
                            max_label = ''
                            # loop through the labels and compare their Chocolate values
                            for label in new_list:
                                choc_value = df.loc[df['Series Label'] == label, col].values[0]
                                if choc_value > max_value:
                                    max_value = choc_value
                                    max_label = label
                            new_list.remove(max_label)
                            df2 = df.loc[df['Series Label'].isin(new_list)]
                            df2.reset_index(drop=True,inplace=True)
                            df3 = df.loc[~df['Series Label'].isin(new_list)]
                            df3.reset_index(drop=True,inplace=True)
                            index = df3.index[df3['Series Label'] == max_label][0]
                            df = pd.concat([df3.iloc[:index+1], df2, df3.iloc[index+1:]])
                options = ['Other', 'other']
                df1 = df.loc[df['Series Label'].isin(options)]
                df = df.loc[~df['Series Label'].isin(options)]
                df = df.append(df1, ignore_index = True)
                dt[col] = dict(zip(df['Series Label'], df[col]))
                result_data.append(dt)
    elif series == "DoNotReOrder":
        for col in data.columns:
            dt = {}
            if col != 'Series Label':
                if series == "ByEachCategory" or series == "":
                    df = data.sort_values(col, ascending = False)
                else:
                    df = data
                    if rollup_threshold == '' or rollup_threshold == 0:
                        if len(acquisition) != 0:
                            new_list = copy.deepcopy(acquisition)
                            # initialize max_value and max_label
                            max_value = 0
                            max_label = ''
                            # loop through the labels and compare their Chocolate values
                            for label in new_list:
                                choc_value = df.loc[df['Series Label'] == label, col].values[0]
                                if choc_value > max_value:
                                    max_value = choc_value
                                    max_label = label
                            new_list.remove(max_label)
                            df2 = df.loc[df['Series Label'].isin(new_list)]
                            df2.reset_index(drop=True,inplace=True)
                            df3 = df.loc[~df['Series Label'].isin(new_list)]
                            df3.reset_index(drop=True,inplace=True)
                            index = df3.index[df3['Series Label'] == max_label][0]
                            df = pd.concat([df3.iloc[:index+1], df2, df3.iloc[index+1:]])
                dt[col] = dict(zip(df['Series Label'], df[col]))
                result_data.append(dt)
    else:
        for col in data.columns:
            dt = {}
            if col != 'Series Label':
                df = data.loc[::-1]
                if rollup_threshold == '' or rollup_threshold == 0:
                    if len(acquisition) != 0:
                        new_list = copy.deepcopy(acquisition)
                        # initialize max_value and max_label
                        max_value = 0
                        max_label = ''
                        # loop through the labels and compare their Chocolate values
                        for label in new_list:
                            choc_value = df.loc[df['Series Label'] == label, col].values[0]
                            if choc_value > max_value:
                                max_value = choc_value
                                max_label = label
                        new_list.remove(max_label)
                        df2 = df.loc[df['Series Label'].isin(new_list)]
                        df2.reset_index(drop=True,inplace=True)
                        df3 = df.loc[~df['Series Label'].isin(new_list)]
                        df3.reset_index(drop=True,inplace=True)
                        index = df3.index[df3['Series Label'] == max_label][0]
                        df = pd.concat([df3.iloc[:index], df2, df3.iloc[index:]])
                dt[col] = dict(zip(df['Series Label'], df[col]))
                result_data.append(dt)
    json_data['Data']['Acquisition'] = {"Labels": data["Series Label"].values.tolist()}

    input_data = {}
    for i in result_data:
        if 'Series Label' not in input_data:
            input_data['Series Label'] = list(list(i.values())[0].keys())
        input_data[list(i.keys())[0]] = list(list(i.values())[0].values())
        
    data = pd.DataFrame.from_dict(input_data)
    series_sum = dict(data[list(data.columns)[1:]].sum(axis = 1))
    categories_sum = dict(data[list(data.columns)[1:]].sum(axis = 0))
    sum_axis = []
    summary_df = data.copy(deep = True)
    summary_df.drop('Series Label', axis = 1, inplace = True)
    summary_d = dict(summary_df.max())
    summary_max_value = max(list(summary_d.values()))
    uom = unit_of_measurement(int(summary_max_value))

    if category_threshold != '' and category_threshold != 0:
        # categories_toexclude = {}
        # total_value = sum(categories_sum.values())
        # for ke, val in categories_sum.items():
        #     if (val/total_value)*100 < category_threshold:
        #         categories_toexclude[ke] = rollup_label
        # print(categories_toexclude)
        if len(categories_toexclude) > 0:
            column_data_modification = []
            for i in json_data['input_data']:   
                for ke in i.copy():
                    if ke in categories_toexclude.keys():
                        column_data_modification.append(i[ke])
                        del i[ke]
                    else:
                        pass
            #dict_json['input_data']
            column_data = [sum(x) for x in zip(*column_data_modification)]
            json_data['input_data'][0][json_data['Data']['rollUp']['label']] = column_data
            #dict_json['input_data']
            category_axis = json_data['Data']['CategoryAxis']['categoryLabel']
            new_category_axis = []
            for axis in category_axis.copy():
                if axis['name'] not in categories_toexclude.keys():
                    new_category_axis.append(axis)
            new_category_axis.append({'name': '{0}'.format(json_data['Data']['rollUp']['label']),
              'parentName': 'CategoryAxis',
              'DisplayText': '',
              'offset': {'x': '', 'y': ''},
              'labelDefaults': [{'rotation': 0,
                'fontColor': '',
                'color': '',
                'fontFamily': '',
                'fontSize': '',
                'bold': False}],
              'fontFamily': '',
              'fontSize': '',
              'fontColor': '',
              'rotation': 0,
              'bold': False})
            json_data['Data']['CategoryAxis']['categoryLabel'] = new_category_axis

            
            sum_dict = {}
            for label in json_data['input_data']:
                for k, v in label.items():
                    if k != 'Series Label':
                        sum_dict[k] = sum(v)
            total = {}
            for cat, val in sum_dict.items():
                total[cat] = truncate([val], uom)
            summaryAxisLabel = []

            for ke, val in total.items():
                item  = {
                         "name": "$"+ str(val),
                         "DisplayText": "",
                         "decimalPlaceValue": "",
                         "offset": 
                             {
                                 "x": "",
                                 "y": ""
                             }
                         ,
                         "fontFamily": "",
                         "fontSize": "",
                         "fontColor": "",
                         "rotation": 0,
                                "bold": False
                            }
                summaryAxisLabel.append(item)
            json_data['Data']['SummaryAxis']['summayAxisLabel'] = summaryAxisLabel

            for label in json_data['Data']['DataLabels']['dataLabels']:
                for c in label['child'].copy():
                    if c['name'] in categories_toexclude.keys():
                        label['child'].remove(c)
                        new_d = {'name': '{0}'.format(json_data['Data']['rollUp']['label']), 'DisplayText': '', 
                                               'decimalPlaceValue': '', 'offset': {'x': '', 'y': ''}, 'fontFamily': '', 
                         'fontSize': '', 'fontColor': '', 'rotation': 0, 'bold': 'False', 'brush': '', 'stroke': '', 'fill': ''}
                        if new_d not in label['child']:
                            label['child'].append(new_d)
            # data.columns = [rollup_label if x in list(categories_toexclude.keys()) else x for x in data.columns]
            # data = data.groupby(data.columns, axis = 1, sort = False).sum()


    for ke, val in input_data.items():
        if ke != 'Series Label':
            final_val = truncate(val, uom)
            final_val = final_val.replace('B','')
            final_val = final_val.replace('K','')
            final_val = final_val.replace('M','')
            sum_axis.append(int(final_val))
    json_data['Data']['MekkoTotal']['Total'] = 'Total = ${0}'.format(sum(sum_axis)) + uom
    summary_axislabel = json_data['Data']['SummaryAxis']['summayAxisLabel']
    z = 0
    s_axis_label = []
    for summary_items in summary_axislabel:
        summary_items['name'] = '${0}'.format(sum_axis[z]) + uom
        s_axis_label.append(summary_items)
        z += 1
    json_data['Data']['SummaryAxis']['summayAxisLabel'] = s_axis_label
    db_label = []
    for i in json_data['input_data'][0]['Series Label']:
        for record in json_data['Data']['DataLabels']['dataLabels']:
            if i == record['name']:
                db_label.append(record)
    json_data['Data']['DataLabels']['dataLabels'] = db_label
    #Data, Axis, CategoryAxis, categoryLabel
    
    cd_label = []
    categoriesorder_required = list(data.columns)
    categoriesorder_required.remove('Series Label')
    for i in categoriesorder_required:
        for record in json_data['Data']['CategoryAxis']['categoryLabel']:
            if i == record['name']:
                cd_label.append(record)
    json_data['Data']['CategoryAxis']['categoryLabel'] = cd_label

    # if rollup_threshold != '' and rollup_threshold != 0:
    #     rollup_threshold = int(rollup_threshold)
    #     new_df = {}
    #     for index, row in data.iterrows():
    #         row_dict = dict(row)
    #         for  ke, val in row_dict.items():
    #             if ke!= 'Series Label':
    #                 new_df[row_dict['Series Label']].append(val/categories_sum[ke]*100)
    #             else:
    #                 new_df[val] = []
    #     companies_toexclude = []    
    #     for companies, percentages in new_df.items():
    #         if any(y > rollup_threshold for y in percentages):
    #             pass
    #         else:
    #             companies_toexclude.append(companies)

    #     copy_input_data = input_data.copy()
    #     copy_input_data['Series Label'] = [rollup_label if x in companies_toexclude else x for x in copy_input_data['Series Label']]
    #     data = pd.DataFrame.from_dict(copy_input_data)
    #     data = data.groupby('Series Label').sum().reset_index()
    #     input_companies = []
    #     df_dict = data.to_dict()
    #     list_items = []
    #     result_dict = {}
    #     for ke, val in df_dict.items():
    #         result_dict[ke] = list(val.values())
    #     list_items.append(result_dict)
    #     input_data = list_items
    #     json_data['input_data'] = list_items
    #     sum_axis = []
    #     for ke, val in input_data[0].items():
    #         if ke != 'Series Label':
    #             final_val = truncate(val, uom)
    #             final_val = final_val.replace('B','')
    #             final_val = final_val.replace('k','')
    #             final_val = final_val.replace('M','')
    #             sum_axis.append(float(final_val))
    #     json_data['Data']['MekkoTotal']['Total'] = 'Total = ${0}'.format(sum(sum_axis))
    #     summary_axislabel = json_data['Data']['SummaryAxis']['summayAxisLabel']
    #     z = 0
    #     s_axis_label = []
    #     for summary_items in summary_axislabel:
    #         summary_items['name'] = '${0}'.format(sum_axis[z])
    #         s_axis_label.append(summary_items)
    #         z += 1
    #     json_data['Data']['SummaryAxis']['summayAxisLabel'] = s_axis_label
    #     data_labels = json_data['Data']['DataLabels']['dataLabels']
    #     result_data_labels = []
    #     for i in data_labels:
    #         if i['name'] not in companies_toexclude:
    #             result_data_labels.append(i)
    #     roll_up_label_add = result_data_labels[0].copy()
    #     roll_up_label_add['name'] = rollup_label
    #     result_data_labels.append(roll_up_label_add)
    #     json_data['Data']['DataLabels']['dataLabels'] = result_data_labels

    input_data = json_data['input_data'][0]
    rightpanel_data = copy.deepcopy(json_data['Data'])
    series_sum = dict(data[list(data.columns)[1:]].sum(axis = 1))
    categories_sum = dict(data[list(data.columns)[1:]].sum(axis = 0))
    
    #title and subtitle changes from json input
    enable_title = json_data['Data']['title']['visible']
    enable_subtitle = json_data['Data']['subTitle']['visible']
    title_text = json_data['Data']['title']['DisplayText'] if json_data['Data']['title']['DisplayText'] != '' else json_data['Data']['title']['name']
    title_bold = json_data['Data']['title']['bold']
    title_pad = json_data['Data']['title']['pad']
    title_font_family = json_data['Data']['title']['fontFamily']
    title_font_size = json_data['Data']['title']['fontSize']
    title_font_color = json_data['Data']['title']['fontColor']
    subtitle_text = json_data['Data']['subTitle']['DisplayText']
    name  = json_data['Data']['subTitle']['name']

    if subtitle_text == '':
        subtitle_text = name
    subtitle_font_family = json_data['Data']['subTitle']['fontFamily']
    subtitle_bold = json_data['Data']['subTitle']['bold']
    subtitle_font_size = json_data['Data']['subTitle']['fontSize']
    subtitle_font_color = json_data['Data']['subTitle']['fontColor']
    
    #Category Axes
    label_colors = json_data['barcolor']
    category_axis = json_data['Data']['CategoryAxis']
    category_axis_child = json_data['Data']['CategoryAxis']['categoryLabel']
    duplicate_categories = []
    dict_count = 0
    for i in category_axis_child:
        if i['name'] not in duplicate_categories:
            duplicate_categories.append(i['name'])
        else:
            del category_axis_child[dict_count]
        dict_count +=1
    category_axis_child = category_axis_child
    xaxis_visible =  category_axis['visible']
    xaxis_titleLabel = category_axis['titleLabel']
    xaxis_titleGap = category_axis['titleGap']
    xaxis_titleposition = category_axis['titleposition']
    xaxis_titleFont = category_axis['titleFont']
    xaxis_titleSize = category_axis['titleSize']
    xaxis_titleBold = category_axis['titleBold']
    xaxis_titleColor = category_axis['titleColor']
    xaxis_categories =  category_axis['categories']
    if category_axis['barGap'] != '':
        xaxis_bargap = int(category_axis['barGap'])
    else:
        xaxis_bargap = category_axis['barGap']
    xaxis_series = category_axis['series']
   
    x_labelDefaults_rotation = category_axis['labelDefaults']['rotation']
    x_labelDefaults_barcolor = category_axis['labelDefaults']['color']
    x_labelDefaults_color = category_axis['labelDefaults']['fontColor']
    x_labelDefaults_fontFamily = category_axis['labelDefaults']['fontFamily']
    x_labelDefaults_fontSize = category_axis['labelDefaults']['fontSize']
    x_labelDefaults_bold = category_axis['labelDefaults']['bold']
    x_labelDefaults_offset = category_axis['labelDefaults']['offset']
    #Value Axis:
    value_axis = json_data['Data']['ValueAxis'] 
    valueaxis_visible =  value_axis['visible']
    valueaxis_titleLabel = value_axis['titleLabel'] if value_axis['titleLabel'] != '' else value_axis['DisplayText']
    valueaxis_titleGap = value_axis['titleGap']
    valueaxis_titleposition = value_axis['titleposition']
    valueaxis_titleFont = value_axis['titleFont']
    valueaxis_titleFontSize = value_axis['titleFontSize']
    valueaxis_titleBold = value_axis['titleBold']
    valueaxis_titleColor = value_axis['titleColor']
    valueaxis_minorTick = value_axis['minorTick']
    valueaxis_labels = value_axis['labels']
    
    #chart size
    aspectratio = json_data['Data']['chartSize']['aspectratio']
    displayWidth = json_data['Data']['chartSize']['displayWidth']
    ppi = json_data['Data']['chartSize']['ppi']
    displayWidth = int(displayWidth if displayWidth != '' else 720)
    aspectratio = int(aspectratio if aspectratio != '' else 1.44)
    list_data = []
    #Summary Axis
    summary_axis = json_data['Data']['SummaryAxis']  
    summary_axis_child = summary_axis['summayAxisLabel']
    summary_axis_visible =  summary_axis['visible']
    summary_axis_titleLabel = summary_axis['titleLabel']
    summary_axis_titleGap = summary_axis['titleGap']
    summary_axis_titleposition = summary_axis['titleposition']
    summary_axis_titleFont = summary_axis['titleFont']
    summary_axis_titleSize = summary_axis['titleSize']
    summary_axis_titleBold = summary_axis['titleBold']
    summary_axis_titleColor = summary_axis['titleColor']
    summary_axis_decimalplacevalue = summary_axis['decimalPlaceValue']
    
    #Summary Axis Label defaults
    summary_labelDefaults_rotation = summary_axis['labelDefaults']['rotation']
    summary_labelDefaults_color = summary_axis['labelDefaults']['color']
    summary_labelDefaults_fontFamily = summary_axis['labelDefaults']['fontFamily']
    summary_labelDefaults_fontSize = summary_axis['labelDefaults']['fontSize']
    summary_labelDefaults_bold = summary_axis['labelDefaults']['bold']
    summary_labelDefaults_offset = summary_axis['labelDefaults']['offset']
    summary_labelDefaults_decimalPlaceValue = summary_axis['decimalPlaceValue']


    if len(category_axis_child) >= 10:
        if summary_labelDefaults_rotation == 0:
            summary_labelDefaults_rotation = 90
        if x_labelDefaults_rotation == 0:
            x_labelDefaults_rotation = 270


    x_axis = list(data.columns)
    x_axis.remove('Series Label')
    #['ColorBar', 'Line', 'Pattern', 'colorbar']
    #Creating bar graph
    #bar_color = [i for i in category_axis_child if i['name'] == ke][0]['labelDefaults'][0]
    list_of_colors = ['skyblue','lavender', 'orange', 'mediumvioletred', 'rosybrown', 'lightblue','tomato','lightsteelblue',  
         'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'lightcoral','cyan', 'darkblue','lightgreen',
        'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
        'aliceblue', 'aqua', 'aquamarine', 'azure', 'beige', 'bisque', 'blanchedalmond', 'blue', 'blueviolet',
         'darkviolet', 'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'forestgreen', 
        'fuchsia', 'gainsboro',  'gold', 'goldenrod', 'gray', 'green', 'greenyellow', 'honeydew', 'hotpink', 
          'indigo', 'ivory', 'khaki',  'lavenderblush', 'lawngreen', 'lemonchiffon', 'darkslateblue',  'darkturquoise',
          'lightgoldenrodyellow', 'lightgray', 'lightgrey', 'darkslategray', 'darkslategrey','green',
         'lightsalmon', 'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey', 'lightpink',
         'lightyellow', 'lime', 'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid',
         'mediumpurple', 'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'lightcyan',
         'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'oldlace', 'olive', 'olivedrab','indianred',
         'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 
         'peachpuff', 'peru', 'pink', 'plum', 'powderblue', 'purple', 'red','royalblue', 'rebeccapurple', 'saddlebrown','darksalmon',
         'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver',  'slateblue', 'slategray', 'slategrey', 'snow','brown', 
         'springgreen', 'steelblue', 'tan', 'teal', 'thistle',  'turquoise', 'violet', 'wheat', 'yellow', 'yellowgreen',
         '#594b8b', '#c73c39', '#07652f', '#101dd2', '#297f70', '#a24592', '#7f9339', '#d9621a', '#94f82f', '#599d06',
         '#721b3f', '#fa05b0', '#da1f7d', '#9f2137', '#e298a1', '#aad1d0', '#8c2967', '#fa2d61', '#851ea6',
         '#a4578c', '#79b8f0', '#b36d21', '#90038d', '#6a2a88', '#1e8e0e', '#6672c0', '#485869', '#30da83', 
         '#f1b780', '#808313', '#6e8d48', '#13205a', '#5e6a9b', '#bccf2b', '#a5ecfd', '#279a2f', '#8fc4c5', '#09071f', 
         '#2f8404', '#67d6ef', '#6bf237', '#9c9019', '#b4f73a', '#b8bc9c', '#0414f5', '#ff667b', '#5ef62b', '#55c169', 
         '#dccd03', '#2fb896', '#561ec8', '#ad1f6f', '#b0b8c8', '#45cba1', '#23833f', '#ed300a', '#8dd65b', '#6db953',
         '#4c1006', '#bf6ddc', '#5dc27d', '#8fe992', '#3f5571', '#02ad96', '#0f8f10', '#4b6013', '#5cb1ea', '#a14f1b',
         '#7428aa', '#5de38d', '#124a14', '#c2242b', '#9b50e9', '#4bd258', '#9f73e7', '#41bf68', '#0d207e', '#0a9fd5',
         '#6f2a41', '#f1707b', '#d818ec', '#2df3ea', '#209925', '#0c88e6', '#02e505', '#3757d0', '#fe5346', '#ba6bc2', '#283fd0',
         '#5f0154', '#c1b433', '#e7ae91', '#fcdf1d', '#7c6a78', '#b99efc', '#13453e', 
         '#80d79f', '#e7041d', '#d6cdc6', '#2901b3']
    
    result =[]
    c = 0
    category_color = {}
    for i in category_axis_child:
        category_color[i['name']] = i['labelDefaults'][0]['color']
    bar_color = {}   
    javascript = []

    sum_category ={}
    new_result_data = []
    for col in data.columns:
        dt = {}
        if col != 'Series Label':
            dt[col] = dict(zip(data['Series Label'], data[col]))
            new_result_data.append(dt)
    for i in new_result_data:
        for cat, comp in i.items():
            sum_category[cat] = sum(comp.values())

    #sum_category.sort(reverse = True)
    width_ = {}
    bar_offset = []
    offset_value = {}
    bar_annot_width = {}
    for cat, val in sum_category.items():
        value = (val/max(sum_category.values()))
        width_[cat] = value
        bar_annot_width[cat] = (val/sum(sum_category.values()))
    x_ = 0
    x_labels_location = []
    DataLabels = json_data['Data']['DataLabels']
    dataLabels = DataLabels['dataLabels']
    brush_label = {"BackwardDiagonal":"/",
    "Cross":"+",
    "DiagonalCross":"+",
    "ForwardDiagonal":"\\",
    "Horizontal":"-",
    "Vertical":"|"}
    location_ = -1
    x_locations  = []
    if xaxis_bargap != '':
        for val in width_.values():
            location_ += 1
            if location_ == 0:
                x_locations.append(0)
            else:
                x_locations.append(list(width_.values())[location_-1] + x_locations[-1]+ xaxis_bargap)
    
    #category_axis_child
    for i in result_data:
        for cat, comp in i.items():
            bar_base_list = [0]
            x_labels_location.append(x_)
            for ke, val in comp.items():
                datalabel = [i for i in dataLabels if i['name'] == ke]
                if len(datalabel) == 0:
                    continue
                datalabel = datalabel[0]
                child  = [i for i in datalabel['child'] if i['name'] == cat]
                category_values = [i for i in category_axis_child if i['name'] == cat]
                child  = child[0]
                brush = child['brush'] if child['brush'] != '' else datalabel['brush']
                stroke = child['stroke'] if child['stroke'] != '' else datalabel['stroke']
                fill =  child['fill'] if child['fill'] != '' else datalabel['fill']
                if fill == '' and category_values[0]['labelDefaults'][0]['color'] != '':
                    fill =  category_values[0]['labelDefaults'][0]['color']
                marker_pattern_size = 4
                if val == 0:
                    continue
                bar_color = label_colors
                if ke not in bar_color.keys():
                    try:
                        bar_color[ke] = 'grey'
                    except:
                        import random
                        random_number = random.randint(0,16777215)
                        hex_number = str(hex(random_number))
                        bar_color[ke] ='#'+ hex_number[2:]
                # if xaxis_categories != 'ReverseOrder':
                #     if ke == 'Other' or ke == 'Others':
                #             bar_color[ke] = 'grey'
                #     if ke not in bar_color.keys():
                #         try:
                #             bar_color[ke] = list_of_colors[c]
                #         except:
                #             import random
                #             random_number = random.randint(0,16777215)
                #             hex_number = str(hex(random_number))
                #             bar_color[ke] ='#'+ hex_number[2:]
                # else:
                #     bar_color = label_colors
                if brush != '' and brush != "Solid":
                    marker_pattern_shape = brush_label[brush]
                    if stroke != '' and fill != '':
                        marker_pattern_fgcolor = stroke
                        marker_pattern_bgcolor = fill
                        if xaxis_bargap != '':
                            trace = {"type":"bar" , "x":x_locations[x_], "y":[(val/sum(data[cat]))*100],  "base":sum(bar_base_list),"name":ke, "showlegend":False,
                            "hoverinfo":'skip', "offset":x_locations[x_],
                            "width":width_[cat], "marker" :{'color': fill if fill != '' else bar_color[ke], "line":{'width':1 , 'color':'white'},
                            "pattern":{"shape": marker_pattern_shape,"size": marker_pattern_size,"fgcolor": marker_pattern_fgcolor,
                                "bgcolor": marker_pattern_bgcolor }}}
                            bar_base_list.append((val/sum(data[cat])) *100)
                        else:
                            trace = {"type":"bar" , "x":[x_], "y":[val],  "name":ke, "showlegend":False, "hoverinfo":'skip', "offset":0,
                                "width":[width_[cat]] , "marker" :{'color':bar_color[ke], "line":{'width':1 , 'color':'white'},
                                "pattern":{"shape": marker_pattern_shape,
                                "size": marker_pattern_size,"fgcolor": marker_pattern_fgcolor,
                                "bgcolor": marker_pattern_bgcolor }}}
                    elif stroke != '':
                        marker_pattern_fgcolor = stroke
                        if xaxis_bargap != '':
                            trace = {"type":"bar" , "x":x_locations[x_], "y":[(val/sum(data[cat]))*100],  "base":sum(bar_base_list),"name":ke, "showlegend":False,
                            "hoverinfo":'skip', "offset":x_locations[x_],
                            "width":width_[cat], "marker" :{'color': fill if fill != '' else bar_color[ke], "line":{'width':1 , 'color':'white'},
                            "pattern":{"shape": marker_pattern_shape,"size": marker_pattern_size,"fgcolor": marker_pattern_fgcolor,
                                "bgcolor": marker_pattern_bgcolor }}}
                            bar_base_list.append((val/sum(data[cat])) *100)
                        else:
                            trace = {"type":"bar" , "x":[x_], "y":[val],  "name":ke, "showlegend":False, "hoverinfo":'skip', "offset":0,
                                "width":[width_[cat]], "marker" :{'color':bar_color[ke], "line":{'width':1 , 'color':'white'},
                                "pattern":{"shape": marker_pattern_shape,
                                "size": marker_pattern_size, "fgcolor": marker_pattern_fgcolor}}}
                    elif fill != '':
                        marker_pattern_bgcolor = fill
                        if xaxis_bargap != '':
                            trace = {"type":"bar" , "x":x_locations[x_], "y":[(val/sum(data[cat]))*100],  "base":sum(bar_base_list),"name":ke, "showlegend":False,
                            "hoverinfo":'skip', "offset":x_locations[x_],
                            "width":width_[cat], "marker" :{'color': fill if fill != '' else bar_color[ke], "line":{'width':1 , 'color':'white'},
                            "pattern":{"shape": marker_pattern_shape,"size": marker_pattern_size,"fgcolor": marker_pattern_fgcolor,
                                "bgcolor": marker_pattern_bgcolor }}}
                            bar_base_list.append((val/sum(data[cat])) *100)
                        else:
                            trace = {"type":"bar" , "x":[x_], "y":[val],  "name":ke, "showlegend":False, "hoverinfo":'skip', "offset":0,
                            "width":[width_[cat]], "marker" :{'color':bar_color[ke], "line":{'width':1 , 'color':'white'},
                            "pattern":{"shape":marker_pattern_shape,
                            "size": marker_pattern_size,"bgcolor": marker_pattern_bgcolor }}}
                    else:
                        if xaxis_bargap != '':
                            trace = {"type":"bar" , "x":x_locations[x_], "y":[(val/sum(data[cat]))*100],  "base":sum(bar_base_list),"name":ke, "showlegend":False,
                            "hoverinfo":'skip', "offset":x_locations[x_],
                            "width":width_[cat], "marker" :{'color':bar_color[ke], "line":{'width':1 , 'color':'white'},
                            "pattern":{"shape":marker_pattern_shape,
                                "size": marker_pattern_size}}}
                            bar_base_list.append((val/sum(data[cat])) *100)
                        else:
                        
                            trace = {"type":"bar" , "x":[x_], "y":[val],  "name":ke, "showlegend":False, "hoverinfo":'skip', "offset":0,
                                "width":[width_[cat]], "marker" :{'color':bar_color[ke], "line":{'width':1 , 'color':'white'},
                                "pattern":{"shape":marker_pattern_shape,
                                "size": marker_pattern_size}}}
                else:
                    if xaxis_bargap != '':
                        trace = {"type":"bar" , "x":x_locations[x_], "y":[(val/sum(data[cat]))*100],  "base":sum(bar_base_list),"name":ke, "showlegend":False,
                        "hoverinfo":'skip', "offset":x_locations[x_],
                        "width":width_[cat], "marker" :{'color': fill if fill != '' else bar_color[ke], "line":{'width':1 , 'color':'white'}}}
                        bar_base_list.append((val/sum(data[cat])) *100)
                    else:
                        trace = {"type":"bar" , "x":[x_], "y":[val],  "name":ke, "showlegend":False, "hoverinfo":'skip', "offset":0,
                                "width":[width_[cat]], "marker" :{'color': fill if fill != '' else bar_color[ke], "line":{'width':1 , 'color':'white'}}}

                c += 1
                javascript.append(trace)
        if xaxis_bargap != '':
            x_+= 1
        else:
            x_= x_+width_[cat]   
    response = {'data': result}
    if subtitle_text != '':
        subtitle = subtitle_text
    else:
        subtitle = ''
    if subtitle_font_family != '':
        subtitle_font = subtitle_font_family
    else:
        subtitle_font = 'Calibri'
    if subtitle_font_size != '':
        subtitle_fontsize = subtitle_font_size
    else:
        subtitle_fontsize = 14
    if subtitle_font_color != '':
        subtitle_fontcolor = subtitle_font_color
    else:
        subtitle_fontcolor = 'black'

    #enable or disable title 
    if enable_title:
        if title_bold:
            title = '<b>{0}</b>'.format(title_text)
        else:
            title = title_text
    #define layout of the graph
    if xaxis_bargap == '':
        response['layout'] =  {"bargroupgap": 0, "bargap": xaxis_bargap if xaxis_bargap != '' else 0, 
               "barnorm": "percent", "editrevision": True, 
               "dragmode": "zoom", "barmode": "stack",
            "plot_bgcolor": "#ffffff" ,
            "showlegend": False,
            "autosize": False,
           "width": displayWidth,
            "height": displayWidth/aspectratio,
            'modebar': {
          #vertical modebar button layout
          'orientation': 'v',
          #for demonstration purposes
          'bgcolor': 'salmon',
          'color': 'white',
          'activecolor': '#9ED3CD'
        },#move plotting area outside the modebar position 
        'margin': {'r': 85},
        #move the legend inside the plot on the top right
        'legend': {'x': 0, 'y': 1}
       }
    else:
        response['layout'] =  {
        "bargroupgap": 0, "bargap": 0,
               "editrevision": True, 
               "dragmode": "zoom", "barmode": "stack",
            "plot_bgcolor": "#ffffff" ,
            "showlegend": False,
            "autosize": False,
            #720
            #500
           "width": displayWidth,
            "height": displayWidth/aspectratio,
            'modebar': {
          #vertical modebar button layout
          'orientation': 'v',
          #for demonstration purposes
          'bgcolor': 'salmon',
          'color': 'white',
          'activecolor': '#9ED3CD'
        },#move plotting area outside the modebar position 
        'margin': {'r': 85},
        #move the legend inside the plot on the top right
        'legend': {'x': 0, 'y': 1}
       }

    if enable_title:
        response['layout']['title'] = {
                "text": title,
                "x": 0.7,
                "y": 0.97
            }
    if enable_title:    
        #padding for title
        #if title_pad:
           # response['layout']['title']['xanchor'] = 'left'
           # response['layout']['title']['pad'] = {
           #         "b": title_pad,
           #         "l": title_pad,
           #         "r": title_pad
           #     }   
        response['layout']['title']['font'] = {}
        if title_font_family:
            response['layout']['title']['font']['family'] = title_font_family
        else:
            response['layout']['title']['font']['family'] = 'Calibri'
        if title_font_color:
            response['layout']['title']['font']['color'] = title_font_color
        else:
            response['layout']['title']['font']['color'] = 'red'
        if title_font_size:
            response['layout']['title']['font']['size'] = title_font_size
        else:
            response['layout']['title']['font']['size'] = 16
    
    response['layout']['template'] = {}
    response['layout']['template']['layout'] = {}
    response['layout']['template']['layout']['xaxis'] = {}
    response['layout']['template']['layout']['xaxis']['title'] = {}
    response['layout']['template']['layout']['xaxis']['title']['font'] = {}
    #response['layout']['template']['layout']['xaxis']['tickfont'] = {}
    response['layout']['annotations'] = []
    y = -5
    x = 0
    length_of_categories = []
    for i in data.columns:
        length_of_categories.append(len(i))
    if max(length_of_categories) >= 20:
        y = -30
    #x-axis labels annotations
    #{'name': 'Chocolate', 'DisplayText': '', 'offset': [{'x': '', 'y': ''}], 'fontFamily': '', 'fontSize': '', 'fontColor': '', 'rotation': '', 'bold': 'True'}
    count_ = -1
    if category_axis['labelrows'] != '':
        final_label_rows = int(category_axis['labelrows'])
        labelrows = []
        for i in range(len(category_axis_child)):
            labelrows.append(y)
        category_axis_count = 0
        for i in range(final_label_rows):
            if category_axis_count == 0:
                labelrows[category_axis_count] = y
            else:
                labelrows[category_axis_count] =  y- (category_axis_count*2)
            category_axis_count += 1
    if xaxis_visible:
        count = 0
        for each_annotation in category_axis_child:
            if each_annotation['DisplayText'] != '':
                displayText = each_annotation['DisplayText']
            else:
                displayText = each_annotation['name']
            
            if xaxis_categories == 'ReverseOrder':
                displayText = x_axis[count_ + 1]
                
            count_ += 1
            if category_axis['labelrows'] != '':
                y = labelrows[count_]
            if xaxis_bargap == '':
                x = list(width_.values())[count_]/2 + sum(list(width_.values())[:count_]) 
            else:
                x = list(width_.values())[count_]/2 + x_locations[count_] 
            if each_annotation['offset']['x'] != '':
                if x < 0:
                    x = -float(each_annotation['offset']['x'])+x
                else:
                    x = float(each_annotation['offset']['x'])+x
            if each_annotation['offset']['y'] != '':
                if y < 0:
                    y = -float(each_annotation['offset']['y'])+y
                else:
                    y = float(each_annotation['offset']['y'])+y
            
            rotation_angle = 0
            if categoryaxisorientation == "Vertical":
                rotation_angle = 90
            elif categoryaxisorientation == "Alternate Vertical Spacing":
                if count % 2 == 0:
                    y -= 2

            response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                "annotations": "annotations[{}]text".format(count_),
                "Parent":"CategoryLabel",
                "font": {
                "color": each_annotation['fontColor'] if each_annotation['fontColor'] != '' else 'black',
                "family":each_annotation['fontFamily'] if each_annotation['fontFamily'] != '' else 'calibri',
                "size":int(each_annotation['fontSize']) if each_annotation['fontSize'] != '' else 10,
                },
               "showarrow": False,
                "text": '<b>' + displayText + '</b>' if each_annotation['bold'] != False else displayText,
                "x":  x,
                "y": y,
                "textangle":each_annotation['rotation'] if each_annotation['rotation'] != 0 else rotation_angle,
                "visible":True })
            count += 1

    #x-axis label defaults
    if xaxis_visible:
        for annotation in (response['layout']['annotations']):
            category_axis_child_default = [i for i in category_axis_child if i['name'] == annotation['text'].replace('<b>', '').replace('</b>','')]
            category_axis_child_default_rotation = int(category_axis_child_default[0]['rotation']) if category_axis_child_default[0]['rotation'] != 0 else (x_labelDefaults_rotation if x_labelDefaults_rotation != 0 else annotation['textangle'])
            category_axis_child_default_fontColor = category_axis_child_default[0]['fontColor'] if category_axis_child_default[0]['fontColor'] != '' else (x_labelDefaults_color if x_labelDefaults_color != '' else annotation['font']['color'])
            category_axis_child_default_fontSize = int(category_axis_child_default[0]['fontSize']) if category_axis_child_default[0]['fontSize'] != '' else (int(x_labelDefaults_fontSize) if x_labelDefaults_fontSize!= '' else annotation['font']['size'])
            category_axis_child_default_fontFamily = category_axis_child_default[0]['fontFamily'] if category_axis_child_default[0]['fontFamily'] != '' else (x_labelDefaults_fontFamily  if x_labelDefaults_fontFamily != '' else annotation['font']['family'])
            category_axis_child_default_text = '<b>' + annotation['text'] + '</b>' if category_axis_child_default[0]['bold'] else ('<b>' + annotation['text'] + '</b>' if x_labelDefaults_bold != False else annotation['text'])
            y = 0 
            if category_axis_child_default_rotation > 0:
                text_width, text_height = get_text_dimension(category_axis_child_default_text,category_axis_child_default_fontFamily, category_axis_child_default_fontSize)
                y = -text_width//10-2
            annotation.update({"align": "center", "arrowhead": 1,
            list(annotation.items())[2][0]: list(annotation.items())[2][1],
            "font": {
            "color": category_axis_child_default_fontColor,
            "family":category_axis_child_default_fontFamily,
            "size": category_axis_child_default_fontSize,
                },
            "showarrow": False,
            "text": category_axis_child_default_text,
            "x":float(x_labelDefaults_offset['x']) if x_labelDefaults_offset['x'] != '' else annotation['x'],
            "y": float(x_labelDefaults_offset['y']) if x_labelDefaults_offset['y'] != '' else (y if y != 0 else annotation['y']),
            "textangle": category_axis_child_default_rotation,
            "visible":True})

    #background color
    #paper_bgcolor = json_data["paper_bgcolor"]
    #plot_bgcolor = json_data["plot_bgcolor"]
    #if paper_bgcolor != "":
    #    response['layout']['paper_bgcolor'] = {}
    #    response['layout']['paper_bgcolor'] = paper_bgcolor
    #if plot_bgcolor != "":
    #    response['layout']['plot_bgcolor'] = {}
    #    response['layout']['plot_bgcolor'] = plot_bgcolor
    
    #distance between title and graph border 
    #
    if title_pad:
        pad_value = 20*(int(title_pad))
        response['layout']['margin'] = {'t':60+pad_value}
    else:
        response['layout']['margin'] = {'t':60}
    #x_labelDefaults_offset
    if xaxis_visible:
        category_offset = []
        for x, val in x_labelDefaults_offset.items():
            category_offset.append(x_labelDefaults_offset[x])
            
        for i in response['layout']['annotations']:
            if category_offset[0] != '':
                x = float(category_offset[0]) + float(i['x'])
                i.update({'x':x})
            if category_offset[1] != '':
                y = float(category_offset[1]) + float(i['y'])
                i.update({'y':y})
            

    if xaxis_titleposition != '':
        xaxis_titleposition = float(xaxis_titleposition)
        if xaxis_titleposition < 0.5:
            xaxis_titleposition = math.floor(len(x_axis)/2) - xaxis_titleposition
        else:
            xaxis_titleposition = math.floor(len(x_axis)/2) + xaxis_titleposition
    else:
        xaxis_titleposition = math.floor(len(x_axis)/2)

    if xaxis_visible:
        if xaxis_titleLabel != '':
            response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
            "annotations": "annotations[{}]text".format(count_),
            "font": {
            "color":xaxis_titleColor  if xaxis_titleColor else 'black',
                                    "family":xaxis_titleFont if xaxis_titleFont else 'Calibri' ,
                                    "size": int(xaxis_titleSize) if xaxis_titleSize!='' else 12,
                                },
                                "showarrow": False,
                                "text":'<b>' +xaxis_titleLabel+'</b>'  if xaxis_titleBold else xaxis_titleLabel,
                                "x":int(response['layout']['annotations'][-1]['x'])  if xaxis_titleposition != '' else int(xaxis_titleposition),
                               # "xref": 'paper',
                               # "yref": 'paper',
                               # "xanchor": 'right',
                               # "yanchor": 'bottom',
                                "y": int(xaxis_titleGap)*-15 if xaxis_titleGap != '' else -10,
                                "textangle":0,
                                "visible":True
                            })
    
    #roll up
    #save chart
    
    #Value Axis:
    majorStep = value_axis['majorStep']
    labelFormat = value_axis['labels']
    label = labelFormat['labelFormat']
    minlabelFormat = labelFormat['minimumLabelFormat']
    maxlabelFormat = labelFormat['maximumLabelFormat']
    fullspecifiedMajorticks = value_axis['fullspecifiedMajorticks']

    min_value = value_axis['min']
    max_value = value_axis['max']
    if majorStep != '' :
        majorStep = majorStep
    else:   
        majorStep = 10
    #yaxis': {'tickangle': 45, 'tickmode': 'array', 'ticktext': [0, 20, 40, 60, 80], 'tickvals': [0, 20, 40, 60, 80]}
    response['layout']['yaxis'] = {}
    response['layout']['yaxis']['tickmode'] = 'array'
    response['layout']['yaxis']['ticktext'] = list(range(int(min_value) if min_value != '' else 0, int(max_value)+int(majorStep) if max_value != '' else 100+int(majorStep), int(majorStep)))
    response['layout']['yaxis']['tickvals'] = list(range(int(min_value) if min_value != '' else 0, int(max_value)+int(majorStep) if max_value != '' else 100+int(majorStep), int(majorStep)))
    
    
    #fullspecifiedMajorticks
    majorTicks = []
    for i in fullspecifiedMajorticks:
        if i["label"] and i['value'] != '':
            majorTicks.append(int(i['value']))
    if len(majorTicks) != 0: 
        majorTicks.sort()
        response['layout']['yaxis']['ticktext'] = majorTicks
        response['layout']['yaxis']['tickvals'] = majorTicks
    
    min_max_label = response['layout']['yaxis']['ticktext']
    ticktext = []
    if label != '' or minlabelFormat != '' or maxlabelFormat != '':
        for i in range(len(response['layout']['yaxis']['ticktext'])):
            if i == 0 and minlabelFormat != '':
                ticktext.append(str(response['layout']['yaxis']['ticktext'][i]) + minlabelFormat)
            elif i == len(response['layout']['yaxis']['ticktext'])-1 and maxlabelFormat != '':
                ticktext.append(str(response['layout']['yaxis']['ticktext'][i]) + maxlabelFormat)
            else:
                if i == 0:
                    ticktext.append(str(response['layout']['yaxis']['ticktext'][i]))
                elif i == len(response['layout']['yaxis']['ticktext'])-1:
                    ticktext.append(str(response['layout']['yaxis']['ticktext'][i]))
                else:
                    ticktext.append(str(response['layout']['yaxis']['ticktext'][i]) + label)          
        response['layout']['yaxis']['ticktext'] = ticktext
    if valueaxis_titleLabel == '':
        response['layout']['yaxis'].update({'title': ""})

    if valueaxis_visible:
        response['layout']['yaxis']['title'] = {}
        response['layout']['yaxis']['title']['text'] =  '<b>' + valueaxis_titleLabel + '</b>' if valueaxis_titleBold else valueaxis_titleLabel
        response['layout']['yaxis']['title']['standoff'] = int(valueaxis_titleGap) if valueaxis_titleGap != '' else 1
        response['layout']['yaxis']['titlefont'] = {}
        response['layout']['yaxis']['titlefont'].update({'color':valueaxis_titleColor if valueaxis_titleColor != '' else 'black'})
        response['layout']['yaxis']['titlefont'].update({'family':valueaxis_titleFont if valueaxis_titleFont != '' else 'Calibri'})
        response['layout']['yaxis']['titlefont'].update({'size':int(valueaxis_titleFontSize) if valueaxis_titleFontSize != '' else 14})
    

    response['layout']['template']['layout']['xaxis']['visible'] = False

    total = []
    
    summary_axis_child_list = []
    for child in summary_axis_child:
        summary_axis_child_list.append(child['name'])
    
    summary_labelDefaults_offset_x = summary_labelDefaults_offset['x']
    summary_labelDefaults_offset_y = summary_labelDefaults_offset['y']
    
    with_decimal = []
    counter = -1
    #Summary Axis Label defaults
    #summary_axis_decimalplacevalue
    if xaxis_categories == "ReverseOrder":
        summary_axis_child = summary_axis_child[::-1]
    if summary_axis_visible:
        loop = 0
        for i in range(len(summary_axis_child)):
            colname = list(data.columns)[i+1]
            with_decimal.append(sum(data[colname])/1000000000)
            if summary_axis_child[i]['DisplayText'] != '':
                if summary_axis_child[i]['decimalPlaceValue'] != '':
                    var = decimalplace_method(summary_axis_child[i]['DisplayText'], int(summary_axis_child[i]['decimalPlaceValue']))
                else:
                    var = summary_axis_child[i]['DisplayText']
            elif summary_axis_child[i]['decimalPlaceValue'] != '':
                var = truncate(data[colname], uom,  int(summary_axis_child[i]['decimalPlaceValue']))
                var = "$" + var
            elif summary_labelDefaults_decimalPlaceValue != '':
                var = truncate(data[colname], uom, int(summary_labelDefaults_decimalPlaceValue))
                if not '.' in var and int(summary_labelDefaults_decimalPlaceValue):
                    label = []
                    digit = []
                    for v in var:
                        if v.isdigit():
                            digit.append(v)
                        else:
                            label.append(v)
                    combining_digit = "".join(digit)
                    combining_digit += ".0"
                    combining_digit += label[0]
                    var = "$" + combining_digit
                else:
                    var = "$" + var
            else:
                var = summary_axis_child[i]['name']
            
            if summary_axis_child[i]['DisplayText'] != '':
                if summary_labelDefaults_bold:
                    var = '<b>' +str(summary_axis_child[i]['DisplayText'])+'</b>'
            else:
                if summary_labelDefaults_bold:
                    var = '<b>' +str(var)+'</b>'
            counter += 1
            if xaxis_bargap == '':
                x = list(width_.values())[i]/2 + sum(list(width_.values())[:i])
            else:
                x = list(width_.values())[i]/2 + x_locations[counter]

            shift = 0
            if categoryaxisorientation == "Alternate Vertical Spacing":
                if loop % 2 == 0:
                    shift = 2
                    

            if len(data.columns) > 10:
                child = summary_axis_child[i]
                count_ += 1
                response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                "annotations": "annotations[{}]text".format(count_),
                "Parent":"SummaryLabel",
                 "font": {
                    "color": summary_labelDefaults_color if summary_labelDefaults_color != '' else (child['fontColor'] if child['fontColor'] != '' else "#000000"),
                     "family": summary_labelDefaults_fontFamily if summary_labelDefaults_fontFamily != '' else (child['fontFamily'] if child['fontFamily'] != '' else "Calibri"),
                     "size": int(summary_labelDefaults_fontSize) if summary_labelDefaults_fontSize != '' else (int(child['fontSize']) if child['fontSize'] != '' else 14),
                 },
                 "showarrow": False,
                 "text": var,
                 "x": x + float(summary_labelDefaults_offset_x) if summary_labelDefaults_offset_x != '' else (float(child['offset']['x']) if child['offset']['x'] != '' else x),
                 "y": 105 + float(summary_labelDefaults_offset_y) if summary_labelDefaults_offset_y != '' else (float(child['offset']['y']) if child['offset']['y'] !='' else 105) + shift,
                 "textangle": int(summary_labelDefaults_rotation) if summary_labelDefaults_rotation != 0 else (int(child['rotation']) if child['rotation'] !='' else 90),
                     })
            else:
                count_ += 1
                child = summary_axis_child[i]
                decimalplacevalue = child['decimalPlaceValue']
                response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                "annotations": "annotations[{}]text".format(count_),
                "Parent":"SummaryLabel",
                     "font": {
                         "color": summary_labelDefaults_color if summary_labelDefaults_color != '' else (child['fontColor'] if child['fontColor'] != '' else "#000000"),
                         "family": summary_labelDefaults_fontFamily if summary_labelDefaults_fontFamily != '' else (child['fontFamily'] if child['fontFamily'] != '' else "Calibri"),
                         "size": int(summary_labelDefaults_fontSize) if summary_labelDefaults_fontSize != '' else (int(child['fontSize']) if child['fontSize'] != '' else 14),
                     },
                     "showarrow": False,
                     "text": var,
                     "x": x + float(summary_labelDefaults_offset_x) if summary_labelDefaults_offset_x != '' else (float(child['offset']['x']) if child['offset']['x'] != '' else x),
                     "y": 105 + float(summary_labelDefaults_offset_y) if summary_labelDefaults_offset_y != '' else (float(child['offset']['y']) if child['offset']['y'] !='' else 105) + shift,
                     "textangle": int(summary_labelDefaults_rotation) if summary_labelDefaults_rotation != 0 else (int(child['rotation']) if child['rotation'] !='' else 0),
                     })
            loop += 1
    
    mekko = json_data['Data']['MekkoTotal']['Total']
    mekko_fontColor = json_data['Data']['MekkoTotal']['fontColor']
    mekko_color = json_data['Data']['MekkoTotal']['color']
    mekko_fontFamily = json_data['Data']['MekkoTotal']['fontFamily']
    mekko_fontSize = json_data['Data']['MekkoTotal']['fontSize']
    mekko_bold = json_data['Data']['MekkoTotal']['bold']
    try:
        percentage_enable = json_data['Data']['showPercentage']['visible']
    except:
        json_data['Data']['showPercentage'] = {'visible':False}
        percentage_enable = False

    if summary_axis_visible:
        meko_total = sum(with_decimal)
        decimal = str(meko_total).split('.')
        new = list(decimal[-1])
        new.insert(0, '.')
        xvalue = list(width_.values())
        new = ''.join(new)
        if float(new) > 0.5:
            res = math.ceil(meko_total)
        else:
            res = int(decimal[0])
        count_ +=1 
        if mekko != '':
            var =  mekko
        else:
            var = " Total= ${}".format(res)
        response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                   "annotations": "annotations[{}]text".format(count_),
                   "Parent":"SummaryLabel",
                    "font": {
                        "color": mekko_fontColor if mekko_fontColor else "#000000",
                        "family": mekko_fontFamily if mekko_fontFamily else "Calibri",
                        "size": int(mekko_fontSize) if mekko_fontSize else 10
                    },
                    "showarrow": False,
                    "text": '<b>' + json_data['Data']['MekkoTotal']['Total'] + '</b>' if mekko_bold else json_data['Data']['MekkoTotal']['Total'],
                    "x":(xvalue[-1]/2 +  sum(xvalue[:-1])) if xaxis_bargap == '' else xvalue[-1]/2  + x_locations[counter],
                    "y": 115
                })
    if enable_subtitle:
        count_ += 1
        response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                "annotations": "annotations[{}]text".format(count_),
                "font": {
                    "color":subtitle_fontcolor,
                    "family":subtitle_font,
                    "size": int(subtitle_fontsize),
                },
                "showarrow": False,
                "text":'<b>' +subtitle+'</b>'  if subtitle_bold else subtitle,
                 "x": 0.55,
                "y": 1.02,
                "xref":"paper",
                "yref":"paper",
                "textangle": 0,
                "visible": True
            })

    # Determine the number of columns
    num_cols = len(newSeries[0]['Values'])

    # Initialize variables for the sums of each column
    sum_cols = [0] * num_cols

    # Loop through each dictionary in the list
    for item in newSeries:
        # Loop through each value in the 'Values' list
        for i, value in enumerate(item['Values']):
            # Add the value to the appropriate sum variable based on the column index
            sum_cols[i] += value

    new_list = []
    for item in newSeries:
        new_dict = {}
        new_dict['Values'] = {}
        # Loop through each value in the 'Values' list
        for i, value in enumerate(item['Values']):
            # Calculate the percentage of the value based on the sum of its column
            if sum_cols[i] == 0:
                percentage = 0
            else:
                percentage = round((value / sum_cols[i]) * 100,2)
            # Replace the value with its percentage
            item['Values'][i] = percentage
            new_dict['Name'] = item['Name']
            new_dict['Values'][columns[i]] =percentage
        new_list.append(new_dict)

    count = 0
    #bgcolor
    index = 0
    length = [0]
    x = 0.1
    for companies in result_data:
        value = []
        index += 1
        if xaxis_bargap == '':
            x = list(width_.values())[index-1]/2 + sum(list(width_.values())[:index-1])
        else:
            if x != 0.1:
                x += 1.1  
            x = list(width_.values())[index-1]/2  + x_locations[index-1]
        #
        for ke , val in companies.items():
            sum_list = [v for k,v in val.items()]
            sum_comp = sum(sum_list)
            for k, v in val.items():
                #child = [i for i in category_axis_child if i['name'] == ke][0]['labelDefaults'][0]
                datalabel = [i for i in dataLabels if i['name'] == k]
                if len(datalabel) == 0:
                    continue
                datalabel = datalabel[0]
                #child = [i for i in category_axis_child if i['name'] == ke][0]['labelDefaults'][0]
                child  = [i for i in datalabel['child'] if i['name'] == ke]
                child  = child[0]
                #rotation = child['rotation']
                if child['DisplayText'] == '':
                    if percentage_enable:
                        for item in new_list:
                            if item['Name'] == k:
                                for key,va in item['Values'].items():
                                    if key == ke:
                                        child['DisplayText'] = item['Name'] + '-'  + str(va) + '%'

                if not percentage_enable:
                    if  child['DisplayText'].find('%') != -1:
                        child['DisplayText'] = ''           
                if datalabel['DisplayText'] != '':
                   k = datalabel['DisplayText']
                if child['DisplayText'] != '':
                    k = child['DisplayText']
                offset = child['offset'] if (child['offset']['x']  != '') or (child['offset']['y']  != '') else datalabel['offset']
                fontColor = child['fontColor'] if child['fontColor'] != '' else datalabel['fontColor']
                fontFamily = child['fontFamily'] if child['fontFamily'] != '' else datalabel['fontFamily']
                fontSize = child['fontSize'] if child['fontSize'] != '' else datalabel['fontSize'] 
                bold = child['bold'] if child['bold'] != '' else datalabel['bold']
                rotation = child['rotation'] if child['rotation'] != 0 else datalabel['rotation']
                category_values = [i for i in category_axis_child if i['name'] == ke]
                
                #
                fontColor = category_values[0]['labelDefaults'][0]['fontColor'] if category_values[0]['labelDefaults'][0]['fontColor'] != '' else fontColor
                fontFamily = category_values[0]['labelDefaults'][0]['fontFamily'] if category_values[0]['labelDefaults'][0]['fontFamily'] != '' else fontFamily
                fontSize = category_values[0]['labelDefaults'][0]['fontSize'] if category_values[0]['labelDefaults'][0]['fontSize'] != '' else fontSize
                bold = category_values[0]['labelDefaults'][0]['bold'] if category_values[0]['labelDefaults'][0]['bold'] != '' else bold
                user_rotation = category_values[0]['labelDefaults'][0]['rotation'] if category_values[0]['labelDefaults'][0]['rotation'] != 0 else rotation
                if len(val) > 20 and rotation == 0:
                    rotation = 90
                if v == 0:
                    continue
                value.append((v/sum(data[ke].values))*100)
                axis = value[-1]/2
                y_data = sum(value)- axis
                #y_data = sum(value)
                if fontSize == '':
                    fontSize = 12
                    font_size = 9
                    # Calculate the available space for the annotation text within the bar
                    text_width, text_height = get_text_dimension(k,'Arial',fontSize)
                    available_width = bar_annot_width[ke] * (displayWidth-85) - 2 
                    available_height = (v/sum_comp) * ((displayWidth/aspectratio)-60) - 2 

                    if available_width > available_height:
                        rotation = 0
                    else:
                        rotation = 270

                    if rotation == 90 or rotation == 270:
                        available_width -= text_height
                        available_height -= text_width
                    else:
                        available_width -= text_width
                        available_height -= text_height

                    # Reduce the font size and orientation of the text to fit within the bar
                    while available_width < 0 or available_height < 0:
                        if fontSize <= 1:
                            break
                        fontSize -= 1

                        text_width, text_height = get_text_dimension(k,'Arial',fontSize)

                        if rotation == 90 or rotation == 270:
                            available_width = (bar_annot_width[ke] * (displayWidth-85)) - text_height - 2
                            available_height = ((v/sum_comp) * ((displayWidth/aspectratio)-60) )- text_width - 2 
                        else:
                            available_width = (bar_annot_width[ke]  * (displayWidth-85)) - text_width - 2 
                            available_height = ((v/sum_comp) * ((displayWidth/aspectratio)-60)) - text_height - 2 


                    if fontSize <= 1:
                        fontSize = 1
                    
                    
                if len(data.columns) > 10:
                    count_ += 1
                    response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                        "annotations": "annotations[{}]text".format(count_),
                        "font": {
                            "color":fontColor if fontColor != '' else "#000000",
                            "family":fontFamily if fontFamily != '' else 'Calibri',
                            "size":fontSize if fontSize!= '' else font_size 
                        }, "showarrow": False, "text": '<b>' + k +'</b>' if bold else k, 
                        "Parent": "DataLabel",
                        "categoryType": ke,
                        "x": x + float(offset['x']) if offset['x'] != '' else x, "y":y_data + float(offset['y']) if offset['y'] != '' else y_data, 
                        "textangle":user_rotation if user_rotation != 0 else rotation
                            })
                        
                else:
                    count_ += 1
                    response['layout']['annotations'].append({"align": "center", "arrowhead": 1,
                      "annotations": "annotations[{}]text".format(count_),
                        "font": {
                            "color":fontColor if fontColor != '' else "#000000",
                            "family":fontFamily if fontFamily != '' else 'Calibri',
                            "size":fontSize if fontSize!= '' else font_size 
                        }, "showarrow": False, "text": '<b>' + k +'</b>' if bold else k, 
                        "Parent": "DataLabel",
                        "categoryType": ke,
                        "x": x + float(offset['x']) if offset['x'] != '' else x, "y":y_data + float(offset['y']) if offset['y'] != '' else y_data, 
                        "textangle":user_rotation if user_rotation != 0 else rotation
                       })
        
                         
        count +=1


    response['layout']['yaxis']['tickfont_size']= 5
    border_flag = []
    for r in category_axis_child:
        if r['rotation'] != '':
            border_flag.append(rotation)
            for j in r['labelDefaults']:
                if j['rotation'] != '':
                    border_flag.append(rotation)
                else:
                    pass
    # if xaxis_bargap != '':
#     response['layout']['shapes'] = [{'line': {'color': 'black', 'width': 1},
#                             'type': 'rect',
#                             'x0': 0,#left border
#                             #'x1': 1,#right border
#                             'xref': 'paper',
#                             #'y0': 0.065,#bottom
#                             #'y1': 0.86,#top border
#                             'yref': 'paper'}]

    if len(border_flag) == 0 and len(x_axis) >= 10:
        response['layout']['shapes'] = [{'line': {'color': 'black', 'width': 1},
           'type': 'rect',
           'x0': 0.01,#left border
           'x1': 0.95,#right border
           'xref': 'paper',
           'y0': 0.060,#bottom
           'y1': 0.86,#top border
                        'yref': 'paper'}]
    else:
        if len(border_flag) == 0:
            response['layout']['shapes'] = [{'line': {'color': 'black', 'width': 1},
                            'type': 'rect',
                            'x0': 0,#left border
                            'x1': 1,#right border
                            'xref': 'paper',
                            'y0': 0.065,#bottom
                            'y1': 0.86,#top border
                            'yref': 'paper'}]
    #showlegend=False disable the left hand side bars with colors showing
    if xaxis_bargap == '':
        response['layout']['xaxis'] = {}
        response['layout']['xaxis']['title'] = ""    
        response['layout']['xaxis']["range"] = [0, sum(width_.values())]


    response['layout']['yaxis']["ticks"] = "outside"
    response['layout']['yaxis']["tickfont"] = {'size': 8}
    

    response['layout']['yaxis']['gridcolor'] = 'white'
    #'gridcolor': 'white'
    config ={"editable":"True","staticPlot":False, "edits":{"annotationPosition":"True", "annotationText":"True", "axisTitleText":"True", "legendPosition":"True", "legendText":"True"}}
    
    category_axis = []
    response['layout']['yaxis'].update({'ticksuffix': ''})
    for i in json_data['Data']["CategoryAxis"]["categoryLabel"]:
        if i['DisplayText'] != '':
            i['name'] = i['DisplayText']
            i['DisplayText'] = ''
        category_axis.append(i)
    
    rightpanel_data["CategoryAxis"]["categoryLabel"] = category_axis
    if rollup_threshold != '' and rollup_threshold != 0:
        rightpanel_data['rollUp']['companies'] = [i['Name'] for i in newSeries if i['Name'] != '' and i['Name'] not in json_data['Data']['rollUp']['updateCompanies']]
        rightpanel_data['rollUp']['updateCompanies']  = json_data['Data']['rollUp']['updateCompanies']
    response = {"data":javascript, "layout":response['layout'], "Data":rightpanel_data,
    "input_data": json_data["input_data"],
     "chart": json_data["chart"],
    "type": json_data["type"],
    "Project": json_data["Project"],
    "saveChart": json_data["saveChart"],
    "Name": "",
    "Year": "",
    "Market": "",
    "Region": "",
    "Currency": "",
    "barcolor":bar_color}
    #saveChart option
    if json_data['saveChart']:
        storage_account_key = storage_account_key
        storage_account_name = storage_account_name
        connection_string = connection_string
        container_name = container_name
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        filename = json_data['Project'] + ".json"
        blob_client = blob_service_client.get_blob_client(container = container_name, blob = filename)
        if blob_client.exists():
            blob_client.delete_blob(delete_snapshots="include")
            pass
        blob_client.upload_blob(json.dumps(response))
    return response

def decimalplace_method(f, n):
    return math.floor(f * 10 ** n) / 10 ** n