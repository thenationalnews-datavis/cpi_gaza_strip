# %% [markdown]
# ---
# title: "Data processing: Consumer Price Index (CPI) in the Gaza Strip"
# date-format: long
# date: last-modified
# lang: en
# format:
#   gfm:
#     html-math-method: katex
#     fig-width: 15
#     fig-asp: 1
#     code-annotations: below
#     df-print: kable
#     wrap: none
# execute:
#   echo: true
#   eval: true
#   warning: false
# ---

# %% [markdown]
"""
By [Isaac Arroyo](https://github.com/isaacarroyov), Data Visualisation Journalist
"""

# %%
#| label: load_libraries_paths_data
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

# %% [markdown]
"""
## Intro

Every month, the [Palestinian Central Bureau of 
Statistics (PCBS)](https://www.pcbs.gov.ps/default.aspx) publishes 
the Consumer Price Index (CPI) in the Gaza Strip. The CPI measures the cost 
of living and the changes in the prices of goods and services purchased or 
acquired by households.

> [!NOTE]
>
> Baseline (2018 prices) = **100**
> 
> Values bigger than **100** :arrow_right: higher costs

The data is downloaded via the 
[Humanitarian Data Exchange (HDX)](https://data.humdata.org/) platform and 
it's under the name ["State of Palestine - Consumer Price 
Index](https://data.humdata.org/dataset/state-of-palestine-consumer-price-index).

Once downloaded, this Python script is run to create five CSVs:

* Long format:
  - Consumer Price Index by major divisions
  - Consumer Price Index by major groups
  - Consumer Price Index by major food group
* Wide format:
  - Consumer Price Index by major groups
  - Consumer Price Index by major food group
"""

# %%
#| label: create-path2cpi
path2cpi = path2input_data + "/consumer-price-index.xlsx"

# %% [markdown]
"""
## Functions

Helpers to extract and format the data from the XLSX file
"""

# %% [markdown]
"""
### `func_parse_month_token`

Convert a header or cell token into a month-end `pandas.Timestamp`. Handles 
strings like 'Dec.2022', 'Jan 2023', or datetime objects.
"""

# %%
#| label: create-func_parse_month_token
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

# %% [markdown]
"""
### `func_build_month_map`

Scan the CPI sheet (wide format) and return a list of tuples (`date`, 
`index_col`, `pct_col` or `None`) mapping each month to its index and 
percentage (%) columns.
"""

# %%
#| label: create-func_build_month_map
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

# %% [markdown]
"""
## CPI by Major Groups

Extract the data from the second sheet named "cpi - data by Major 
Groups". The sheet contains the CPI and percentage changes of all the 
groups (01 - 13, including a special group with the code '12+13') and the 
overall CPI (0999)
"""

# %%
#| label: create-func_load_major_groups_xlsx
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

# %%
#| label: create-db_cpi_major_groups
db_cpi_major_groups = func_load_major_groups_xlsx(xlsx_path=path2cpi)

# %% [markdown]
"""
We will rename the groups with shorter names. The new names are in 
`'cpi_groups_names_codes.csv'`
"""

# %%
#| label: load-df_group_code_name
df_group_code_name = pd.read_csv(filepath_or_buffer = path2extras + "/cpi_groups_names_codes.csv")

# %%
#| label: show-df_group_code_name
#| echo: false
Markdown(
    df_group_code_name
    .to_markdown(index = False))

# %%
#| label: add_short_names_to_db_cpi_major_groups
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

# %%
#| label: show_tail-db_cpi_major_groups
#| echo: false
Markdown(
    db_cpi_major_groups
    .groupby('code_good_service')
    .tail(n = 1)
    .to_markdown(index = False))

# %% [markdown]
"""
## CPI by divisions

Extract the data from the first sheet named "cpi - data by major 
division". The sheet contains the CPI and percentage changes of the elements 
of the first seven major groups (01 - 07) and overall CPI (0999)
"""

# %%
#| label: create-func_load_major_division_xlsx_en
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

# %%
#| label: create-db_cpi_major_divisions
db_cpi_major_divisions = func_load_major_division_xlsx(xlsx_path= path2cpi)

# ~ Save data ~ #
db_cpi_major_divisions.to_csv(path_or_buf= path2output_data + '/long_cpi_gaza_strip_major_divisions.csv', index = False)

# %%
#| label: show_tail-db_cpi_major_divisions
#| echo: false
Markdown(
    db_cpi_major_divisions
    .groupby('name_good_service')
    .tail(n = 1)
    .tail(10)
    .to_markdown(index= False))

# %% [markdown]
"""
## CPI by major food groups

Food will always be a relevant topic, especially in the Gaza Strip. The 
group "01 - Food and Non-Alcoholic Beverages" in `db_cpi_major_divisions` 
has many levels of information; however, we will focus on the codes with 
four digits.

Additionally, we will rename the divisions with shorter names. The new 
names are in `'cpi_food_names_codes.csv'`
"""

# %%
#| label: load_df_food_code_name
# Load new names
df_food_code_name = pd.read_csv(filepath_or_buffer= path2extras + "/cpi_food_names_codes.csv", dtype = str)

# %% [markdown]
"""
Shorter division/element names
"""

# %%
#| label: show_df_food_code_name
#| echo: false
Markdown(
    df_food_code_name
    .to_markdown(index = False))

# %%
#| label: create-db_cpi_foods
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

# %%
#| label: show_tail-db_cpi_foods
Markdown(
    db_cpi_foods
    .groupby('code_food')
    .tail(n = 1)
    .to_markdown(index = False))

# %% [markdown]
"""
## Wide format

In this format, the columns are ordered in descending order (left to right) 
based on their latest CPI value, except:

* "All items" (major groups database): Always first
* "Miscellaneous" (major groups database): Always last
* "All food and drink" (major food groups database): Always first
* "Other food products" (major food groups database): Always last
"""

# %% [markdown]
"""
#### Cost of living in Gaza

> [!NOTE]
> 
> Some groups are omitted in this version:
> 
> * Group 02 (Alcoholic beverages and tobacco): Extreme values that overshadowed the overall results
> * Groups 12 and 13 (Financial services and Personal care and miscellaneous): They're combined in Group 12+13 (Miscellaneous)
"""

# %% 
#| label: create-df_wide_cpi_gaza_strip_groups
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

# %%
#| label: show_tail-df_wide_cpi_gaza_strip_groups
#| echo: false
Markdown(
    df_wide_cpi_gaza_strip_groups
    .tail(n = 12)
    .to_markdown(index = False))

# %% [markdown]
"""
#### Cost of eating in Gaza
"""

# %%
#| label: create-df_wide_cpi_gaza_strip_foods
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

# %%
#| label: show-df_wide_cpi_gaza_strip_foods
#| echo: false
Markdown(
    df_wide_cpi_gaza_strip_foods
    .tail(12)
    .to_markdown(index = False))
