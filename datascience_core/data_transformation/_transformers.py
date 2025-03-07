from ._base import IDataFrameTransformer, IDataFrameCaster
import pandas as pd
import copy
from pandas.api.types import is_datetime64_any_dtype as is_datetime
import logging
from datetime import datetime
import numpy as np
from typing import List, Any, Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def is_data_size_small(data_object: Union[pd.DataFrame, pd.Series]) -> bool:
    """
    Checks if the size of the data is smaller than 100million and returns a boolean

    Args:
        data_object (pd.DataFrame): Dataframe to check the size of
    returns:
        bool: True if the size less than 100,000,000, False otherwise

    Example:
        is_data_size_small(pd.DataFrame({'col1': [1, 2, 3], 'col2': [1, 2, 3]}))
        >>> True
        is_data_size_small(pd.DataFrame(np.random.randint(0,100,size=(110000, 1000)), columns=list(range(1000))))
        >>> False

    """

    return True if data_object.size < 100000000 else False


class PreprocessingError(Exception):
    """
    Error raised if there is an issue during an IDataTransformer process step
    """

    def __init__(
            self, step_name: str = "preprocessing", message: str = "preprocessing error"
    ):
        """Instantiates a preprocessing error, based on the step that it occurred and the error message

        Args:
            step_name (str, optional): Name of the step currently being applied. Defaults to "preprocessing".
            message (str, optional): Error message to raise. Defaults to "preprocessing error".
        """
        self.stepName = step_name
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format the error as a string

        Returns:
            str: Error message
        """
        return "{}: {}".format(self.stepName, self.message)


class ColumnRenamer(IDataFrameTransformer):
    """
    Accepts a dataframe and a dictionary of columns to rename.  Returns a dataframe with the columns
    renamed

    Typical usage example:
    ```python
    from datascience_core.data_transformation import ColumnRenamer

    input_df = pd.DataFrame({'col1': [1, 2, 3], 'col2': [1, 2, 3]})
    input_mapper_dict = {'col1':'colB'}
    col_renamer = ColumnRenamer(name_mapping=input_mapper_dict)
    renamed_df = col_renamer.process(input_df)
    ```
    """

    def __init__(self, name_mapping: dict):
        """Instantiate a ColumnRenamer

        Args:
            name_mapping (dict): Dictionary where the keys are the current column names and the values are the names that the keys should be renamed to

        Raises:
            TypeError: Raised if name_mapping is not a dictionary
        """
        logger.debug("Creating a ColumnRenamer")
        if not isinstance(name_mapping, dict):
            raise TypeError

        self.name_mapping = name_mapping

        super().__init__()

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply the Renaming transformation

        Args:
            data (pd.DataFrame): Pandas dataframe with columns to rename

        Returns:
            pd.DataFrame: New dataframe with renamed columns
        """
        logger.debug(f"Renaming {len(self.name_mapping.keys())} columns")
        return data.rename(columns=self.name_mapping)


class ColumnDotRenamer(IDataFrameTransformer):
    """
    Renames columns with a format 'App.Gender' to 'App Gender'
    """

    def __init__(self, fmt="speedy", from_name=".", to_name=" "):
        self.fmt = fmt
        self.from_name = from_name
        self.to_name = to_name

    def process(self, dfIn):
        if self.fmt == "speedy":
            dfOut = dfIn.rename(
                {col: col.replace(self.from_name, self.to_name) for col in dfIn.index}
            )
        elif self.fmt == "flat":
            dfOut = dfIn.rename(
                {
                    col: col.replace(self.from_name, self.to_name)
                    for col in dfIn.columns
                },
                axis=1,
            )
        return dfOut


class DataFrameTimeSlicer(IDataFrameTransformer):
    """
    Accepts a dataframe with a datetime column, a min time and max time.  The class with slice the dataframe and return
    a new dataframe in the date range

    Typical usage example:
    ```python
    from datascinece_core.data_transformation import DataFrameTimeSlicer

    input_df = pd.DataFrame({'date': [date1, date2, date3], 'col2': [1, 2, 3]})

    start_time = datetime.strptime('2022-01-01', '%Y-%m-%d')
    end_time = datetime.strptime('2022-02-01', '%Y-%m-%d')
    date_col = 'date'

    col_slicer = DataFrameTimeSlicer(date_col, start_time, end_time)
    sliced_df = col_slicer.process(input_data)
    ```

    """

    # date range inclusive (>=, <=)
    def __init__(
            self,
            col_name_for_time: str,
            min_time: datetime,
            max_time: datetime,
            convert_to_datetime_format: str = "",
    ):
        """Instantiate a DataFrameTimeSlicer

        Args:
            col_name_for_time (str): The column name that contains the timestamp to use for slicing
            min_time (datetime): The minimum time for rows to pass through the filter
            max_time (datetime): The maximum time for rows to pass throught the filter
            convert_to_datetime_format (bool, optional): If set, use this format string to convert the col_name_for_time column into a datetime dtype.

        Raises:
            ValueError: Raised if the time ranges are not datetime objects
        """
        self.col_name_for_time = col_name_for_time
        if not isinstance(min_time, datetime):
            raise ValueError("Argument min_time must be a datetime object")
        if not isinstance(max_time, datetime):
            raise ValueError("Argument max_time must be a datetime object")
        self.convert_to_datetime_format = convert_to_datetime_format
        self.min_time = min_time
        self.max_time = max_time
        logger.debug(
            f"Creating a DataFrameTimeSlicer on column {col_name_for_time} between {self.min_time} and {self.max_time}"
        )

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply the time slicing transformer

        Args:
            data (pd.DataFrame): Data to be sliced

        Returns:
            pd.DataFrame: Time Sliced dataframe
        """
        if self.convert_to_datetime_format:
            logger.debug(f"Converting to datetime")
            data[self.col_name_for_time] = pd.to_datetime(
                data[self.col_name_for_time], format=self.convert_to_datetime_format
            )
            logger.debug(
                f"After conversion the dtype of the column is: {data[self.col_name_for_time].dtype}"
            )
            logger.debug(
                f"THe month of the first date in the data is {pd.DatetimeIndex(data[self.col_name_for_time]).month}"
            )
        logger.debug("DataFrameTimeSlicer is procesing")

        data_max_date = data[self.col_name_for_time].max()
        data_min_date = data[self.col_name_for_time].min()
        logger.debug(f"The max date in the data is {data_max_date}")
        logger.debug(f"The min date in the data is {data_min_date}")
        if self.max_time > data_max_date:
            logger.warn(
                "Input maximum date is greater than the maximum date within the dataframe"
            )
        if self.min_time < data_min_date:
            logger.warn(
                "Input minimum date is less than the minimum date within the dataframe"
            )
        logger.debug(f"The data at this point is {data}")
        return data[
            (data[self.col_name_for_time] >= self.min_time)
            & (data[self.col_name_for_time] <= self.max_time)
            ]


class DataFrameCaster(IDataFrameCaster):
    """
    Casts the input dataframe into the target_schema.  The function will not handle an incorrectly formatted
    schema.  Any deviation from the expected format will throw an error.  Use schema validator to ensure the
    data is compatible before using the DataFrame Caster

    The schema must be in the format:

    {
        "col1": {
            "description": "Description of code",
            "unique_categories": [],
            "is_date": true,
            "min_val": "NaN",
            "max_val": "NaN",
            "dtype": "datetime64[ns]"
        },
    }

    Schemas are stored in the shemas folder in the data_transformation module. See there for a schema guide.

    Typical usage examle:
    ```python
    from datascience_core.data_transformation import DataFrameCaster

    input_df = pd.DataFrame({'col1': [date1, date2, date3]})
    with open(os.path.join(test_path,"example_schema.json"),'r') as schema_file:
        return json.load(schema_file)
    caster = DataFrameCaster(target_schema=schema)
    casted_df = caster.process(input_df)
    ```

    """

    def __init__(self, target_schema: dict):
        """Create a DataFrameCaster instance

        Args:
            target_schema (dict): Schema to cast to during the process function
        """
        logger.debug("Creating a DataFrameCaster")
        self.target_schema = target_schema

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply the cast to the input dataframe and return a new dataframe with the specified dtypes

        Args:
            data (pd.DataFrame): Input dataframe

        Returns:
            pd.DataFrame: Caster dataframe
        """
        logger.debug("Casting to the target schema")
        new_schema = {key: val["dtype"] for key, val in self.target_schema.items()}
        data = data.astype(new_schema, errors="ignore")
        return data


# For the analyser
class TierMapper(IDataFrameTransformer):
    """
    Maps the scorecard output into tiers using boundaries provided (using the map_score function).
    Also can remap from one set of boundaries to another (using the process function)

    Typical usage example:
    ```python
    from datascience_core.data_transformation import TierMapper

    existing_tier_dict = {
        'Tier1': 0.19,
        'Tier2': 0.26,
        'Tier3': 0.32,
        'Tier4': 0.43,
        'Tier5': 0.48,
        'Tier6': 0.52
        }
    new_tier_dict = {
        'Tier1': 0.19,
        'Tier2': 0.26,
        'Tier3': 0.32,
        'Tier4': 0.43,
        'Tier5': 0.48,
        'Tier6': 0.52
        }
    tier_mapper = TierMapper(existing_tier_dict,new_tier_dict)

    previous_score = 0.15
    new_score = tier_mapper.process(previous_score)
    ```
    """

    def __init__(self, previous_tier_boundaries: dict, new_tier_boundaries: dict):
        """Instantiates a new TierMapper

        Args:
            previous_tier_boundaries (dict): Current tier boundaries
            new_tier_boundaries (dict): New tier boundaries to map to in the process function
        """
        self.previous_tier_boundaries = previous_tier_boundaries
        self.new_tier_boundaries = new_tier_boundaries
        super().__init__()

    def _unmap_score(self, AD_score: float, raw_score_boundaries_dict: dict) -> float:
        """
        converts a score back to the raw score

        Args:
            AD_score (float): Score to unmap to a raw score
            raw_score_boundaries_dict (dict): Score boundaries to remove from score
        Returns:
            Ad_score (float): Unmapped AD score
        """

        raw_score_boundaries_dict["Tier7"] = 1.0

        fixed_boundaries = {
            "Tier1": 0.25,
            "Tier2": 0.4,
            "Tier3": 0.5,
            "Tier4": 0.6,
            "Tier5": 0.65,
            "Tier6": 0.75,
            "Tier7": 1.0,
        }
        t1 = raw_score_boundaries_dict["Tier1"]
        t2 = raw_score_boundaries_dict["Tier2"]
        t3 = raw_score_boundaries_dict["Tier3"]
        t4 = raw_score_boundaries_dict["Tier4"]
        t5 = raw_score_boundaries_dict["Tier5"]
        t6 = raw_score_boundaries_dict["Tier6"]
        t7 = raw_score_boundaries_dict["Tier7"]

        if AD_score <= fixed_boundaries["Tier1"]:
            return (AD_score / fixed_boundaries["Tier1"]) * raw_score_boundaries_dict[
                "Tier1"
            ]

        if AD_score <= fixed_boundaries["Tier2"]:
            return (AD_score - fixed_boundaries["Tier1"]) / (
                    fixed_boundaries["Tier2"] - fixed_boundaries["Tier1"]
            ) * (
                    raw_score_boundaries_dict["Tier2"] - raw_score_boundaries_dict["Tier1"]
            ) + raw_score_boundaries_dict[
                "Tier1"
            ]
        if AD_score <= fixed_boundaries["Tier3"]:
            return (AD_score - fixed_boundaries["Tier2"]) / (
                    fixed_boundaries["Tier3"] - fixed_boundaries["Tier2"]
            ) * (
                    raw_score_boundaries_dict["Tier3"] - raw_score_boundaries_dict["Tier2"]
            ) + raw_score_boundaries_dict[
                "Tier2"
            ]

        if AD_score <= fixed_boundaries["Tier4"]:
            return (AD_score - fixed_boundaries["Tier3"]) / (
                    fixed_boundaries["Tier4"] - fixed_boundaries["Tier3"]
            ) * (
                    raw_score_boundaries_dict["Tier4"] - raw_score_boundaries_dict["Tier3"]
            ) + raw_score_boundaries_dict[
                "Tier3"
            ]
        if AD_score <= fixed_boundaries["Tier5"]:
            return (AD_score - fixed_boundaries["Tier4"]) / (
                    fixed_boundaries["Tier5"] - fixed_boundaries["Tier4"]
            ) * (
                    raw_score_boundaries_dict["Tier5"] - raw_score_boundaries_dict["Tier4"]
            ) + raw_score_boundaries_dict[
                "Tier4"
            ]
        if AD_score <= fixed_boundaries["Tier6"]:
            return (AD_score - fixed_boundaries["Tier5"]) / (
                    fixed_boundaries["Tier6"] - fixed_boundaries["Tier5"]
            ) * (
                    raw_score_boundaries_dict["Tier6"] - raw_score_boundaries_dict["Tier5"]
            ) + raw_score_boundaries_dict[
                "Tier5"
            ]

        if AD_score <= fixed_boundaries["Tier7"]:
            return (AD_score - fixed_boundaries["Tier6"]) / (
                    fixed_boundaries["Tier7"] - fixed_boundaries["Tier6"]
            ) * (
                    raw_score_boundaries_dict["Tier7"] - raw_score_boundaries_dict["Tier6"]
            ) + raw_score_boundaries_dict[
                "Tier6"
            ]

        return AD_score

    @classmethod
    def map_score(cls, AD_raw_score: float, raw_boundaries: dict) -> float:
        """
        maps an AD_score to new boundaries

        Args:
            AD_raw_score (float): Raw score to map using raw_boundaries
            raw_boundaries (dict): Boundaries to map scores to
        Returns:
            AD_raw_score (float): Mapped raw_score
        """

        raw_boundaries["Tier7"] = 1.0

        fixed_boundaries = {
            "Tier1": 0.25,
            "Tier2": 0.4,
            "Tier3": 0.5,
            "Tier4": 0.6,
            "Tier5": 0.65,
            "Tier6": 0.75,
        }

        t1 = raw_boundaries["Tier1"]
        t2 = raw_boundaries["Tier2"]
        t3 = raw_boundaries["Tier3"]
        t4 = raw_boundaries["Tier4"]
        t5 = raw_boundaries["Tier5"]
        t6 = raw_boundaries["Tier6"]

        if AD_raw_score <= t1:
            return AD_raw_score / t1 * fixed_boundaries["Tier1"]
        elif AD_raw_score <= t2:
            return (AD_raw_score - t1) / (t2 - t1) * (
                    fixed_boundaries["Tier2"] - fixed_boundaries["Tier1"]
            ) + fixed_boundaries["Tier1"]

        elif AD_raw_score <= t3:
            return (AD_raw_score - t2) / (t3 - t2) * (
                    fixed_boundaries["Tier3"] - fixed_boundaries["Tier2"]
            ) + fixed_boundaries["Tier2"]

        elif AD_raw_score <= t4:
            return (AD_raw_score - t3) / (t4 - t3) * (
                    fixed_boundaries["Tier4"] - fixed_boundaries["Tier3"]
            ) + fixed_boundaries["Tier3"]

        elif AD_raw_score <= t5:
            return (AD_raw_score - t4) / (t5 - t4) * (
                    fixed_boundaries["Tier5"] - fixed_boundaries["Tier4"]
            ) + fixed_boundaries["Tier4"]

        elif AD_raw_score <= t6:
            return (AD_raw_score - t5) / (t6 - t5) * (
                    fixed_boundaries["Tier6"] - fixed_boundaries["Tier5"]
            ) + fixed_boundaries["Tier5"]

        else:
            return (AD_raw_score - t6) / (1 - t6) * (
                    1 - fixed_boundaries["Tier6"]
            ) + fixed_boundaries["Tier6"]

    def process(
            self,
            AD_score: float,
    ) -> float:
        """
        Remaps AD_score from old boundaries to new boundaries
        Args:
            AD_score (float): Current mapped score
        Returns:
            AD_score (float): Remapped score
        """
        score = self._unmap_score(AD_score, self.previous_tier_boundaries)
        return self.map_score(score, self.new_tier_boundaries)

    @classmethod
    def score_to_tier(cls, score: float, tier_boundaries: dict) -> str:
        """Based on the provided boundaries, assign a tier to the given scorecard score

        Args:
            score (float): Score to assign tier to
            tier_boundaries (dict): Tier boundaries to use

        Raises:
            ValueError: Raised if the score or tier boundaries are not between 0 and 1

        Returns:
            str: Tier allocated. Names given by the keys of tier_boundaries input
        """
        tier_boundaries = {
            k: v for k, v in sorted(tier_boundaries.items(), key=lambda item: item[1])
        }
        tier_names = list(tier_boundaries.keys())
        limits = list(tier_boundaries.values())
        tier_names.append("Tier7")
        limits.insert(0, 0.0)
        limits.append(1.0)
        for i in range(len(tier_names)):
            if score <= limits[i + 1] and score > limits[i]:
                return tier_names[i]
        raise ValueError("Score input and tier boundaries must be between 0 and 1")


class InvalidPayloadDropperByPrefix(IDataFrameTransformer):
    """
    Drops rows where there are NaN values in a subset of columns that begin with the prefix's provided
    Example Use Case:
    ```python
    from datascience_core.data_transformation import InvalidPayloadDropperByPrefix

    prefixes = ['App']

    input_df = pd.DataFrame({
        'App.Name': ['John', NaN, 'Alice'],
        'App.Profession': ['Carpenter', 'Sleigh Driver', NaN],
        'QCB.CreditScore': [NaN, 100, 100]
    })

    prefix_dropper = InvalidPayloadDropperByPrefix(prefixes)
    output_df = prefix_dropper.process(input_df)
    # Output will only have one row (John) as the other two rows have NaN values in a column beginning with 'App'
    ```
    """

    def __init__(self, column_Prefixes: list):
        """Instantiate the payload dropper

        Args:
            column_Prefixes (list): Column prefixex used for selecting columns to drop NaN values by
        """
        self.column_Prefixes = column_Prefixes

    def process(self, cra_data: pd.DataFrame) -> pd.DataFrame:
        data_to_transform = (
            cra_data.copy(deep=True) if is_data_size_small(cra_data) else cra_data
        )
        if not is_data_size_small(cra_data):
            print(
                "Data is too large to copy. Transformation is being applied to the passed dataset directly"
            )

        logger.info(
            f"dropping invalid payload by checking columns with prefixes {self.column_Prefixes}"
        )
        field_prefixes = self.column_Prefixes
        for prefix in field_prefixes:
            column_names_with_this_prefix = [
                col for col in cra_data.columns if prefix in col
            ]
            data_to_transform.dropna(
                how="all", subset=column_names_with_this_prefix, inplace=True
            )
        return data_to_transform


class ValueReplacer(IDataFrameTransformer):
    """
    Replaces values with NaN that are either missing data, mistakes or outliers in the credit-check payloads
    Example Use Case:
    ```python
    from datascience_core.data_transformation import ValueReplacer

    value_replacer = ValueReplacer(unwanted_values=['bad_value_1', 'bad_value_2'], replacement_value=0)

    input_df = pd.DataFrame({'col_name': ['bad_value_2', 1, 2, 3, 'bad_value_1']})
    output_df = value_replacer.process(input_df)
    ```
    """

    def __init__(
            self,
            unwanted_values: List = [
                "M",
                "C",
                "{ND}",
                "ND",
                "OB",
                "Not Found",
                "{OB}",
                "T",
                "__",
                -999997,
                -999999,
                999999,
                999997,
                -999997.0,
                -999999.0,
                999999.0,
                999997.0,
                "-999997",
                "-999999",
                "999999",
                "999997",
                "-999997.0",
                "-999999.0",
                "999999.0",
                "999997.0",
            ],
            replacement_value: Any = np.nan,
    ):
        """Instantiate the ValueReplacer

        Args:
            unwanted_values (List, optional): Values to replace. Defaults to [ "M", "C", "{ND}", "ND", "OB", "Not Found", "{OB}", "T", "__", -999997, -999999, 999999, 999997, -999997.0, -999999.0, 999999.0, 999997.0, "-999997", "-999999", "999999", "999997", "-999997.0", "-999999.0", "999999.0", "999997.0", ].
            replacement_value (Any, optional): Value to replace with. Defaults to np.nan.
        """
        self.unwanted_values = unwanted_values
        self.replacement_value = replacement_value

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply the value replacer, replacing the unwanted values with NaN in the entire dataframe

        Args:
            data (pd.DataFrame): DataFrame to replace values in

        Raises:
            PreprocessingError: Raised if there is any issue during processing

        Returns:
            pd.DataFrame: Dataframe with values replaced
        """
        try:
            return data.replace(self.unwanted_values, self.replacement_value)
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)


class DominatedColumnDropper(IDataFrameTransformer):
    """
    Drops columns based on a dominance threshold. For instance if the threshold is 0.6 then columns with more than 60% of the vales that are the same are dropped.
    Example Use Case:
    ```python
    from datascience_core.data_transformation import DominatedColumnDropper

    dom_threshold = 0.6
    ignore_cols = ['ignore_this']

    dom_col_dropper = DominatedColumnDropper(dominance_threshold=dom_threshold, ignore_cols=ignore_cols)

    input_df = pd.DataFrame({
        'above_thresh': [1, 1, 1, 2],
        'below_thresh': [1, 1, 2, 2],
        'ignore_this': [1, 1, 1, 1]
    })
    output_df = dom_col_dropper.process(input_df)
    # Output DF will only drop the 'above thresh' column, as more than 60% of the values are the same (1)
    ```
    """

    def __init__(self, dominance_threshold: float = 0.99, ignore_cols: List[str] = []):
        """Instantiate the column dropper

        Args:
            dominance_threshold (float, optional): Threshold to drop columns if the dominance is higher than it. Defaults to 0.99.
            ignore_cols (List[str], optional): Any columns to exclude from the dominance check. Defaults to [].
        """
        self.dominance_threshold = dominance_threshold
        self.ignore_cols = ignore_cols

    def process(self, data: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
        """Apply the column dropper and retun a dataframe without domicated columns

        Args:
            data (pd.DataFrame): Dataframe to apply dominance threshold to
            verbose (bool): If true, enable additional logging, with print statements

        Raises:
            PreprocessingError: Raised if there is any error raised during the processing

        Returns:
            pd.DataFrame: Pandas dataframe with columns dropped that are above the dominance threshold
        """
        try:
            df_out = copy.deepcopy(data)
            if verbose:
                print("start to remove the columns with the identical values...")
            cols_to_check = [x for x in df_out.columns if x not in self.ignore_cols]
            col_to_remove = []
            for col in cols_to_check:
                nan_sum = df_out[col].isna().sum()
                if nan_sum / df_out.shape[0] >= self.dominance_threshold:
                    col_to_remove.append(col)
                    continue
                if (
                        df_out[col].value_counts().iloc[0] / df_out.shape[0]
                        >= self.dominance_threshold
                ):
                    col_to_remove.append(col)

            if verbose:
                print(
                    """total number of columns in the input data frame is {}
                number of columns to be removed is {}
                number of remaining columns is {}""".format(
                        data.shape[1],
                        len(col_to_remove),
                        data.shape[1] - len(col_to_remove),
                    )
                )
            df_out.drop(col_to_remove, axis=1, inplace=True)
            if verbose:
                print("finished removing columns that have only one value")
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)
        return df_out


class CatTypeConverter(IDataFrameTransformer):
    """
    Converts the type of specified columns to category and the rest to numeric.
    This worked for speedy card (one column dataframe) and normal card
    Example Use Case:
    ```python
    from datascience_core.data_transformation import CatTypeConverter

    categorical_columns = ['shape', 'color']
    cat_converter = CatTypeConverter(categorical_columns)

    input_df = pd.DataFrame({
        'shape': ['square', 'circle', 'oval'],
        'color': ['brown', 'brown', 'white'],
        'size': ['5', '5', '6']
    })
    output_df = cat_converter.process(input_df)
    # output_df will have categorical dtypes for 'shape' and 'color' and 'size' will be converted into float type
    ```

    """

    def __init__(self, cat_col_names: List[str] = [], date_col_names: List[str] = []):
        """Instantiate a CatTypeConverter

        Args:
            cat_col_names (List[str], optional): the column names to be converted to category type. Defaults to [].
            date_col_names (List[str], optional): The names of the date columns (and not to convert)
        """
        self.cat_col_names = cat_col_names
        self.date_col_names = date_col_names

    def process(
            self, df: pd.DataFrame, verbose: bool = False, create_copy=False
    ) -> pd.DataFrame:
        """Apply the column conversion returning a new dataframe

        Args:
            df (pd.DataFrame): input dataframe to convert to categorical type
            verbose (bool, optional): Enable additional logging if enabled. Defaults to False.
            create_copy (bool, optional): If true, return a copy of the dataframe. Defaults to False.

        Raises:
            PreprocessingError: Raised if there is any issue during applying the processing

        Returns:
            pd.DataFrame: Converted dataframe

        """
        try:
            if create_copy:
                if not is_data_size_small(df):
                    print(
                        "Data Size is too large to copy. Applying transformation on original dataframe"
                    )
                    df_out = df
                else:
                    df_out = copy.deepcopy(df)
            else:
                df_out = df

            # We still want the function to complete in the case when no categorical columns are passed.
            if len(self.cat_col_names) == 0:
                if "0" in df_out.columns:
                    df_out["0"] = pd.to_numeric(df_out["0"], errors="coerce")
                else:
                    df_out = df_out.apply(pd.to_numeric, errors="coerce")
                return df_out

            if set(self.cat_col_names).issubset(set(df_out.index)):
                df_cat = copy.deepcopy(df_out.loc[self.cat_col_names])
                df_cat.fillna("NaN", inplace=True)
                df_cat["0"] = df_cat["0"].astype("str")
                df_cat["0"] = df_cat["0"].astype("category")

                df_dates = df_out.loc[self.date_col_names]

                df_out.drop(self.cat_col_names, inplace=True)
                df_out.drop(self.date_col_names, inplace=True)

                df_out["0"] = pd.to_numeric(df_out["0"], errors="coerce")

                df_out = pd.concat([df_out.T, df_cat.T, df_dates.T], axis=1)

                if verbose:
                    print(
                        "{} out of {} features changed to category type and other {} to numeric".format(
                            len(df_cat.index), len(df.index), len(df_out.index)
                        )
                    )
            elif set(self.cat_col_names).issubset(set(df_out.columns)):
                df_cat = copy.deepcopy(df_out[self.cat_col_names])
                df_cat.fillna("NaN", inplace=True)
                df_cat = df_cat.astype("str")
                df_cat = df_cat.astype("category")
                df_out.drop(columns=self.cat_col_names, inplace=True)
                numeric_cols = [
                    col for col in df_out.columns if col not in self.date_col_names
                ]
                df_out[numeric_cols] = df_out[numeric_cols].apply(
                    lambda x: pd.to_numeric(x, errors="coerce")
                    if x.name not in self.cat_col_names
                    else x
                )
                df_out = pd.concat([df_out, df_cat], axis=1)
                if verbose:
                    print(
                        "{} out of {} features changed to category type and other {} to numeric".format(
                            len(df_cat.columns), len(df.columns), len(df_out.columns)
                        )
                    )
            else:
                msg = "some of the requested feature names are not included in the dataframe"
                raise PreprocessingError(type(self).__name__, msg)
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)
        return df_out


class SimpleCatTypeConverter(IDataFrameTransformer):

    """
    Takes a list of column names and converts those in a dataframe to a category type.
    Date columns are not converted to a different type.
    All other columns are converted to a numeric type.
    If a categorical column is missed, its values will be converted to Nans.

    Args:
        categorical_columns (List[str]): The names of the columns to convert to category type
        date_columns (List[str]): The names of the date columns (and not to convert)

    Returns:
        pd.DataFrame: Converted dataframe

    """

    def __init__(self, categorical_columns: List[str], date_columns: List[str] = []):
        self.categorical_columns = categorical_columns
        self.date_columns = date_columns

    def process(self, df: pd.DataFrame):
        df[self.categorical_columns] = df[self.categorical_columns].astype("category")
        non_categorical_columns = list(set(df.columns) - set(self.categorical_columns) - set(self.date_columns))
        df[non_categorical_columns] = df[non_categorical_columns].apply(pd.to_numeric, errors="coerce")  # noqa: E501
        return df


class GranularColumnDropper(IDataFrameTransformer):
    """Drops columns that have to many categorical values above a threshold.
    Example Use Case:
    ```python

    from datascience_core.data_transformation import GranularColumnDropper

    granular_dropper = GranularColumnDropper(threshold=0.6, list_of_cols=['col1', 'col2'])
    input_df = pd.DataFrame({
        'col1': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'],
        'col2': ['a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a', 'a'],
        })
    output_df = granular_dropper.process(input_df)
    # output_df will have 'col1' dropped because it has more than 60% unique values
    # output_df will not have 'col2' dropped because it has less than 60% unique values
    ```
    """

    def __init__(self, threshold: float = 0.6, list_of_cols: List[str] = []):
        """transformer class to drop a column if the number of unique values in a column exceeds a threshold for total columns


        Args:
            threshold (float, optional): threshold for dropping. Defaults to 0.6.
            list_of_cols (List[str], optional): list of columns to evaluate. Defaults to [].
             If empty, all columns will be evaluated
        """
        self.threshold = threshold
        self.list_of_cols = list_of_cols

    def process(self, df: pd.DataFrame, create_copy=False) -> pd.DataFrame:
        """run function for the transformer.  Can be used by a datascience_core IDataFrameTransformer

        Args:
            df (pd.DataFrame): input data to process
            create_copy (bool, optional): if true, return a copy of the dataframe. Defaults to False.

        Raises:
            PreprocessingError: raises an error if the process fails

        Returns:
            pd.DataFrame: processed dataframe
        """

        try:
            if create_copy:
                if not is_data_size_small(df):
                    print(
                        "Data Size is too large to copy. Applying transformation on original dataframe"
                    )
                    df_copy = df
                else:
                    df_copy = copy.deepcopy(df)
            else:
                df_copy = df

            cols_to_drop = []

            if len(self.list_of_cols) > 0:
                columns_to_evaluate = list(
                    set(self.list_of_cols).intersection(set(df_copy.columns))
                )
                self.missing_column_warning(columns_to_evaluate)
            else:
                columns_to_evaluate = df_copy.columns

            for col in columns_to_evaluate:
                if len(df_copy[col].unique()) / df_copy.shape[0] > self.threshold:
                    cols_to_drop.append(col)

            return df_copy.drop(columns=cols_to_drop)
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)

    def missing_column_warning(self, columns_to_evaluate):
        if len(columns_to_evaluate) < len(self.list_of_cols):
            print("Some of the columns requested are not in the dataframe")
            logger.warn("Some of the columns requested are not in the dataframe")


class ColBasedQuantiler(IDataFrameTransformer):
    """
    Old class - Not currently in use
    Examples
    --------
    >>> dictQuantileColsTest = {'BSB FB': (0.1, 0.9)}
    >>> ColBasedQuantilerTest = ColBasedQuantiler()
    >>> ColBasedQuantilerTest.calc_thresholds_by_column(data_frame_test, dictQuantileColsTest)
    >>> ColBasedQuantilerTest.dict_quantile_thresholds = {'BSB FB': (2, 13.49999)}
    >>> dfQuantiled = ColBasedQuantilerTest.run_step(data_frame_test)
    """

    def __init__(self):
        self.dict_quantile_thresholds = {}

    def calc_thresholds_by_column(
            self, df: pd.DataFrame, quantile_cols: List[float]
    ) -> dict:
        """
        calculates the lower and upper values based on provided quantile and columns

        Parameters
        ----------
        df: dataframe to be processed. The dataframe must contain the given column names by quantile_cols
        quantile_cols: the dict that has column name as key and a tuple with quantile percentage values (lower, upper)

        Returns
        -------
        dict_quantile_thresholds: the dict with column name as key qand a tuple with calculated actual quantile thresholds

        """
        dict_quantile_thresholds = {}
        for col, quantiles in quantile_cols.items():
            lower = df[col].quantile(quantiles[0])
            upper = df[col].quantile(quantiles[1])
            dict_quantile_thresholds[col] = (lower, upper)
        self.dict_quantile_thresholds = dict_quantile_thresholds
        return dict_quantile_thresholds

    def process(self, df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
        try:
            df_out = df.copy(deep=True) if is_data_size_small(df) else df
            if not is_data_size_small(df):
                print(
                    "Data is too large to copy. Transformation is being applied to the passed dataset directly"
                )
            for col, tupQuantile in self.dict_quantile_thresholds.items():
                lower = self.dict_quantile_thresholds[col][0]
                upper = self.dict_quantile_thresholds[col][1]

                if verbose:
                    print("-" * 10 + "\n", col)
                    print("lower: {} to upper: {}".format(lower, upper))
                    print("before max", df_out[col].max())
                    print("before min", df_out[col].min())

                df_out.loc[df_out[df_out[col] < lower].index, col] = lower
                df_out.loc[df_out[df_out[col] > upper].index, col] = upper

                if verbose:
                    print("after max", df_out[col].max())
                    print("after min", df_out[col].min())
                    print("-" * 10 + "\n", col)
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)
        return df_out


class MissingColumnReplacer(IDataFrameTransformer):
    """
    Creates missing columns in a dataframe based on the expected columns. THen fill these columns by the fill_value
    """

    def __init__(self, expected_columns: List[str], fill_value: Any = np.nan):
        """Instantiate a missing column replacer

        Args:
            expected_columns (List[str]): Columns to create if missing
            fill_value (Any, optional): Value to fill missing columns with. Defaults to np.nan.
        """
        self.expected_columns = expected_columns
        self.fill_value = fill_value

    def process(self, df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
        """Apply the MissingColumnReplacer, filling missing columns with the fill_value

        Args:
            df (pd.DataFrame): Dataframe to apply the processing to
            verbose (bool, optional): Enable additional logging. Defaults to False.

        Raises:
            PreprocessingError: Raised if there are any issues during the transformation

        Returns:
            pd.DataFrame: Dataframe with additional columns containing the fill_value (if the columns are missing)
        """
        try:
            missing_cols = [x for x in self.expected_columns if x not in df.columns]
            df_out = df.copy(deep=True) if is_data_size_small(df) else df
            if not is_data_size_small(df):
                print(
                    "Data is too large to copy. Transformation is being applied to the passed dataset directly"
                )
            if len(missing_cols) > 0:
                for col in missing_cols:
                    df_out[col] = self.fill_value
        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)
        return df_out


class ColumnFiller(IDataFrameTransformer):
    """
    to modify the existing field values or add field values

    """

    def __init__(
            self,
            col_names,
            critical_features,
            fill_value=np.nan,
            enforce=False,
            fmt="speedy",
            logger=None,
    ):
        self.col_names = col_names
        self.critical_features = critical_features
        self.fill_value = fill_value
        self.enforce = enforce
        self.fmt = fmt
        self.logger = logger

    def process(self, df, verbose=False):
        """Apply the ColumnFiller, filling missing columns with the fill_value

        Args:
            df (pd.DataFrame): Dataframe to apply the processing to
            verbose (bool, optional): Enable additional logging. Defaults to False.

        Raises:
            PreprocessingError: Raised if there are specified columns missing from the output dataframe

        Returns:
            pd.DataFrame: Dataframe with additional columns containing the fill_value (if the columns are missing)


        """
        try:
            df_out = df.copy(deep=True) if is_data_size_small(df) else df
            if not is_data_size_small(df):
                print(
                    "Data is too large to copy. Transformation is being applied to the passed dataset directly"
                )

            if self.fmt == "speedy":
                missing_cols = [x for x in self.col_names if x not in df_out.index]
                for col in self.col_names:
                    if self.enforce or col not in df_out.index:
                        df_out.loc[col] = self.fill_value

            elif self.fmt == "flat":
                missing_cols = [x for x in self.col_names if x not in df_out.columns]
                for col in self.col_names:
                    if self.enforce or col not in df_out.columns:
                        df_out[col] = self.fill_value

            if self.logger is not None and bool(missing_cols):
                self.logger.addWarnings("missing_cols", missing_cols)

            critical_missing_cols = [
                x for x in missing_cols if x in self.critical_features
            ]
            if critical_missing_cols:
                raise PreprocessingError(
                    "column_filler",
                    "Missing Critical columns: {}".format(critical_missing_cols),
                )

        except Exception as err:
            raise PreprocessingError(type(self).__name__, err)
        return df_out


class LowerCaseTransformer(IDataFrameTransformer):
    """
    Converts all strings in the input dataframe into lowercase.

    #write a minumal working example where it converts a 3 row dataframe into lowercase
    Example:
        #>>> import pandas as pd
        #>>> from data_preprocessing import LowerCaseTransformer
        #>>> df = pd.DataFrame({'1': ['a', 'b', 'c'], '2': ['A', 'B', 'C']})
        #>>> transformer = LowerCaseTransformer(['1', '2'])
        #>>> transformer.process(df)
           A  B
        0  a  a
        1  b  b
        2  c  c

    """

    def __init__(self, col_names: list, fmt="speedy") -> None:
        super().__init__()
        self.col_names = col_names
        self.fmt = fmt

    def process(self, df, verbose=False) -> pd.DataFrame:
        """
        Apply the LowerCaseTransformer, converting all strings in the input dataframe into lowercase.

        Args:
            df (pd.DataFrame): Dataframe to apply the processing to
            verbose (bool, optional): Enable additional logging. Defaults to False.

        Raises:
            PreprocessingError: Raised if there are any issues during the transformation

        Returns:
            pd.DataFrame: Dataframe with all strings converted to lowercase.


        """
        df_out = df.copy(deep=True) if is_data_size_small(df) else df

        if not is_data_size_small(df):
            print(
                "Data is too large to copy. Transformation is being applied to the passed dataset directly"
            )

        if self.fmt == "speedy":
            columns = [col for col in self.col_names if col in df_out.index.values]
            for key in columns:
                df_out.loc[key] = df_out.loc[key].str.lower()
            return df_out
        elif self.fmt == "flat":
            columns = [col for col in self.col_names if col in df_out.columns]
            for col in columns:
                df_out[col] = df_out[col].str.lower()
            return df_out
        else:
            raise PreprocessingError(
                type(self).__name__,
                "Invalid format argument supplied when setting up class",
            )


class CategoricalColumnSplitter(IDataFrameTransformer):
    """
    Converts a QCB categorical field (insight codes) and splits it into a numerical and a categorical column. Seperating out the number of missed payments and other categorical fields.
    """  # noqa: E501

    def __init__(self, categorical_columns_to_split):
        self.categorical_columns_to_split = categorical_columns_to_split

    def _split_categorical_column(self, col_series: pd.Series, force_numeric=True):
        """
        For each insight code the following logic applies:

        0, 1, 2, 3, 4, 5, 6 - These contribute to the numerical field. Where the number is 3 or greater, a value of 'D' is set in the categorical field as we consider 3 missed payments a default
        'D' - This contributes to the categorical field, and a value of 5 is set in the numerical field as 5 is a clear default (a few missed payments higher than the minimum)
        'R', 'V' - This contributes to the categorical field, and a value of 6 is set in the numerical field as there has been a reposession this means they have missed the worst amount of payments
        'S' - This contributes to the categorical field, and a value of 0 is set in the numerical field, indicating that they have an account (or just had an account, and it is settled)
        'A' - This contributes to the categorical field, and a value of 2 is set in the numerical field as it indicates between 1 and 3 missed payments
        'C', 'M', 'T', 'U', 'N', 'Q', 'Z', '.', 'I' (and any others unseen) - These contribute to the categorical field, and a value of NaN is set in the numerical field

        Args:
        col_series (pd.Series): A series containing a mix of numerical and categorical values

        Returns:
        Tuple[pd.Series, pd.Series]: A tuple containing the numerical and categorical series
        """  # noqa: E501

        # Create a numerical series because one col will be numeric and one will be categorical
        numerical_series = col_series.copy()
        numerical_series = numerical_series.replace(
            ["D", "R", "V", "S", "A"], [5, 6, 6, 0, 2]
        )
        if force_numeric:
            numerical_series = pd.to_numeric(numerical_series, errors="coerce")

        # Create a categorical series. Removed copy for memory efficiency
        cat_series = col_series.replace(["0", "1", "2"], [np.nan, np.nan, np.nan])
        cat_series = cat_series.replace(["3", "4", "5", "6"], ["D", "D", "D", "D"])

        return cat_series, numerical_series

    def process(self, df_in: pd.DataFrame):
        num_dict = {}
        for col in self.categorical_columns_to_split:
            if "QCB" in col:
                cat_series, numerical_series = self._split_categorical_column(
                    df_in[col]
                )
                num_dict[col + "_num"] = numerical_series
                df_in[col] = cat_series
        df_in = pd.concat([df_in, pd.DataFrame(num_dict)], axis=1)
        return df_in
