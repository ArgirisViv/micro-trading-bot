"""Causal features, known targets only, purged temporal holdout. Optional research ML."""
import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

MODEL_FILE = os.getenv('MODEL_PATH', 'model.joblib')
FEATURE_COLUMNS = ['return', 'sma_fast', 'sma_slow', 'rsi']


def create_features(df):
    close = pd.to_numeric(df['close'], errors='coerce')
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((loss == 0) & (gain == 0), 50)
    X = pd.DataFrame({'return': close.pct_change(fill_method=None),
        'sma_fast': close.rolling(10).mean(), 'sma_slow': close.rolling(30).mean(),
        'rsi': rsi}, index=df.index).replace([np.inf, -np.inf], np.nan).dropna()
    next_close = close.shift(-1)
    y = (next_close > close).astype('Int64').mask(next_close.isna() | close.isna())
    return X[FEATURE_COLUMNS], y.reindex(X.index)


def train_and_save(df, model_path=MODEL_FILE):
    X, y = create_features(df)
    known = y.notna()
    X, y = X.loc[known], y.loc[known].astype(int)
    if len(X) < 50 or y.nunique() < 2:
        raise ValueError('Insufficient labeled data; no dummy model will be published')
    split = int(len(X) * .8)
    X_train, y_train = X.iloc[:split-1], y.iloc[:split-1]
    X_test, y_test = X.iloc[split:], y.iloc[split:]
    model = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=42)
    model.fit(X_train, y_train)
    score = float(accuracy_score(y_test, model.predict(X_test)))
    training_end = str(X_train.index[-1])
    setattr(model, 'orbit_training_end', training_end)
    setattr(model, 'orbit_schema', FEATURE_COLUMNS)
    joblib.dump(model, model_path)
    metadata = {'schema_version': 1, 'features': FEATURE_COLUMNS,
        'training_end': training_end, 'holdout_start': str(X_test.index[0]),
        'holdout_end': str(X_test.index[-1]), 'holdout_accuracy': score,
        'majority_baseline_accuracy': float(y_test.value_counts(normalize=True).max()),
        'training_rows': len(X_train), 'holdout_rows': len(X_test),
        'purged_rows': 1, 'note': 'Directional classification is not trading profitability.'}
    with open(str(model_path) + '.json', 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle, indent=2)
    print('Temporal holdout accuracy:', score)
    return model


def load_model(path=MODEL_FILE):
    if not os.path.isfile(path):
        return None
    # Joblib executes serialized Python: load only your own trusted local artifact.
    model = joblib.load(path)
    if getattr(model, 'orbit_schema', None) != FEATURE_COLUMNS:
        raise ValueError('Model schema is absent or incompatible; retrain explicitly')
    return model
