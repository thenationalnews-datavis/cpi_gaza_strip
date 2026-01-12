# Data processing: Consumer Price Index (CPI) in the Gaza Strip

January 12, 2026

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
| 0999 | All items of consumer price index | All items | 2025-12-01 00:00:00 | 195.601 | -11.5441 |
| 01 | Food and Non-Alcoholic Beverages | Food and drink | 2025-12-01 00:00:00 | 202.778 | -21.0678 |
| 02 | Alcholoic Beverages, Tobacco and Narcotics | Alcoholic beverages and tobacco | 2025-12-01 00:00:00 | 609.056 | 28.037 |
| 03 | Clothing and Footwear | Clothing | 2025-12-01 00:00:00 | 153.203 | 15.255 |
| 04 | Housing, Water, Electricity, Gas and Other Fuels | Housing expenses | 2025-12-01 00:00:00 | 292.924 | -4.97392 |
| 05 | Furnishings, Household Equipment and Routine Houshold Maintenance | Houshold equipement and maintenance | 2025-12-01 00:00:00 | 112.411 | -5.69273 |
| 06 | Health | Health | 2025-12-01 00:00:00 | 183.882 | 0 |
| 07 | Transport | Transport | 2025-12-01 00:00:00 | 248.984 | -38.4755 |
| 08 | Information and Communication | Information and Communication | 2025-12-01 00:00:00 | 100.424 | 0 |
| 09 | Recreation, Sport, Culture, Gardens and Pets | Recreation | 2025-12-01 00:00:00 | 132.204 | 0 |
| 10 | Education Services | Education | 2025-12-01 00:00:00 | 102.396 | 0 |
| 11 | Resturants and Accomodation Services | Hospitality | 2025-12-01 00:00:00 | 108.58 | 3.64617 |
| 12+13 | Miscellaneous Goods and Services (12+13) | Miscellaneous | 2025-12-01 00:00:00 | 116.847 | -1.1109 |
| 12 | Insurance and Financial Services | Financial services | 2025-12-01 00:00:00 | 99.0217 | -0.190575 |
| 13 | Personal Care, Social Protection and Miscellaneous Goods and Services | Personal care and miscellaneous | 2025-12-01 00:00:00 | 126.088 | -1.48074 |

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
| 04522 | Liquefied hydrocarbons | 2025-12-01 00:00:00 | 858.964 | -2.31608 |
| 04530 | Liquid fuels | 2025-12-01 00:00:00 | 777.409 | 1.11111 |
| 0454 | Solid fuels | 2025-12-01 00:00:00 | 517.875 | -50 |
| 04541 | Coal, coal briquettes and peat | 2025-12-01 00:00:00 | 517.875 | -50 |
| 07 | TRANSPORT | 2025-12-01 00:00:00 | 248.984 | -38.4755 |
| 0722 | Fuels and lubricants for personal transport equipment | 2025-12-01 00:00:00 | 1474.03 | -33.7137 |
| 07221 | Diesel | 2025-12-01 00:00:00 | 777.374 | 1.11111 |
| 07222 | Petrol | 2025-12-01 00:00:00 | 1526.41 | -34.3675 |
| 073 | PASSENGER TRANSPORT SERVICES | 2025-12-01 00:00:00 | 133.095 | -50.9243 |
| 0999 | Consumer Price Index | 2025-12-01 00:00:00 | 195.601 | -11.5441 |

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
| Food and Non-Alcoholic Beverages | All food and drink | 01 | 2025-12-01 00:00:00 | 202.778 | -21.0678 |
| Cereals and cereal products | Cereals | 0111 | 2025-12-01 00:00:00 | 104.108 | -13.5497 |
| Live animals, meat and other parts of slaughtered land animals | Meat | 0112 | 2025-12-01 00:00:00 | 242.712 | -29.9812 |
| Milk, other dairy products and eggs | Dairy products | 0114 | 2025-12-01 00:00:00 | 235.107 | -31.4699 |
| Oils and fats | Oils and fats | 0115 | 2025-12-01 00:00:00 | 134.192 | -6.29272 |
| Fruits and nuts | Fruit and nuts | 0116 | 2025-12-01 00:00:00 | 303.071 | -13.2052 |
| Vegetables, tubers, plantains, cooking bananas and pulses | Vegetables | 0117 | 2025-12-01 00:00:00 | 240.929 | -19.7131 |
| Sugar, confectionery and desserts | Sugar | 0118 | 2025-12-01 00:00:00 | 134.507 | -21.3732 |
| Ready-made food and other food products | Other food products | 0119 | 2025-12-01 00:00:00 | 184.21 | -5.6265 |
| Coffee and coffee substitutes | Coffee | 0122 | 2025-12-01 00:00:00 | 140.384 | 4.03666 |
| Water | Water | 0124 | 2025-12-01 00:00:00 | 200 | -20 |
| Soft drinks | Soft drinks | 0126 | 2025-12-01 00:00:00 | 162.562 | -9.09091 |

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

| date_month | date_label | All items | Housing expenses | Transport | Food and drink | Health | Clothing | Recreation | Houshold equipement and maintenance | Hospitality | Education | Information and Communication | Miscellaneous |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-01-01 00:00:00 | January 2025 | 312.365 | 312.246 | 334.071 | 359.025 | 183.882 | 180.225 | 132.204 | 132.673 | 104.76 | 102.396 | 99.7815 | 123.886 |
| 2025-02-01 00:00:00 | February 2025 | 208.368 | 157.056 | 395.285 | 213.255 | 183.882 | 171.039 | 132.204 | 117.612 | 104.76 | 102.396 | 99.7815 | 119.176 |
| 2025-03-01 00:00:00 | March 2025 | 292.928 | 482.931 | 328.687 | 304.901 | 183.882 | 170.843 | 132.204 | 122.39 | 104.76 | 102.396 | 99.7815 | 117.237 |
| 2025-04-01 00:00:00 | April 2025 | 514.354 | 1018.13 | 506.552 | 489.027 | 183.882 | 171.003 | 132.204 | 167.005 | 104.76 | 102.396 | 99.7815 | 138.458 |
| 2025-05-01 00:00:00 | May 2025 | 736.587 | 1105.05 | 401.132 | 726.379 | 183.882 | 171.258 | 132.204 | 165.676 | 104.76 | 102.396 | 99.7815 | 145.593 |
| 2025-06-01 00:00:00 | June 2025 | 777.426 | 1099.83 | 565.912 | 1388.38 | 183.882 | 171.258 | 132.204 | 165.676 | 104.76 | 102.396 | 100.216 | 152.95 |
| 2025-07-01 00:00:00 | July 2025 | 824.697 | 1101.79 | 629.2 | 1468.47 | 183.882 | 171.258 | 132.204 | 162.185 | 104.76 | 102.396 | 100.216 | 169.88 |
| 2025-08-01 00:00:00 | August 2025 | 656.957 | 1104.53 | 755.231 | 975.418 | 183.882 | 171.258 | 132.204 | 155.154 | 104.76 | 102.396 | 100.216 | 178.978 |
| 2025-09-01 00:00:00 | September 2025 | 568.368 | 1405.68 | 706.341 | 823.875 | 183.882 | 171.258 | 132.204 | 186.649 | 104.76 | 102.396 | 100.424 | 151.635 |
| 2025-10-01 00:00:00 | October 2025 | 338.621 | 300.66 | 564.742 | 573.89 | 183.882 | 158.171 | 132.204 | 148.74 | 104.76 | 102.396 | 100.424 | 122.263 |
| 2025-11-01 00:00:00 | November 2025 | 221.128 | 308.256 | 404.691 | 256.901 | 183.882 | 132.926 | 132.204 | 119.196 | 104.76 | 102.396 | 100.424 | 118.16 |
| 2025-12-01 00:00:00 | December 2025 | 195.601 | 292.924 | 248.984 | 202.778 | 183.882 | 153.203 | 132.204 | 112.411 | 108.58 | 102.396 | 100.424 | 116.847 |

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

| date_month | date_label | All food and drink | Fruit and nuts | Meat | Vegetables | Dairy products | Water | Soft drinks | Coffee | Sugar | Oils and fats | Cereals | Other food products |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-01-01 00:00:00 | January 2025 | 359.025 | 487.726 | 347.038 | 559.793 | 266.049 | 500 | 176.225 | 238.338 | 233.722 | 272.207 | 233.496 | 307.475 |
| 2025-02-01 00:00:00 | February 2025 | 213.255 | 303.82 | 210.77 | 267.367 | 191.463 | 317.857 | 126.245 | 169.198 | 148.56 | 171.292 | 111.696 | 222.84 |
| 2025-03-01 00:00:00 | March 2025 | 304.901 | 391.785 | 355.306 | 502.136 | 215.537 | 316.667 | 150.207 | 226.057 | 184.552 | 210.584 | 139.956 | 216.259 |
| 2025-04-01 00:00:00 | April 2025 | 489.027 | 593.144 | 366.607 | 968.3 | 543.001 | 308.333 | 150.207 | 268.538 | 470.101 | 507.162 | 248.539 | 293.124 |
| 2025-05-01 00:00:00 | May 2025 | 726.379 | 693.67 | 368.86 | 1265.39 | 1002.39 | 450 | 150.207 | 311.129 | 1147.71 | 1006.97 | 660.628 | 345.096 |
| 2025-06-01 00:00:00 | June 2025 | 1388.38 | 1406.83 | 1743.95 | 2356.26 | 1035.22 | 450 | 150.207 | 463.527 | 2876.46 | 992.791 | 679.139 | 414.758 |
| 2025-07-01 00:00:00 | July 2025 | 1468.47 | 1622.58 | 1739.87 | 2102.85 | 1035.22 | 450 | 150.207 | 539.415 | 3794.09 | 848.149 | 919.23 | 709.419 |
| 2025-08-01 00:00:00 | August 2025 | 975.418 | 1267.67 | 928.565 | 1624.94 | 1133.54 | 450 | 150.207 | 408.527 | 1439.42 | 477.999 | 594.538 | 468.787 |
| 2025-09-01 00:00:00 | September 2025 | 823.875 | 1494.11 | 903.23 | 1265.06 | 1397.4 | 450 | 650.248 | 586.927 | 385.803 | 273.586 | 230.435 | 277.075 |
| 2025-10-01 00:00:00 | October 2025 | 573.89 | 765.67 | 739.789 | 662.634 | 1571.9 | 450 | 650.248 | 474.913 | 243.282 | 193.728 | 110.879 | 169.665 |
| 2025-11-01 00:00:00 | November 2025 | 256.901 | 349.182 | 346.639 | 300.085 | 343.071 | 250 | 178.818 | 134.937 | 171.07 | 143.204 | 120.425 | 195.192 |
| 2025-12-01 00:00:00 | December 2025 | 202.778 | 303.071 | 242.712 | 240.929 | 235.107 | 200 | 162.562 | 140.384 | 134.507 | 134.192 | 104.108 | 184.21 |
