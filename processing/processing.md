# Data processing: Consumer Price Index (CPI) in the Gaza Strip

December 26, 2025

By [Isaac Arroyo](https://github.com/isaacarroyov), Data Visualisation Journalist

``` python
import os
os.chdir("../")

import pandas as pd
import numpy as np
from dateutil import parser
from IPython.display import Markdown

path2repo = os.getcwd()
path2input_data = path2repo + "/input_data"
path2output_data = path2repo + "/output_data"
path2extras = path2repo + "/extras"
```

## Intro

Every month, the [Palestinian Central Bureau of Statistics (PCBS)](https://www.pcbs.gov.ps/default.aspx) publishes the Consumer Price Index (CPI) in the Gaza Strip. The CPI measures the cost of living and the changes in the prices of goods and services purchased or acquired by households.

> \[!NOTE\]
>
> Baseline (2018 prices) = **100**
>
> Values bigger than **100** :arrow_right: higher costs

The data is downloaded via the [Humanitarian Data Exchange (HDX)](https://data.humdata.org/) platform and it’s under the name [“State of Palestine - Consumer Price Index](https://data.humdata.org/dataset/state-of-palestine-consumer-price-index).

Once downloaded, this Python script is run to create five CSVs:

- Long format:
  - Consumer Price Index by major divisions
  - Consumer Price Index by major groups
  - Consumer Price Index by major food group
- Wide format:
  - Consumer Price Index by major groups
  - Consumer Price Index by major food group

``` python
path2cpi = path2input_data + "/consumer-price-index.xlsx"
```

## Functions

Helpers to extract and format the data from the XLSX file

### `func_parse_month_token`

Convert a header or cell token into a month-end `pandas.Timestamp`. Handles strings like ‘Dec.2022’, ‘Jan 2023’, or datetime objects.

``` python
def func_parse_month_token(token):

    """
    Returns: `pd.Timestamp`
    """

    if isinstance(token, (pd.Timestamp, np.datetime64)):
        cleaned_date = pd.to_datetime(token).to_period("M").to_timestamp("M")
        return cleaned_date
    
    # If not pd.Timestamp or np.datetime64 => clean string 
    cleaned = str(token).replace("  ", " ").replace(".", "")
    cleaned_date = (
        pd.to_datetime(arg = parser.parse(cleaned, dayfirst=False, fuzzy=True))
        .to_period("M")
        .to_timestamp("M"))
    return cleaned_date
```

### `func_build_month_map`

Scan the CPI sheet (wide format) and return a list of tuples (`date`, `index_col`, `pct_col` or `None`) mapping each month to its index and percentage (%) columns.

``` python
def func_build_month_map(
    df,
    header_row_idx,
    date_row_idx,
    first_data_col):

    """
    - df: pd.DataFrame,
    - header_row_idx: int,
    - date_row_idx: int,
    - first_data_col: int
    
    Returns: List[Tuple[pd.Timestamp, int, Optional[int]]]:
    """

    cols = []
    c = first_data_col
    ccount = df.shape[1]
    while c < ccount:
        head = df.iat[header_row_idx, c]
        # Consider this an index column if header says "Index" or there's a date in the date row
        is_index_like = (isinstance(head, str) and head.strip().lower() == "index") or not pd.isna(df.iat[date_row_idx, c])
        if not is_index_like:
            c += 1
            continue

        # Parse date label
        date_token = df.iat[date_row_idx, c] if not pd.isna(df.iat[date_row_idx, c]) else head
        try:
            period = func_parse_month_token(date_token)
        except Exception:
            c += 1
            continue

        # Detect if the next column is % change
        pct_col = None
        if c + 1 < ccount:
            nxt = df.iat[header_row_idx, c + 1]
            if isinstance(nxt, str) and "%" in nxt:
                pct_col = c + 1

        cols.append((period, c, pct_col))
        c += 2 if pct_col is not None else 1

    return cols
```

## CPI by Major Groups

Extract the data from the second sheet named “cpi - data by Major Groups”. The sheet contains the CPI and percentage changes of all the groups (01 - 13, including a special group with the code ‘12+13’) and the overall CPI (0999)

``` python
def func_load_major_groups_xlsx(
    xlsx_path,
    sheet_name = "cpi - by Major Groups ",
    code_col = 0,
    name_col = 2,
    header_row_idx = 5,
    date_row_idx = 5,
    data_start_row = 6):

    """
    Load CPI data by major group and return tidy long format:
    columns = [code_good_service, name_good_service, date_month, cpi_index, pct_change].

    xlsx_path: str | Path,
    sheet_name: str = "cpi - by Major Groups ",
    code_col: int = 0,
    name_col: int = 2,
    header_row_idx: int = 5,
    date_row_idx: int = 5,
    data_start_row: int = 6
    
    Returns: pd.DataFrame
    """

    df = pd.read_excel(io = xlsx_path, sheet_name = sheet_name, header = None)
    first_data_col = max(code_col, name_col) + 1
    months = func_build_month_map(df, header_row_idx, date_row_idx, first_data_col)

    base = (df
            .iloc[data_start_row:, [code_col, name_col]]
            .rename(
                columns= {
                    code_col: "code_good_service",
                    name_col: "name_good_service"}))

    frames = []
    for date, idx_col, pct_col in months:
        tmp = base.copy()
        tmp["date_month"] = date.strftime("%Y-%m-01")
        tmp["date_month"] = pd.to_datetime(tmp["date_month"])
        tmp["cpi_index"] = pd.to_numeric(df.iloc[data_start_row:, idx_col], errors="coerce")
        tmp["pct_change"] = pd.to_numeric(df.iloc[data_start_row:, pct_col], errors="coerce") if pct_col is not None else pd.NA
        frames.append(tmp)

    out = pd.concat(frames, ignore_index=True)
    out = out[~out["code_good_service"].isna()].copy()
    out["code_good_service"] = (out["code_good_service"]
                                .astype(str)
                                .str
                                .replace(r"\.0$", "", regex=True))
    
    out = (out
           .sort_values(["code_good_service", "date_month"])
           .reset_index(drop=True))

    return out
```

``` python
db_cpi_major_groups = func_load_major_groups_xlsx(xlsx_path=path2cpi)
```

We will rename the groups with shorter names. The new names are in `'cpi_groups_names_codes.csv'`

``` python
df_group_code_name = pd.read_csv(filepath_or_buffer = path2extras + "/cpi_groups_names_codes.csv")
```

| code_good_service | name_good_service | short_name_good_service |
|:---|:---|:---|
| 0999 | All items of consumer price index | All items |
| 01 | Food and Non-Alcoholic Beverages | Food and drink |
| 02 | Alcholoic Beverages, Tobacco and Narcotics | Alcoholic beverages and tobacco |
| 03 | Clothing and Footwear | Clothing |
| 04 | Housing, Water, Electricity, Gas and Other Fuels | Housing expenses |
| 05 | Furnishings, Household Equipment and Routine Houshold Maintenance | Houshold equipement and maintenance |
| 06 | Health | Health |
| 07 | Transport | Transport |
| 08 | Information and Communication | Information and Communication |
| 09 | Recreation, Sport, Culture, Gardens and Pets | Recreation |
| 10 | Education Services | Education |
| 11 | Resturants and Accomodation Services | Hospitality |
| 12+13 | Miscellaneous Goods and Services (12+13) | Miscellaneous |
| 12 | Insurance and Financial Services | Financial services |
| 13 | Personal Care, Social Protection and Miscellaneous Goods and Services | Personal care and miscellaneous |

``` python
db_cpi_major_groups = (pd.merge(
        left  = df_group_code_name,
        right = db_cpi_major_groups,
        on    = ['code_good_service', 'name_good_service'],
        how   = "right")
    .reset_index(drop = True))

# Order goods and services
list_order_name_groups = df_group_code_name['short_name_good_service'].values.tolist()
db_cpi_major_groups['short_name_good_service'] = pd.Categorical(
    values= db_cpi_major_groups['short_name_good_service'],
    categories = list_order_name_groups,
    ordered = True)
db_cpi_major_groups = (db_cpi_major_groups
                       .sort_values(["short_name_good_service", "date_month"])
                       .reset_index(drop = True))

# ~ Save data ~ #
db_cpi_major_groups.to_csv(path_or_buf= path2output_data + '/long_cpi_gaza_strip_major_groups.csv', index = False)
```

| code_good_service | name_good_service | short_name_good_service | date_month | cpi_index | pct_change |
|:---|:---|:---|:---|---:|---:|
| 0999 | All items of consumer price index | All items | 2025-11-01 00:00:00 | 221.128 | -34.6974 |
| 01 | Food and Non-Alcoholic Beverages | Food and drink | 2025-11-01 00:00:00 | 256.901 | -55.2351 |
| 02 | Alcholoic Beverages, Tobacco and Narcotics | Alcoholic beverages and tobacco | 2025-11-01 00:00:00 | 475.688 | 11.0581 |
| 03 | Clothing and Footwear | Clothing | 2025-11-01 00:00:00 | 132.926 | -15.961 |
| 04 | Housing, Water, Electricity, Gas and Other Fuels | Housing expenses | 2025-11-01 00:00:00 | 308.256 | 2.5264 |
| 05 | Furnishings, Household Equipment and Routine Houshold Maintenance | Houshold equipement and maintenance | 2025-11-01 00:00:00 | 119.196 | -19.8629 |
| 06 | Health | Health | 2025-11-01 00:00:00 | 183.882 | 0 |
| 07 | Transport | Transport | 2025-11-01 00:00:00 | 404.691 | -28.3404 |
| 08 | Information and Communication | Information and Communication | 2025-11-01 00:00:00 | 100.424 | 0 |
| 09 | Recreation, Sport, Culture, Gardens and Pets | Recreation | 2025-11-01 00:00:00 | 132.204 | 0 |
| 10 | Education Services | Education | 2025-11-01 00:00:00 | 102.396 | 0 |
| 11 | Resturants and Accomodation Services | Hospitality | 2025-11-01 00:00:00 | 104.76 | 0 |
| 12+13 | Miscellaneous Goods and Services (12+13) | Miscellaneous | 2025-11-01 00:00:00 | 118.16 | -3.35574 |
| 12 | Insurance and Financial Services | Financial services | 2025-11-01 00:00:00 | 99.2108 | -0.101922 |
| 13 | Personal Care, Social Protection and Miscellaneous Goods and Services | Personal care and miscellaneous | 2025-11-01 00:00:00 | 127.983 | -4.60437 |

## CPI by divisions

Extract the data from the first sheet named “cpi - data by major division”. The sheet contains the CPI and percentage changes of the elements of the first seven major groups (01 - 07) and overall CPI (0999)

``` python
def func_load_major_division_xlsx(
    xlsx_path,
    sheet_name = "cpi - data by major division ",
    code_col = 0,
    name_col = 2,
    header_row_idx = 2,
    date_row_idx = 3,
    data_start_row = 4):

    """
    Load CPI data by major division (English names) and return tidy long format:
    columns = [code_good_service, name_good_service, date_month, cpi_index, pct_change].

    xlsx_path: str | Path,
    sheet_name: str = "cpi - data by major division ",
    code_col: int = 0,        # Column A: codes (e.g., 0999 at A5)
    name_col: int = 2,        # Column C: English group names (e.g., "Consumer Price Index" at C5)
    header_row_idx: int = 2,  # Row with "Index" / "%" markers
    date_row_idx: int = 3,    # Row with actual month timestamps
    data_start_row: int = 4   # First data row
    
    Returns: pd.DataFrame
    """

    df = pd.read_excel(io = xlsx_path, sheet_name = sheet_name, header = None)
    first_data_col = max(code_col, name_col) + 1
    months = func_build_month_map(df, header_row_idx, date_row_idx, first_data_col)

    base = (df
            .iloc[data_start_row:, [code_col, name_col]]
            .rename(columns = {
                code_col: "code_good_service",
                name_col: "name_good_service"}))

    frames = []
    for date, idx_col, pct_col in months:
        tmp = base.copy()
        tmp["date_month"] = date.strftime("%Y-%m-01")
        tmp["date_month"] = pd.to_datetime(tmp["date_month"])
        tmp["cpi_index"] = pd.to_numeric(df.iloc[data_start_row:, idx_col], errors="coerce")
        tmp["pct_change"] = pd.to_numeric(df.iloc[data_start_row:, pct_col], errors="coerce") if pct_col is not None else pd.NA
        frames.append(tmp)

    out = pd.concat(frames, ignore_index=True)
    out = out[~out["code_good_service"].isna()].copy()
    out["code_good_service"] = (out["code_good_service"]
                                .astype(str)
                                .str.replace(r"\.0$", "", regex=True))
  
    out = (out
           .sort_values(["code_good_service", "date_month"])
           .reset_index(drop=True))

    return out
```

``` python
db_cpi_major_divisions = func_load_major_division_xlsx(xlsx_path= path2cpi)

# ~ Save data ~ #
db_cpi_major_divisions.to_csv(path_or_buf= path2output_data + '/long_cpi_gaza_strip_major_divisions.csv', index = False)
```

| code_good_service | name_good_service | date_month | cpi_index | pct_change |
|---:|:---|:---|---:|---:|
| 04522 | Liquefied hydrocarbons | 2025-11-01 00:00:00 | 879.329 | 18.3871 |
| 04530 | Liquid fuels | 2025-11-01 00:00:00 | 768.866 | -40.8249 |
| 0454 | Solid fuels | 2025-11-01 00:00:00 | 1035.75 | 282.979 |
| 04541 | Coal, coal briquettes and peat | 2025-11-01 00:00:00 | 1035.75 | 282.979 |
| 07 | TRANSPORT | 2025-11-01 00:00:00 | 404.691 | -28.3404 |
| 0722 | Fuels and lubricants for personal transport equipment | 2025-11-01 00:00:00 | 2223.73 | -44.0664 |
| 07221 | Diesel | 2025-11-01 00:00:00 | 768.831 | -40.8249 |
| 07222 | Petrol | 2025-11-01 00:00:00 | 2325.7 | -44.1333 |
| 073 | PASSENGER TRANSPORT SERVICES | 2025-11-01 00:00:00 | 271.204 | 0 |
| 0999 | Consumer Price Index | 2025-11-01 00:00:00 | 221.128 | -34.6974 |

## CPI by major food groups

Food will always be a relevant topic, especially in the Gaza Strip. The group “01 - Food and Non-Alcoholic Beverages” in `db_cpi_major_divisions` has many levels of information; however, we will focus on the codes with four digits.

Additionally, we will rename the divisions with shorter names. The new names are in `'cpi_food_names_codes.csv'`

``` python
# Load new names
df_food_code_name = pd.read_csv(filepath_or_buffer= path2extras + "/cpi_food_names_codes.csv", dtype = str)
```

Shorter division/element names

| code_food | name_food | short_name_food |
|---:|:---|:---|
| 01 | Food and Non-Alcoholic Beverages | All food and drink |
| 0111 | Cereals and cereal products | Cereals |
| 0112 | Live animals, meat and other parts of slaughtered land animals | Meat |
| 0114 | Milk, other dairy products and eggs | Dairy products |
| 0115 | Oils and fats | Oils and fats |
| 0116 | Fruits and nuts | Fruit and nuts |
| 0117 | Vegetables, tubers, plantains, cooking bananas and pulses | Vegetables |
| 0124 | Water | Water |
| 0118 | Sugar, confectionery and desserts | Sugar |
| 0122 | Coffee and coffee substitutes | Coffee |
| 0126 | Soft drinks | Soft drinks |
| 0119 | Ready-made food and other food products | Other food products |

``` python
# Create mask: codes of four digits
mask_food_codes = db_cpi_major_divisions['code_good_service'].str.startswith("01")
mask_lenght_4 = db_cpi_major_divisions['code_good_service'].str.len() == 4
maks_food_divisions = mask_food_codes & mask_lenght_4

# Isolate group 01
data_cpi_group_01 = db_cpi_major_groups.query('code_good_service == "01"').drop(columns = ["short_name_good_service"])

# Isolate major food groups
data_major_food_groups = db_cpi_major_divisions[maks_food_divisions]

# Combine Group 01 and major food groups and add short food names
db_cpi_foods = (pd.concat(
        objs= [data_cpi_group_01, data_major_food_groups],
        ignore_index= True)
    .rename(
        columns = {
            'code_good_service': 'code_food',
            'name_good_service': 'name_food'})
    .merge(
        right = df_food_code_name,
        on = ["code_food", "name_food"],
        how = "left")
    [['name_food',
      'short_name_food',
      'code_food',
      'date_month',
      'cpi_index',
      'pct_change']])

# ~ Save data ~ #
db_cpi_foods.to_csv(path_or_buf= path2output_data + '/long_cpi_gaza_strip_major_foods.csv', index = False)
```

``` python
Markdown(
    db_cpi_foods
    .groupby('code_food')
    .tail(n = 1)
    .to_markdown(index = False))
```

| name_food | short_name_food | code_food | date_month | cpi_index | pct_change |
|:---|:---|---:|:---|---:|---:|
| Food and Non-Alcoholic Beverages | All food and drink | 01 | 2025-11-01 00:00:00 | 256.901 | -55.2351 |
| Cereals and cereal products | Cereals | 0111 | 2025-11-01 00:00:00 | 120.425 | 8.60918 |
| Live animals, meat and other parts of slaughtered land animals | Meat | 0112 | 2025-11-01 00:00:00 | 346.639 | -53.1436 |
| Milk, other dairy products and eggs | Dairy products | 0114 | 2025-11-01 00:00:00 | 343.071 | -78.1748 |
| Oils and fats | Oils and fats | 0115 | 2025-11-01 00:00:00 | 143.204 | -26.0802 |
| Fruits and nuts | Fruit and nuts | 0116 | 2025-11-01 00:00:00 | 349.182 | -54.3953 |
| Vegetables, tubers, plantains, cooking bananas and pulses | Vegetables | 0117 | 2025-11-01 00:00:00 | 300.085 | -54.7133 |
| Sugar, confectionery and desserts | Sugar | 0118 | 2025-11-01 00:00:00 | 171.07 | -29.6823 |
| Ready-made food and other food products | Other food products | 0119 | 2025-11-01 00:00:00 | 195.192 | 15.0458 |
| Coffee and coffee substitutes | Coffee | 0122 | 2025-11-01 00:00:00 | 134.937 | -71.5869 |
| Water | Water | 0124 | 2025-11-01 00:00:00 | 250 | -44.4444 |
| Soft drinks | Soft drinks | 0126 | 2025-11-01 00:00:00 | 178.818 | -72.5 |

## Wide format

In this format, the columns are ordered in descending order (left to right) based on their latest CPI value, except:

- “All items” (major groups database): Always first
- “Miscellaneous” (major groups database): Always last
- “All food and drink” (major food groups database): Always first
- “Other food products” (major food groups database): Always last

#### Cost of living in Gaza

> \[!NOTE\]
>
> Some groups are omitted in this version:
>
> - Group 02 (Alcoholic beverages and tobacco): Extreme values that overshadowed the overall results
> - Groups 12 and 13 (Financial services and Personal care and miscellaneous): They’re combined in Group 12+13 (Miscellaneous)

``` python
# = = = Order wide columns based on latest CPI = = = #
# - - Filter: Latest date - - #
mask_max_date_major_groups = db_cpi_major_groups["date_month"] == db_cpi_major_groups["date_month"].max()

# - - Filter: Omit specific groups - - #
# ~ All items and Miscellaneous will be added manually as first and last elements of the list ~ #
# ~ Group 02 is omitted due to extreme values that overshadowed the overall results ~ #
mask_ignore_all_items_02_12_and_13 = (~db_cpi_major_groups
                                      ["code_good_service"]
                                      .isin(["0999", "02", "12", "13", "12+13"]))
# ~ Create order list ~ #
list_order_columns_name_group = (
    ["All items"]
    + 
    db_cpi_major_groups
    [mask_max_date_major_groups & mask_ignore_all_items_02_12_and_13]
    .sort_values("cpi_index", ascending = False)
    ["short_name_good_service"]
    .tolist()
    +
    ["Miscellaneous"])

df_wide_cpi_gaza_strip_groups = (db_cpi_major_groups
    .drop(columns = ["pct_change", "code_good_service", "name_good_service"])
    .pivot(
        index = 'date_month',
        columns = 'short_name_good_service',
        values = "cpi_index")
    .reset_index()
    .rename_axis(None, axis = 1))
df_wide_cpi_gaza_strip_groups['date_label'] = df_wide_cpi_gaza_strip_groups["date_month"].dt.strftime("%B %Y")

df_wide_cpi_gaza_strip_groups = df_wide_cpi_gaza_strip_groups[['date_month', 'date_label', ] + list_order_columns_name_group]

# ~ Save data ~ #
df_wide_cpi_gaza_strip_groups.to_csv(path_or_buf= path2output_data + "/wide_cpi_gaza_strip_major_groups.csv",index = False)
```

| date_month | date_label | All items | Transport | Housing expenses | Food and drink | Health | Clothing | Recreation | Houshold equipement and maintenance | Hospitality | Education | Information and Communication | Miscellaneous |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024-12-01 00:00:00 | December 2024 | 668.514 | 407.646 | 320.764 | 638.125 | 183.882 | 185.524 | 132.204 | 148.154 | 104.76 | 102.396 | 99.7815 | 129.563 |
| 2025-01-01 00:00:00 | January 2025 | 312.365 | 334.071 | 312.246 | 359.025 | 183.882 | 180.225 | 132.204 | 132.673 | 104.76 | 102.396 | 99.7815 | 123.886 |
| 2025-02-01 00:00:00 | February 2025 | 208.368 | 395.285 | 157.056 | 213.255 | 183.882 | 171.039 | 132.204 | 117.612 | 104.76 | 102.396 | 99.7815 | 119.176 |
| 2025-03-01 00:00:00 | March 2025 | 292.928 | 328.687 | 482.931 | 304.901 | 183.882 | 170.843 | 132.204 | 122.39 | 104.76 | 102.396 | 99.7815 | 117.237 |
| 2025-04-01 00:00:00 | April 2025 | 514.354 | 506.552 | 1018.13 | 489.027 | 183.882 | 171.003 | 132.204 | 167.005 | 104.76 | 102.396 | 99.7815 | 138.458 |
| 2025-05-01 00:00:00 | May 2025 | 736.587 | 401.132 | 1105.05 | 726.379 | 183.882 | 171.258 | 132.204 | 165.676 | 104.76 | 102.396 | 99.7815 | 145.593 |
| 2025-06-01 00:00:00 | June 2025 | 777.426 | 565.912 | 1099.83 | 1388.38 | 183.882 | 171.258 | 132.204 | 165.676 | 104.76 | 102.396 | 100.216 | 152.95 |
| 2025-07-01 00:00:00 | July 2025 | 824.697 | 629.2 | 1101.79 | 1468.47 | 183.882 | 171.258 | 132.204 | 162.185 | 104.76 | 102.396 | 100.216 | 169.88 |
| 2025-08-01 00:00:00 | August 2025 | 656.957 | 755.231 | 1104.53 | 975.418 | 183.882 | 171.258 | 132.204 | 155.154 | 104.76 | 102.396 | 100.216 | 178.978 |
| 2025-09-01 00:00:00 | September 2025 | 568.368 | 706.341 | 1405.68 | 823.875 | 183.882 | 171.258 | 132.204 | 186.649 | 104.76 | 102.396 | 100.424 | 151.635 |
| 2025-10-01 00:00:00 | October 2025 | 338.621 | 564.742 | 300.66 | 573.89 | 183.882 | 158.171 | 132.204 | 148.74 | 104.76 | 102.396 | 100.424 | 122.263 |
| 2025-11-01 00:00:00 | November 2025 | 221.128 | 404.691 | 308.256 | 256.901 | 183.882 | 132.926 | 132.204 | 119.196 | 104.76 | 102.396 | 100.424 | 118.16 |

#### Cost of eating in Gaza

``` python
# = = = Order wide columns based on latest CPI = = = #
# - - Filter: Latest date - - #
mask_max_date_major_foods = db_cpi_foods["date_month"] == db_cpi_foods["date_month"].max()

# - - Filter: Omit specific groups - - #
# ~ All food and drink and Other food products will be added manually as first and last elements of the list ~ #
mask_ignore_all_foods_other_food_products = ~db_cpi_foods["code_food"].isin(["01", "0119"])

# ~ Create order list ~ #
list_order_columns_name_food = (
    ["All food and drink"]
    +
    db_cpi_foods
    [mask_max_date_major_foods & mask_ignore_all_foods_other_food_products]
    .sort_values("cpi_index", ascending = False)
    ["short_name_food"]
    .tolist()
    +
    ["Other food products"])

df_wide_cpi_gaza_strip_foods = (db_cpi_foods
    .drop(columns=["code_food", "name_food", "pct_change"])
    .pivot(
        index = 'date_month',
        columns = 'short_name_food',
        values = 'cpi_index')
    .reset_index(drop = False)
    .rename_axis(None, axis = 1))

df_wide_cpi_gaza_strip_foods['date_label'] = df_wide_cpi_gaza_strip_foods["date_month"].dt.strftime("%B %Y")

df_wide_cpi_gaza_strip_foods = df_wide_cpi_gaza_strip_foods[["date_month", "date_label"] + list_order_columns_name_food]

# ~ Save data ~ #
df_wide_cpi_gaza_strip_foods.to_csv(path_or_buf= path2output_data + "/wide_cpi_gaza_strip_major_foods.csv",index = False)
```

| date_month | date_label | All food and drink | Fruit and nuts | Meat | Dairy products | Vegetables | Water | Soft drinks | Sugar | Oils and fats | Coffee | Cereals | Other food products |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2024-12-01 00:00:00 | December 2024 | 638.125 | 803.439 | 806.47 | 439.42 | 1091.66 | 500 | 192.685 | 453.893 | 393.547 | 330.585 | 329.193 | 317.519 |
| 2025-01-01 00:00:00 | January 2025 | 359.025 | 487.726 | 347.038 | 266.049 | 559.793 | 500 | 176.225 | 233.722 | 272.207 | 238.338 | 233.496 | 307.475 |
| 2025-02-01 00:00:00 | February 2025 | 213.255 | 303.82 | 210.77 | 191.463 | 267.367 | 317.857 | 126.245 | 148.56 | 171.292 | 169.198 | 111.696 | 222.84 |
| 2025-03-01 00:00:00 | March 2025 | 304.901 | 391.785 | 355.306 | 215.537 | 502.136 | 316.667 | 150.207 | 184.552 | 210.584 | 226.057 | 139.956 | 216.259 |
| 2025-04-01 00:00:00 | April 2025 | 489.027 | 593.144 | 366.607 | 543.001 | 968.3 | 308.333 | 150.207 | 470.101 | 507.162 | 268.538 | 248.539 | 293.124 |
| 2025-05-01 00:00:00 | May 2025 | 726.379 | 693.67 | 368.86 | 1002.39 | 1265.39 | 450 | 150.207 | 1147.71 | 1006.97 | 311.129 | 660.628 | 345.096 |
| 2025-06-01 00:00:00 | June 2025 | 1388.38 | 1406.83 | 1743.95 | 1035.22 | 2356.26 | 450 | 150.207 | 2876.46 | 992.791 | 463.527 | 679.139 | 414.758 |
| 2025-07-01 00:00:00 | July 2025 | 1468.47 | 1622.58 | 1739.87 | 1035.22 | 2102.85 | 450 | 150.207 | 3794.09 | 848.149 | 539.415 | 919.23 | 709.419 |
| 2025-08-01 00:00:00 | August 2025 | 975.418 | 1267.67 | 928.565 | 1133.54 | 1624.94 | 450 | 150.207 | 1439.42 | 477.999 | 408.527 | 594.538 | 468.787 |
| 2025-09-01 00:00:00 | September 2025 | 823.875 | 1494.11 | 903.23 | 1397.4 | 1265.06 | 450 | 650.248 | 385.803 | 273.586 | 586.927 | 230.435 | 277.075 |
| 2025-10-01 00:00:00 | October 2025 | 573.89 | 765.67 | 739.789 | 1571.9 | 662.634 | 450 | 650.248 | 243.282 | 193.728 | 474.913 | 110.879 | 169.665 |
| 2025-11-01 00:00:00 | November 2025 | 256.901 | 349.182 | 346.639 | 343.071 | 300.085 | 250 | 178.818 | 171.07 | 143.204 | 134.937 | 120.425 | 195.192 |
