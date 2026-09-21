# core/enhanced_ml.py - Enhanced Machine Learning Strategy
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class EnhancedMLModel:
    """
    Enhanced ML model with ensemble methods, feature engineering, and online learning.
    """
    
    def __init__(self, model_path="enhanced_model.joblib"):
        self.model_path = model_path
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.is_trained = False
        self.last_training = None
        self.performance_history = []
        
    def create_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create advanced technical and fundamental features.
        """
        df = df.copy()
        
        # Price-based features
        df['price_change'] = df['close'].pct_change()
        df['price_change_2d'] = df['close'].pct_change(2)
        df['price_change_5d'] = df['close'].pct_change(5)
        df['price_change_10d'] = df['close'].pct_change(10)
        
        # Volatility features
        df['volatility_5d'] = df['price_change'].rolling(5).std()
        df['volatility_10d'] = df['price_change'].rolling(10).std()
        df['volatility_20d'] = df['price_change'].rolling(20).std()
        
        # Volume features
        df['volume_ma_5'] = df['volume'].rolling(5).mean()
        df['volume_ma_10'] = df['volume'].rolling(10).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_5']
        
        # Technical indicator features
        df['rsi_ma'] = df['rsi'].rolling(5).mean()
        df['rsi_std'] = df['rsi'].rolling(5).std()
        df['sma_ratio'] = df['sma_fast'] / df['sma_slow']
        df['sma_diff'] = df['sma_fast'] - df['sma_slow']
        
        # Momentum features
        df['momentum_5d'] = df['close'] / df['close'].shift(5) - 1
        df['momentum_10d'] = df['close'] / df['close'].shift(10) - 1
        df['momentum_20d'] = df['close'] / df['close'].shift(20) - 1
        
        # Mean reversion features
        df['price_to_sma_20'] = df['close'] / df['close'].rolling(20).mean()
        df['price_to_sma_50'] = df['close'] / df['close'].rolling(50).mean()
        
        # ATR-based features
        df['atr_ratio'] = df['atr'] / df['close']
        df['atr_ma'] = df['atr'].rolling(10).mean()
        
        # Target variable (next day direction)
        df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
        
        # Remove rows with NaN values
        df = df.dropna()
        
        return df
    
    def select_features(self, df: pd.DataFrame) -> tuple:
        """
        Select the most important features using correlation and importance analysis.
        """
        # Define feature columns (excluding target and basic OHLCV)
        feature_cols = [
            'price_change', 'price_change_2d', 'price_change_5d', 'price_change_10d',
            'volatility_5d', 'volatility_10d', 'volatility_20d',
            'volume_ratio', 'rsi_ma', 'rsi_std', 'sma_ratio', 'sma_diff',
            'momentum_5d', 'momentum_10d', 'momentum_20d',
            'price_to_sma_20', 'price_to_sma_50', 'atr_ratio', 'atr_ma'
        ]
        
        # Filter available features
        available_features = [col for col in feature_cols if col in df.columns]
        
        X = df[available_features]
        y = df['target']
        
        self.feature_columns = available_features
        
        return X, y
    
    def train_ensemble_model(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """
        Train multiple models and create ensemble predictions.
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Initialize models
        models = {
            'random_forest': RandomForestClassifier(
                n_estimators=200, 
                max_depth=10, 
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        }
        
        # Train models
        trained_models = {}
        predictions = {}
        scores = {}
        
        for name, model in models.items():
            logger.info(f"Training {name}...")
            
            # Train model
            model.fit(X_train_scaled, y_train)
            trained_models[name] = model
            
            # Make predictions
            y_pred = model.predict(X_test_scaled)
            predictions[name] = y_pred
            
            # Calculate scores
            scores[name] = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred)
            }
            
            logger.info(f"{name} - Accuracy: {scores[name]['accuracy']:.3f}")
        
        # Ensemble prediction (simple average)
        ensemble_pred = np.mean([pred.astype(float) for pred in predictions.values()], axis=0)
        ensemble_pred = (ensemble_pred > 0.5).astype(int)
        
        # Ensemble scores
        ensemble_scores = {
            'accuracy': accuracy_score(y_test, ensemble_pred),
            'precision': precision_score(y_test, ensemble_pred),
            'recall': recall_score(y_test, ensemble_pred),
            'f1': f1_score(y_test, ensemble_pred)
        }
        
        scores['ensemble'] = ensemble_scores
        logger.info(f"Ensemble - Accuracy: {ensemble_scores['accuracy']:.3f}")
        
        # Store models and scaler
        self.models = trained_models
        self.is_trained = True
        self.last_training = datetime.now()
        
        # Store performance
        self.performance_history.append({
            'date': self.last_training,
            'scores': scores,
            'n_samples': len(X)
        })
        
        return scores
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using the trained ensemble model.
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train_ensemble_model first.")
        
        # Create features
        df_features = self.create_advanced_features(df)
        
        # Select features
        X, _ = self.select_features(df_features)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from each model
        predictions = {}
        for name, model in self.models.items():
            predictions[name] = model.predict_proba(X_scaled)[:, 1]
        
        # Ensemble prediction (weighted average)
        weights = {
            'random_forest': 0.4,
            'gradient_boosting': 0.4,
            'logistic_regression': 0.2
        }
        
        ensemble_pred = np.zeros(len(X))
        for name, pred in predictions.items():
            ensemble_pred += weights[name] * pred
        
        # Convert to binary predictions
        binary_pred = (ensemble_pred > 0.5).astype(int)
        
        return binary_pred
    
    def online_update(self, new_data: pd.DataFrame, batch_size: int = 100):
        """
        Online learning: update model with new data.
        """
        if not self.is_trained:
            logger.warning("Model not trained. Cannot perform online update.")
            return
        
        # Create features for new data
        new_features = self.create_advanced_features(new_data)
        X_new, y_new = self.select_features(new_features)
        
        if len(X_new) < batch_size:
            logger.info(f"Not enough new data for online update. Need {batch_size}, got {len(X_new)}")
            return
        
        # Scale new features
        X_new_scaled = self.scaler.transform(X_new)
        
        # Update each model
        for name, model in self.models.items():
            if hasattr(model, 'partial_fit'):
                # Models that support partial_fit
                model.partial_fit(X_new_scaled, y_new)
            else:
                # Retrain from scratch for models without partial_fit
                logger.info(f"Retraining {name} with new data...")
                model.fit(X_new_scaled, y_new)
        
        logger.info(f"Online update completed with {len(X_new)} new samples")
        self.last_training = datetime.now()
    
    def save_model(self, path: str = None):
        """
        Save the trained model and scaler.
        """
        if not self.is_trained:
            logger.warning("No trained model to save.")
            return
        
        save_path = path or self.model_path
        
        model_data = {
            'models': self.models,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'is_trained': self.is_trained,
            'last_training': self.last_training,
            'performance_history': self.performance_history
        }
        
        joblib.dump(model_data, save_path)
        logger.info(f"Model saved to {save_path}")
    
    def load_model(self, path: str = None):
        """
        Load a previously trained model.
        """
        load_path = path or self.model_path
        
        try:
            model_data = joblib.load(load_path)
            
            self.models = model_data['models']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = model_data['is_trained']
            self.last_training = model_data['last_training']
            self.performance_history = model_data.get('performance_history', [])
            
            logger.info(f"Model loaded from {load_path}")
            
        except FileNotFoundError:
            logger.warning(f"Model file {load_path} not found.")
            self.is_trained = False
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance from Random Forest model.
        """
        if not self.is_trained or 'random_forest' not in self.models:
            return pd.DataFrame()
        
        rf_model = self.models['random_forest']
        importance = rf_model.feature_importances_
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return feature_importance
    
    def get_performance_summary(self) -> dict:
        """
        Get summary of model performance over time.
        """
        if not self.performance_history:
            return {}
        
        latest = self.performance_history[-1]
        
        summary = {
            'last_training': latest['date'],
            'total_samples': latest['n_samples'],
            'models': {}
        }
        
        for model_name, scores in latest['scores'].items():
            summary['models'][model_name] = {
                'accuracy': scores['accuracy'],
                'f1_score': scores['f1']
            }
        
        return summary


def create_and_train_enhanced_model(df: pd.DataFrame, save_path: str = "enhanced_model.joblib"):
    """
    Convenience function to create and train the enhanced ML model.
    """
    logger.info("Creating enhanced ML model...")
    
    # Initialize model
    model = EnhancedMLModel(save_path)
    
    # Create features
    df_features = model.create_advanced_features(df)
    
    # Select features
    X, y = model.select_features(df_features)
    
    logger.info(f"Training with {len(X)} samples and {len(model.feature_columns)} features")
    
    # Train model
    scores = model.train_ensemble_model(X, y)
    
    # Save model
    model.save_model()
    
    # Feature importance
    importance = model.get_feature_importance()
    logger.info("Top 5 most important features:")
    for _, row in importance.head().iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.3f}")
    
    return model, scores


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Load sample data
    from data.live_data_fetch import get_live_data
    from core.indicators import add_indicators
    
    df = get_live_data("AAPL")
    df = add_indicators(df)
    
    if not df.empty:
        model, scores = create_and_train_enhanced_model(df)
        print("Model training completed!")
        print("Performance summary:", model.get_performance_summary())
    else:
        print("No data available for training")
