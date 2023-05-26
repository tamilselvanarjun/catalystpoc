import pandas as pd
import json
import math
from numerize import numerize
#json converter
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
    

def mekkojson(data, projectName):
    result = []
    d = {}
    for col in data.columns:
        d[col] = data[col].tolist()
    result.append(d)
    category_label = []
    for col in data.columns:
        if col != 'Series Label':
            d = {
            "name": col,
               "parentName": "CategoryAxis",
               "DisplayText": "",
               "offset": 
                   {
                       "x": "",
                       "y": ""
                   }
               ,
               "labelDefaults": [
                   {
                       "rotation": 0,
                       "fontColor": "",
                       "color": "",
                       "fontFamily": "",
                       "fontSize": "",
                       "bold": False
                   }
               ],
               "fontFamily": "",
               "fontSize": "",
               "fontColor": "",
               "rotation": 0,
                        "bold": False
                    }
            category_label.append(d)    
     



    category_axis = {
                "labelName": "CategoryAxis",
                "parentName": "Axis",
                "labelrows": "",
                "barGap": "",
                "name": "parent",
                "DisplayText": "",
                "labelDefaults": {
                    "rotation": 0,
                    "offset": {
                            "x": "",
                            "y": ""
                        }
                    ,
                    "fontColor": "",
                    "color": "",
                    "fontFamily": "",
                    "fontSize": "",
                    "bold": False
                },
                "fontColor": "",
                "color": "",
                "fontFamily": "",
                "fontSize": "",
                "bold": False,
                "visible": True,
                "categories": "DoNotReOrder",
                "series": "ByEachCategory",
                "titleLabel": "",
                "titleGap": "",
                "titleposition": "",
                "titleFont": "Arial",
                "titleSize": 16,
                "titleBold": False,
                "titleColor": "black",
                "categoryLabel":category_label
            }

    result_data = []
    data = data.sort_values(list(data.columns)[1], ascending = False)
    summary_df = data.copy(deep = True)
    summary_df.drop('Series Label', axis = 1, inplace = True)
    summary_d = dict(summary_df.max())
    summary_max_value = max(list(summary_d.values()))

    def unit_of_measurement(value):
        a = numerize.numerize(value)
        unit = ''.join([i for i in a if not i.isdigit()])
        unit = unit.replace('.','')
        return unit
    uom = unit_of_measurement(int(summary_max_value))
    #
    for col in data.columns:
        dt = {}
        if col != 'Series Label':
            df = data.sort_values(col, ascending = False)
            options = ['Other', 'other']
            df1 = df.loc[df['Series Label'].isin(options)]
            df = df.loc[~df['Series Label'].isin(options)]
            df = df.append(df1, ignore_index = True)
            dt[col] = dict(zip(df['Series Label'], df[col]))
            result_data.append(dt)
    javascript = []
    x_ = 0
    sum_category ={}
    for i in result_data:
        for cat, comp in i.items():
            sum_category[cat] = sum(comp.values())       
     
    total = {}
    for cat, val in sum_category.items():
        total[cat] = truncate([val], uom)
    summaryAxisLabel = []
    for ke, val in total.items():
        unit = ''.join([i for i in val if not i.isdigit()])
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
    
                    
    summary_axis =  {
                "labelDefaults": {
                    "rotation": 0,
                    "offset":
                        {
                            "x": "",
                            "y": ""
                        }
                    ,
                    "color": "",
                    "fontFamily": "",
                    "fontSize": "",
                    "bold": False
                },
                "visible": True,
                "titleLabel": "",
                "titleGap": "",
                "titleposition": "",
                "titleFont": "",
                "titleSize": "",
                "titleBold": False,
                "titleColor": "",
                 "decimalPlaceValue": "",
                "summayAxisLabel": summaryAxisLabel
            }

    value_axis =  {
                "name": "parent",
                "DisplayText": "",
                "majorStep": "",
                "min": "",
                "max": "",
                "minorTick": "",
                "fullspecifiedMajorticks": [
                    {
                        "value": "",
                        "label": True
                    }
                ],
                "visible": True,
                "bold": False,
                "titleLabel": "",
                "titleGap": "",
                "titleposition": "",
                "titleFont": "",
                "titleFontSize": "",
                "titleBold": False,
                "titleColor": "black",
                "labels": 
                    {
                        "labelFormat": "",
                        "maximumLabelFormat": "",
                        "minimumLabelFormat": ""
                    }
                
            }
            
    chart_size = {
                "aspectratio": "",
                "displayWidth": "",
                "ppi": ""
            }


    child = []
    for col in data.columns:
        if col != 'Series Label':
            c ={
               "name": col,
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
               "bold": False,
               "brush": "",
               "stroke":"",
               "fill": ""
               }
               
            child.append(c)   
           
           
    dataLabels = [] 
    for  i in data['Series Label']:
        dt ={
          "name": i,
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
          "bold": False,
          "brush": "",
          "stroke":"",
          "fill": "",
          "child":child
                        }
        dataLabels.append(dt)
        
        
        
    subtitle = {
                "name": "2015-2022 sales",
                "DisplayText": "",
                "fontFamily": "Calibri",
                "fontSize": 12,
                "fontColor": "black",
                "visible": True,
                "bold": False
            }
            
    title = {
                "name": "North America Confectionary market companies",
                "DisplayText": "",
                "fontFamily": "Calibri",
                "fontSize": 12,
                "fontColor": "black",
                "visible": True,
                "pad": 0,
                "bold": False
            }

    rollup = {
                "label": "",
                "threshold": 0,
                "category threshold": 0,
                "companies": [],
                "updateCompanies": []
            }
    
    categoryaxisorientation = {"Label": "Horizontal"}
    acquisition = {"Labels": data["Series Label"].values.tolist()}
    showPercentage = {'visible':False}
            
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
    
    color_code = {}
    color_count = 0
    for each_comp in data['Series Label'].unique():
        if each_comp == 'Other' or each_comp == 'Others':
            color_code[each_comp] = 'grey'
        else:
            try:
                color_code[each_comp] = list_of_colors[color_count]
                color_count += 1
            except:
                import random
                random_number = random.randint(0,16777215)
                hex_number = str(hex(random_number))
                color_code[each_comp] = '#'+ hex_number[2:]
    
    mekko_total = 0
    for value in summary_axis['summayAxisLabel']:
        b = value['name'].replace('$','')
        K = b.replace('K','')
        M = K.replace('M','')
        B = M.replace('B','')
        mekko_total += int(B)
    response = {
            "chart": "mekko",
            "type": "plotly",
            "input_data": result,
            "Data": {
                    "Labels": [
                        "Axis",
                        "chartSize",
                        "DataLabels",
                        "MekkoTotal",
                        "subTitle",
                        "title",
                        "rollUp",
                        "Acquisition",
                        "CategoryAxisOrientation",
                        "showPercentage"
                    ],
                    "Axis": [
                        "CategoryAxis",
                        "SummaryAxis",
                        "ValueAxis"
                    ],
                    "MekkoTotal": {"Total": "Total = ${0}b".format(mekko_total),
                           "fontColor": "black",
                            "color": "",
                            "fontFamily": "",
                            "fontSize":12,
                            "bold": False},
                    "CategoryAxis": category_axis,
                    "CategoryAxisOrientation" : categoryaxisorientation,
                    "SummaryAxis": summary_axis,
                    "ValueAxis": value_axis,
                    "chartSize": chart_size,
                    "DataLabels": {"dataLabels":dataLabels},
                    "subTitle": subtitle,
                    "title": title,
                    "rollUp": rollup,
                    "Acquisition": acquisition,
                    "showPercentage": showPercentage
                }    ,
                 "Project": projectName,
                "Name": "",
                "Year": "",
                "saveChart":False,
                "Market": "",
                "Region": "",
                "Currency": "",
                "barcolor": color_code
            }
            
    return response