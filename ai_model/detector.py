import joblib
import os
import pandas as pd
import numpy as np

class BehaviorDetector:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(__file__), 'isolation_forest.pkl')
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model file not found. Please train the model first.")
        self.model = joblib.load(model_path)

    def analyze(self, files_accessed, data_transfer_mb, usb_copy_frequency, hour_of_day):
        """
        Analyzes a single record and returns whether it's an anomaly and a risk score.
        Returns: (is_anomaly, risk_score)
        - is_anomaly: 1 if anomaly, 0 if normal
        - risk_score: 0 to 100
        """
        input_data = pd.DataFrame({
            'files_accessed': [files_accessed],
            'data_transfer_mb': [data_transfer_mb],
            'usb_copy_frequency': [usb_copy_frequency],
            'hour_of_day': [hour_of_day]
        })

        # Predict anomaly (-1 is anomaly, 1 is normal in IsolationForest)
        prediction = self.model.predict(input_data)[0]
        is_anomaly = 1 if prediction == -1 else 0

        # Calculate risk score based on decision function
        # Lower decision score means more anomalous.
        score = self.model.decision_function(input_data)[0]
        
        # Normalize score to a 0-100 risk score
        # The typical range for decision_function is roughly -0.5 to 0.5.
        # Let's map it inversely so higher risk score = higher anomaly probability
        # Cap to 0-100
        risk_score = 50 - (score * 100)
        risk_score = max(0, min(100, risk_score))

        return is_anomaly, round(risk_score, 2)
