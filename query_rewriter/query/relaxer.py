import pandas as pd
import numpy as np
import editdistance


class QueryRelaxer:
    query: dict = None
    '''
    Dictionary of key-value pairs representing the original query.
    Each key is an attribute of the DataSet.
    The corresponding value can be a single value or a list of values for which the equality has to be true.
    '''
    rfds_df: pd.DataFrame = None
    '''
    DataFrame containing all the RFDs in the following format:
    RHS | Attributes
    RHS column is the RHS attribute label of the RFD for each row.
    Attributes columns contains the corresponding threshold for the RFD attribute.
    '''
    data_set_df: pd.DataFrame = None
    '''
    DataFrame containing the data to query.
    '''
    query_attributes: list = None
    '''
    List of the attributes involved in the query.
    '''

    def __init__(self, query: dict, rfds_df: pd.DataFrame, data_set_df: pd.DataFrame) -> None:
        super().__init__()
        self.query = query
        self.rfds_df = rfds_df
        self.data_set_df = data_set_df
        # ===============================================
        self.query_attributes = list(self.query.keys())

    def drop_query_na(self) -> pd.DataFrame:
        '''
        Drops the RFDs where an attribute of the query is NaN.
        :return: the dropped RFDs DataFrame.
        '''
        self.rfds_df = self.rfds_df.dropna(subset=self.query_attributes).reset_index(drop=True)
        return self.rfds_df

    def drop_query_rhs(self) -> pd.DataFrame:
        '''
        Drops the RFDs where the RHS attribute is part of the query.
        :return: the dropped RFDs DataFrame.
        '''
        self.rfds_df = self.rfds_df.drop(self.rfds_df[self.rfds_df["RHS"].isin(self.query_attributes)]
                                         .index).reset_index(drop=True)
        return self.rfds_df

    def sort_nan_query_attributes(self) -> pd.DataFrame:
        '''
        Sorts the RFDs DataFrame by decreasing number of NaNs and increasing values of query attributes.
        :return: the sorted RFDs DataFrame.
        '''
        nan_count = "NaNs"
        kwargs = {nan_count: lambda x: x.isnull().sum(axis=1)}
        self.rfds_df = self.rfds_df.assign(**kwargs)

        # print("Sorting Keys:", sorting_cols)
        ascending = [False]

        sorting_cols = self.query_attributes
        sorting_cols = sorting_cols.extend([nan_count])
        ascending.extend([True for _ in self.query_attributes])

        self.rfds_df = self.rfds_df.sort_values(by=sorting_cols,
                                                ascending=ascending,
                                                na_position="first").reset_index(drop=True).drop(nan_count, axis=1)

        return self.rfds_df

    def rfd_to_string(rfd: dict) -> str:
        string = ""
        string += "".join(["" if key == "RHS" or key == rfd["RHS"] or np.isnan(val) else "(" + key + " <= " + str(
            val) + ") " for key, val in rfd.items()])
        string += "---> ({} <= {})".format(rfd["RHS"], rfd[rfd["RHS"]])
        return string

    def query_dict_to_expr(query: dict) -> str:
        expr = " and ".join(
            ["{} == {}".format(k, v) if not isinstance(v, str) else "{} == '{}'".format(k, v) for k, v in
             query.items()])
        return expr

    def extend_query_ranges(query: dict, rfd: dict, data_set: pd.DataFrame = None) -> dict:
        '''
        Given a query and an RFD, extends the query attributes range
        by the corresponding threshold contained in the RFD.
        If some of the query attributes are of type string, the full DataFrame
        is needed to calculate the list of strings similar to the attribute value.
        :param query: The query to be extended.
        :param rfd: The RFD containing the thresholds to apply.
        :param data_set: The full DataFrame to query.
        :return: the extended query.
        '''

        for key, val in query.items():
            print("{} : {}".format(key, val))
            if key in rfd:
                print(key + " in RFD")
                threshold = rfd[key]
                print("Threshold:", threshold)

                if threshold > 0.0:
                    print("Threshold is positive:", threshold)
                    if isinstance(val, int):
                        print(val, " is int...")
                        val_range = range(int(val - threshold), int(val + threshold + 1))
                        print("Range: ", list(val_range))
                        query[key] = list(val_range)
                    elif isinstance(val, str):
                        print(val, " is string...")
                        source = val
                        simil_string = QueryRelaxer.similar_strings(source=source, data=data_set, col=key,
                                                                    threshold=threshold)
                        print("Similar strings: ", simil_string)
                        query[key] = simil_string
                else:
                    print("Threshold is not positive:", threshold)
        return query

    def similar_strings(source: str, data: pd.DataFrame, col: str, threshold: int) -> list:
        '''
        Returns a list of strings, from the column col of data DataFrame,
        that are similar to the source string with an edit distance of at most threshold.
        :param source: the string against which to compute the edit distances.
        :param data: the DataFrame containing the string values.
        :param col: the DataFrame column containing the string values.
        :param threshold: the maximum edit distance between source and another string.
        :return: the list of strings similar to source.
        '''

        return data[data[col].apply(lambda word: int(editdistance.eval(source, word)) <= threshold)][
            col].tolist()
