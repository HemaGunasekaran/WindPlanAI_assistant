# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss
from sklearn.model_selection import train_test_split
from windplan.data import FEATURES


def train_model(history):
    x_train, x_test, y_train, y_test = train_test_split(history[FEATURES],
        history.completed_as_planned, test_size=.25, stratify=history.completed_as_planned, random_state=42)
    model = RandomForestClassifier(n_estimators=160, max_depth=8, min_samples_leaf=8,
        random_state=42, n_jobs=1)
    model.fit(x_train, y_train)
    scores = model.predict_proba(x_test)[:, list(model.classes_).index(1)]
    return model, {"holdout_accuracy": accuracy_score(y_test, scores >= .5),
        "holdout_auc": roc_auc_score(y_test, scores),
        "model_brier_loss": brier_score_loss(y_test, scores),
        "baseline_brier_loss": brier_score_loss(y_test, [y_train.mean()] * len(y_test)),
        "majority_baseline_accuracy": max(y_test.mean(), 1 - y_test.mean()), "train_rows": len(x_train), "test_rows": len(x_test)}
