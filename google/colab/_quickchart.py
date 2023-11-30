"""Automated chart generation for data frames."""
import collections.abc
import itertools
import logging

import IPython
import numpy as np


_CATEGORICAL_DTYPES = (
    np.dtype('object'),
    np.dtype('bool'),
)
_DEFAULT_DATETIME_DTYPE = np.dtype('datetime64[ns]')  # a.k.a. "<M8[ns]".
_DATETIME_DTYPES = (_DEFAULT_DATETIME_DTYPE,)
_DATETIME_DTYPE_KINDS = ('M',)  # More general set of datetime dtypes.
_DATETIME_COLNAME_PATTERNS = (
    'date',
    'datetime',
    'time',
    'timestamp',
)  # Prefix/suffix matches.
_DATETIME_COLNAMES = ('dt', 't', 'ts', 'year')  # Exact matches.
_EXPECTED_DTYPES = _CATEGORICAL_DTYPES + _DATETIME_DTYPES
_CATEGORICAL_LARGE_SIZE_THRESHOLD = 8  # Facet-friendly size limit.

_DATAFRAME_REGISTRY = None


def find_charts(
    df,
    max_chart_instances=None,
):
  """Finds charts compatible with dtypes of the given data frame.

  Args:
    df: (pd.DataFrame) A dataframe.
    max_chart_instances: (int) For a single chart type, the max number instances
      to generate.

  Returns:
    (iterable<ChartSection>) A sequence of chart sections.
  """
  # Lazy import to avoid loading altair and transitive deps on kernel init.
  from google.colab import _quickchart_helpers  # pylint: disable=g-import-not-at-top

  def _ensure_dataframe_registry():
    global _DATAFRAME_REGISTRY
    if _DATAFRAME_REGISTRY is None:
      if IPython.get_ipython():
        variable_namespace = IPython.get_ipython().user_ns
      else:  # Fallback to placeholder namespace in testing environment.
        variable_namespace = {}
      _DATAFRAME_REGISTRY = _quickchart_helpers.DataframeRegistry(
          variable_namespace
      )

  _ensure_dataframe_registry()

  chart_sections = determine_charts(
      df, _DATAFRAME_REGISTRY, max_chart_instances
  )
  if not chart_sections:
    print('No charts were generated by quickchart')
  return chart_sections


def find_charts_json(df_name: str, max_chart_instances=None):
  """Equivalent to find_charts, but emits to JSON for use from browser."""

  class FixedDataframeRegistry:

    def get_or_register_varname(self, _) -> str:
      """Returns the name of the fixed dataframe name."""
      return df_name

  dataframe = IPython.get_ipython().user_ns[df_name]

  chart_sections = determine_charts(
      dataframe, FixedDataframeRegistry(), max_chart_instances
  )
  return IPython.display.JSON([s.to_json() for s in chart_sections])


def determine_charts(df, dataframe_registry, max_chart_instances=None):
  """Finds charts compatible with dtypes of the given data frame."""
  # Lazy import to avoid loading matplotlib and transitive deps on kernel init.
  from google.colab import _quickchart_helpers  # pylint: disable=g-import-not-at-top

  dtype_groups = _classify_dtypes(df)
  numeric_cols = dtype_groups['numeric']
  categorical_cols = dtype_groups['categorical']
  time_cols = dtype_groups['datetime'] + dtype_groups['timelike']
  chart_sections = []

  if numeric_cols:
    section = _quickchart_helpers.histograms_section(
        df, numeric_cols[:max_chart_instances], dataframe_registry
    )
    if section.charts:
      chart_sections.append(section)

  if categorical_cols:
    selected_categorical_cols = categorical_cols[:max_chart_instances]
    section = _quickchart_helpers.categorical_histograms_section(
        df, selected_categorical_cols, dataframe_registry
    )
    if section.charts:
      chart_sections.append(section)

  if len(numeric_cols) >= 2:
    section = _quickchart_helpers.scatter_section(
        df,
        _select_first_k_pairs(numeric_cols, k=max_chart_instances),
        dataframe_registry,
    )
    if section.charts:
      chart_sections.append(section)

  if time_cols:
    section = _quickchart_helpers.time_series_line_plots_section(
        df,
        _select_time_series_cols(
            time_cols=time_cols,
            numeric_cols=numeric_cols,
            categorical_cols=categorical_cols,
            k=max_chart_instances,
        ),
        dataframe_registry,
    )
    if section.charts:
      chart_sections.append(section)

  if numeric_cols:
    section = _quickchart_helpers.value_plots_section(
        df, numeric_cols[:max_chart_instances], dataframe_registry
    )
    if section.charts:
      chart_sections.append(section)

  if len(categorical_cols) >= 2:
    section = _quickchart_helpers.heatmaps_section(
        df,
        _select_first_k_pairs(categorical_cols, k=max_chart_instances),
        dataframe_registry,
    )
    if section.charts:
      chart_sections.append(section)

  if categorical_cols and numeric_cols:
    section = _quickchart_helpers.faceted_distributions_section(
        df,
        _select_faceted_numeric_cols(
            numeric_cols, categorical_cols, k=max_chart_instances
        ),
        dataframe_registry,
    )
    if section.charts:
      chart_sections.append(section)

  return chart_sections


def _select_first_k_pairs(colnames, k=None):
  """Selects the first k pairs of column names, sequentially.

  e.g., ['a', 'b', 'c'] => [('a', b'), ('b', 'c')] for k=2

  Args:
    colnames: (iterable<str>) Column names from which to generate pairs.
    k: (int) The number of column pairs.

  Returns:
    (list<(str, str)>) A k-length sequence of column name pairs.
  """
  return itertools.islice(itertools.pairwise(colnames), k)


def _select_faceted_numeric_cols(numeric_cols, categorical_cols, k=None):
  """Selects numeric columns and corresponding categorical facets.

  Args:
    numeric_cols: (iterable<str>) Available numeric columns.
    categorical_cols: (iterable<str>) Available categorical columns.
    k: (int) The number of column pairs to select.

  Returns:
    (iter<(str, str)>) Prioritized sequence of (numeric, categorical) column
    pairs.
  """
  return itertools.islice(itertools.product(numeric_cols, categorical_cols), k)


def _select_time_series_cols(time_cols, numeric_cols, categorical_cols, k=None):
  """Selects combinations of colnames that can be plotted as time series.

  Args:
    time_cols: (iter<str>) Available time-like columns.
    numeric_cols: (iter<str>) Available numeric columns.
    categorical_cols: (iter<str>) Available categorical columns.
    k: (int) The number of combinations to select.

  Returns:
    (iter<(str, str, str)>) Prioritized sequence of (time, value, series)
    colname combinations.
  """
  numeric_cols = [c for c in numeric_cols if c not in time_cols]
  numeric_aggregates = ['count()']
  if not categorical_cols:
    categorical_cols = [None]
  return itertools.islice(
      itertools.product(
          time_cols, numeric_cols + numeric_aggregates, categorical_cols
      ),
      k,
  )


def _classify_dtypes(
    df,
    categorical_dtypes=_CATEGORICAL_DTYPES,
    datetime_dtypes=_DATETIME_DTYPES,
    datetime_dtype_kinds=_DATETIME_DTYPE_KINDS,
    categorical_size_threshold=_CATEGORICAL_LARGE_SIZE_THRESHOLD,
):
  """Classifies each dataframe series into a datatype group.

  Args:
    df: (pd.DataFrame) A dataframe.
    categorical_dtypes: (iterable<str>) Categorical data types.
    datetime_dtypes: (iterable<str>) Datetime data types.
    datetime_dtype_kinds: (iterable<str>) Datetime dtype.kind values.
    categorical_size_threshold: (int) The max number of unique values for a
      given categorical to be considered "small".

  Returns:
    ({str: list<str>}) A dict mapping a dtype name to the corresponding
    column names.
  """
  # Lazy import to avoid loading pandas and transitive deps on kernel init.
  import pandas as pd  # pylint: disable=g-import-not-at-top
  from pandas.api.types import is_numeric_dtype  # pylint: disable=g-import-not-at-top

  dtypes = (
      pd.DataFrame(df.dtypes, columns=['colname_dtype'])
      .reset_index()
      .rename(columns={'index': 'colname'})
  )

  filtered_cols = []
  numeric_cols = []
  cat_cols = []
  datetime_cols = []
  timelike_cols = []
  singleton_cols = []
  for colname, colname_dtype in zip(dtypes.colname, dtypes.colname_dtype):
    if not all(df[colname].apply(pd.api.types.is_hashable)):
      filtered_cols.append(colname)
    elif len(df[colname].unique()) <= 1:
      singleton_cols.append(colname)
    elif colname_dtype in categorical_dtypes:
      cat_cols.append(colname)
    elif (colname_dtype in datetime_dtypes) or (
        colname_dtype.kind in datetime_dtype_kinds
    ):
      datetime_cols.append(colname)
    elif is_numeric_dtype(colname_dtype):
      numeric_cols.append(colname)
    else:
      filtered_cols.append(colname)
  if filtered_cols:
    logging.warning(
        'Quickchart encountered unexpected dtypes in columns: "%r"',
        (filtered_cols,),
    )

  small_cat_cols, large_cat_cols = [], []
  for colname in cat_cols:
    if len(df[colname].unique()) <= categorical_size_threshold:
      small_cat_cols.append(colname)
    else:
      large_cat_cols.append(colname)

  def _matches_datetime_pattern(colname):
    colname = str(colname).lower()
    return any(
        colname.startswith(p) or colname.endswith(p)
        for p in _DATETIME_COLNAME_PATTERNS
    ) or any(colname == c for c in _DATETIME_COLNAMES)

  for colname in df.columns:
    if (
        _matches_datetime_pattern(colname)
        or _is_monotonically_increasing_numeric(df[colname])
    ) and _all_values_scalar(df[colname]):
      timelike_cols.append(colname)

  return {
      'numeric': numeric_cols,
      'categorical': small_cat_cols,
      'large_categorical': large_cat_cols,
      'datetime': datetime_cols,
      'timelike': timelike_cols,
      'singleton': singleton_cols,
      'filtered': filtered_cols,
  }


def _is_monotonically_increasing_numeric(series):
  # Pandas extension dtypes do not extend numpy's dtype and will fail if passed
  # into issubdtype.
  if not isinstance(series.dtype, np.dtype):
    return False
  return np.issubdtype(series.dtype.base, np.number) and np.all(
      np.array(series)[:-1] <= np.array(series)[1:]
  )


def _all_values_scalar(series):
  def _is_non_scalar(x):
    return isinstance(x, collections.abc.Iterable) and not isinstance(
        x, (bytes, str)
    )

  return not any(_is_non_scalar(x) for x in series)


def _get_axis_bounds(series, padding_percent=0.05, zero_rtol=1e-3):
  """Gets the min/max axis bounds for a given data series.

  Args:
    series: (pd.Series) A data series.
    padding_percent: (float) The amount of padding to add to the minimal domain
      extent as a percentage of the domain size.
    zero_rtol: (float) If either min or max bound is within this relative
      tolerance to zero, don't add padding for aesthetics.

  Returns:
    (<float> min_bound, <float> max_bound)
  """
  min_bound, max_bound = series.min(), series.max()
  padding = (max_bound - min_bound) * padding_percent
  if not np.allclose(0, min_bound, rtol=zero_rtol):
    min_bound -= padding
  if not np.allclose(0, max_bound, rtol=zero_rtol):
    max_bound += padding
  return min_bound, max_bound
