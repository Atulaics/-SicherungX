import pandas as pd
import joblib
import os
from sklearn.ensemble import IsolationForest

def train_model():
    dataset_path = os.path.join(os.path.dirname(__file__), 'mock_dataset.csv')
    
    if not os.path.exists(dataset_path):
        print("Dataset not found. Run dataset_gen.py first.")
        return

    print("Loading dataset...")
    df = pd.read_csv(dataset_path)
    
    # Features for training
    X = df[['files_accessed', 'data_transfer_mb', 'usb_copy_frequency', 'hour_of_day']]
    
    print("Training Isolation Forest model...")
    # contamination = 0.05 because we assumed 5% anomalies in our mock data
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(X)
    
    model_path = os.path.join(os.path.dirname(__file__), 'isolation_forest.pkl')
    joblib.dump(model, model_path)
    print(f"Model saved successfully at {model_path}")

if __name__ == "__main__":
    train_model()
