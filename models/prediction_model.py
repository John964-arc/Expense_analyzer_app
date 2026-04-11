"""
prediction_model.py
───────────────────
Multi-model regression pipeline to predict next month's total expense.

Three models are compared via Leave-One-Out Cross Validation (LOOCV):
  1. LinearRegression  — baseline trend line
  2. Ridge             — L2-regularised, more stable with small datasets
  3. PolynomialFeatures(degree=2) + LinearRegression — captures curved trends

The winner is selected by lowest RMSE. Features include rolling mean,
rolling std, and sin/cos month-of-year encoding for seasonality.
"""

import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneOut


class ExpensePredictionModel:

    MODEL_REGISTRY = {
        'linear': lambda: LinearRegression(),
        'ridge':  lambda: Ridge(alpha=1.0),
        'poly2':  lambda: Pipeline([
                      ('poly',   PolynomialFeatures(degree=2, include_bias=False)),
                      ('scaler', StandardScaler()),
                      ('reg',    LinearRegression()),
                  ]),
    }

    def __init__(self):
        self.best_model      = None
        self.best_model_name = None
        self.scaler_X        = StandardScaler()
        self.is_trained      = False
        self.num_months      = 0
        self.training_data   = []
        self.model_scores    = {}
        self._X_fitted       = False

    # ── Public API ────────────────────────────────────────────────────

    def train(self, monthly_totals: list) -> bool:
        """Train all candidate models; select best by LOOCV RMSE."""
        self.training_data = monthly_totals
        self.num_months    = len(monthly_totals)

        if len(monthly_totals) < 3:
            self.is_trained = bool(monthly_totals)
            return self.is_trained

        X = self._build_features(monthly_totals)
        y = np.array(monthly_totals, dtype=float)

        self.y_mean   = y.mean()
        self.y_std    = y.std() if y.std() > 0 else 1.0
        y_scaled      = (y - self.y_mean) / self.y_std

        best_rmse, best_name, best_fitted = float('inf'), None, None

        for name, factory in self.MODEL_REGISTRY.items():
            try:
                model = factory()
                rmse  = self._loocv_rmse(model, X, y_scaled)
                self.model_scores[name] = round(rmse * self.y_std, 2)
                if rmse < best_rmse:
                    best_rmse   = rmse
                    best_name   = name
                    best_fitted = factory()
                    best_fitted.fit(X, y_scaled)
            except Exception:
                continue

        if best_fitted is None:
            return False

        self.best_model      = best_fitted
        self.best_model_name = best_name
        self.is_trained      = True
        return True

    def predict_next_month(self) -> float:
        """Predict total expense for the next calendar month."""
        if not self.is_trained:
            return 0.0
        if self.best_model is None:
            tail = self.training_data[-3:] if len(self.training_data) >= 3 else self.training_data
            return round(float(np.mean(tail)), 2) if tail else 0.0

        X_next = self._build_features(self.training_data + [0])[-1:]
        raw    = self.best_model.predict(X_next)[0]
        return max(0.0, round(float(raw * self.y_std + self.y_mean), 2))

    def predict_confidence_interval(self, confidence: float = 0.90) -> tuple:
        """Return (lower, upper) 90% prediction interval."""
        pred = self.predict_next_month()
        if not self.is_trained or len(self.training_data) < 3:
            margin = pred * 0.15
            return (round(max(0, pred - margin), 2), round(pred + margin, 2))

        X = self._build_features(self.training_data)
        y = np.array(self.training_data, dtype=float)
        y_scaled = (y - self.y_mean) / self.y_std
        residuals = (self.best_model.predict(X) - y_scaled) * self.y_std
        sigma = float(np.std(residuals))
        z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
        margin = z * sigma
        return (round(max(0, pred - margin), 2), round(pred + margin, 2))

    def get_trend(self, monthly_totals: list = None) -> str:
        """Return 'increasing' | 'decreasing' | 'stable' based on recent slope."""
        data = monthly_totals if monthly_totals is not None else self.training_data
        if len(data) < 2:
            return 'stable'
        tail  = data[-3:] if len(data) >= 3 else data
        slope = np.polyfit(range(len(tail)), tail, 1)[0]
        mean  = np.mean(tail) if np.mean(tail) > 0 else 1
        pct   = (slope / mean) * 100
        if pct > 3:   return 'increasing'
        if pct < -3:  return 'decreasing'
        return 'stable'

    def get_month_over_month_change(self, monthly_totals: list = None) -> float:
        """Return % change between last two months."""
        data = monthly_totals if monthly_totals is not None else self.training_data
        if len(data) < 2 or data[-2] == 0:
            return 0.0
        return round((data[-1] - data[-2]) / data[-2] * 100, 1)

    def get_model_report(self) -> dict:
        return {
            'best_model':   self.best_model_name or 'none',
            'model_scores': self.model_scores,
            'n_months':     self.num_months,
            'is_trained':   self.is_trained,
        }

    # ── Private helpers ───────────────────────────────────────────────

    def _build_features(self, monthly_totals: list) -> np.ndarray:
        n         = len(monthly_totals)
        arr       = np.array(monthly_totals, dtype=float)
        time_idx  = np.arange(n, dtype=float)
        roll_mean = np.array([arr[max(0, i-2):i+1].mean() for i in range(n)])
        roll_std  = np.array([arr[max(0, i-2):i+1].std()  for i in range(n)])
        now       = datetime.now()
        months    = np.array([(now.month - (n-1-i)) % 12 + 1 for i in range(n)], dtype=float)
        sin_m     = np.sin(2 * np.pi * months / 12)
        cos_m     = np.cos(2 * np.pi * months / 12)
        X = np.column_stack([time_idx, roll_mean, roll_std, sin_m, cos_m])
        if not self._X_fitted:
            self.scaler_X.fit(X)
            self._X_fitted = True
        return self.scaler_X.transform(X)

    @staticmethod
    def _loocv_rmse(model, X: np.ndarray, y: np.ndarray) -> float:
        loo, errors = LeaveOneOut(), []
        for tr, te in loo.split(X):
            try:
                model.fit(X[tr], y[tr])
                errors.append((model.predict(X[te])[0] - y[te[0]]) ** 2)
            except Exception:
                errors.append(1e9)
        return float(np.sqrt(np.mean(errors))) if errors else float('inf')
