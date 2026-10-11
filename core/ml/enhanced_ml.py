"""
Enhanced ML Model for Trading Bot Dashboard
Provides ML insights, predictions, and feature analysis
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import os
from typing import Any, Dict, Tuple
import logging

class EnhancedMLModel:
    """Enhanced ML model for trading insights and predictions"""
    
    def __init__(self, model_path: str = "models/enhanced_ml_model.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
        self.logger = logging.getLogger(__name__)
        
        # Load pre-trained model if exists
        self.load_model()
    
    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create technical features from price data"""
        try:
            features = pd.DataFrame(index=data.index)
            
            # Price-based features
            features['returns'] = data['close'].pct_change()
            features['log_returns'] = np.log(data['close'] / data['close'].shift(1))
            features['price_change'] = data['close'] - data['close'].shift(1)
            features['price_change_pct'] = (data['close'] - data['close'].shift(1)) / data['close'].shift(1)
            
            # Moving averages
            features['sma_5'] = data['close'].rolling(window=5).mean()
            features['sma_20'] = data['close'].rolling(window=20).mean()
            features['ema_12'] = data['close'].ewm(span=12).mean()
            features['ema_26'] = data['close'].ewm(span=26).mean()
            
            # Price ratios
            features['price_sma5_ratio'] = data['close'] / features['sma_5']
            features['price_sma20_ratio'] = data['close'] / features['sma_20']
            features['ema_ratio'] = features['ema_12'] / features['ema_26']
            
            # Volatility features
            features['volatility_5'] = features['returns'].rolling(window=5).std()
            features['volatility_20'] = features['returns'].rolling(window=20).std()
            features['volatility_ratio'] = features['volatility_5'] / features['volatility_20']
            
            # Volume features
            if 'volume' in data.columns:
                features['volume_sma'] = data['volume'].rolling(window=20).mean()
                features['volume_ratio'] = data['volume'] / features['volume_sma']
                features['volume_price_trend'] = (data['volume'] * features['returns']).rolling(window=5).sum()
            
            # Momentum features
            features['momentum_5'] = data['close'] / data['close'].shift(5) - 1
            features['momentum_10'] = data['close'] / data['close'].shift(10) - 1
            features['momentum_20'] = data['close'] / data['close'].shift(20) - 1
            
            # RSI-like features
            features['rsi_5'] = self._calculate_rsi(data['close'], window=5)
            features['rsi_14'] = self._calculate_rsi(data['close'], window=14)
            
            # Bollinger Bands features
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(data['close'])
            features['bb_position'] = (data['close'] - bb_lower) / (bb_upper - bb_lower)
            features['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # MACD features
            macd, signal, _ = self._calculate_macd(data['close'])
            features['macd'] = macd
            features['macd_signal'] = signal
            features['macd_histogram'] = macd - signal
            
            # Remove infinite and NaN values
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.ffill().fillna(0)
            
            self.feature_names = features.columns.tolist()
            return features
            
        except Exception as e:
            self.logger.error(f"Error creating features: {e}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices: pd.Series, window: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def train(self, features: pd.DataFrame, target: pd.Series) -> bool:
        """Train the ML model"""
        try:
            if len(features) < 50:
                self.logger.warning("Insufficient data for training (need at least 50 samples)")
                return False
            
            # Prepare data
            X = features.values
            y = target.astype("int64").to_numpy(copy=True)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.logger.info(f"Model trained successfully. Test accuracy: {accuracy:.2%}")
            self.is_trained = True
            
            # Save model
            self.save_model()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            return False
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained or self.model is None:
            return np.array([])
        
        try:
            X = features.values
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            return predictions
        except Exception as e:
            self.logger.error(f"Error making predictions: {e}")
            return np.array([])
    
    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Get prediction probabilities"""
        if not self.is_trained or self.model is None:
            return np.array([])
        
        try:
            X = features.values
            X_scaled = self.scaler.transform(X)
            probabilities = self.model.predict_proba(X_scaled)
            return probabilities
        except Exception as e:
            self.logger.error(f"Error getting probabilities: {e}")
            return np.array([])
    
    def evaluate(self, features: pd.DataFrame, target: pd.Series) -> Dict[str, float]:
        """Evaluate model performance"""
        if not self.is_trained or self.model is None:
            return {}
        
        try:
            predictions = self.predict(features)
            if len(predictions) == 0:
                return {}
            
            return {
                'accuracy': float(accuracy_score(target, predictions)),
                'precision': float(precision_score(target, predictions, average='weighted')),
                'recall': float(recall_score(target, predictions, average='weighted')),
                'f1': float(f1_score(target, predictions, average='weighted'))
            }
        except Exception as e:
            self.logger.error(f"Error evaluating model: {e}")
            return {}
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if not self.is_trained or self.model is None:
            return {}
        
        try:
            importance = self.model.feature_importances_
            feature_importance = dict(zip(self.feature_names, importance))
            return dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        except Exception as e:
            self.logger.error(f"Error getting feature importance: {e}")
            return {}
    
    def save_model(self) -> bool:
        """Save the trained model"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, self.model_path)
            self.logger.info(f"Model saved to {self.model_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self) -> bool:
        """Load a pre-trained model"""
        try:
            if os.path.exists(self.model_path):
                model_data = joblib.load(self.model_path)
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.feature_names = model_data['feature_names']
                self.is_trained = model_data['is_trained']
                self.logger.info(f"Model loaded from {self.model_path}")
                return True
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
        
        return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'is_trained': self.is_trained,
            'feature_count': len(self.feature_names),
            'model_path': self.model_path,
            'feature_names': self.feature_names[:10]  # First 10 features
        }
