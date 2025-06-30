import pandas as pd
from sklearn.model_selection import train_test_split

INPUT_FILE = "data/dfoeufs_with_predictions_with_ground_truth.jsonl"


def load_dataset(input_file=INPUT_FILE, Xcol="ocr_text", ycol="ground_truth", supervised=True):
    """_summary_

    Args:
        input_file (str, optional): json or csv having Xcol and ycol columns. Defaults to INPUT_FILE.
        Xcol (str, optional): Feature (X) column name. Defaults to "ocr_text".
        ycol (str, optional): Label (y) column name. Defaults to "ground_truth".
        supervised (bool, optional): If True, drop nans in ycol. Defaults to True.

    Returns:
        (np.array, np.array)): List-like of X and y values.
    """

    df=pd.read_json(input_file, lines=True) if input_file.endswith(".jsonl") else pd.read_csv(input_file)
    df=df.dropna(subset=Xcol).set_index("code")
    if supervised:
        df = df[df[ycol] != 'None'].dropna(subset=ycol)
    return df[Xcol].values, df[ycol].values


def train_test_dataset(input_file=INPUT_FILE,
                       Xcol="ocr_text",
                       ycol="ground_truth",
                       test_size=0.15,
                       random_state=2):
    """Retrieve a standard training and testing split.

    Args:
        input_file (str, optional): json or csv having Xcol and ycol columns. Defaults to INPUT_FILE.
        Xcol (str, optional): Feature (X) column name. Defaults to "ocr_text".
        ycol (str, optional): Label (y) column name. Defaults to "ground_truth".
        test_size (float, optional): Fraction or test dataset. Defaults to 0.15.
        random_state (int, optional): For reproductibility. Defaults to 2.

    Returns:
        X_train, y_train, X_test, y_test: cf scikit-learn documentation
    """

    X, y=load_dataset(input_file, Xcol, ycol, supervised=True)
    return train_test_split(X, y, test_size=test_size, random_state=random_state)
