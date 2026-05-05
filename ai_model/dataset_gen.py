import pandas as pd
import numpy as np
import os

def generate_mock_data(num_samples=2000):
    """
    Generates a mock dataset for training the Isolation Forest model.
    Features:
    - files_accessed (count per hour)
    - data_transfer_mb (MB per hour)
    - usb_copy_frequency (count per hour)
    - hour_of_day (0-23)
    """
    np.random.seed(42)
    
    # 95% Normal behavior
    normal_samples = int(num_samples * 0.95)
    normal_files = np.random.poisson(lam=20, size=normal_samples) # Average 20 files/hour
    normal_data = np.random.exponential(scale=10.0, size=normal_samples) # Average 10 MB/hour
    normal_usb = np.random.poisson(lam=1, size=normal_samples) # Rare USB copy (1 per hour or less)
    normal_hours = np.random.randint(9, 18, size=normal_samples) # 9 AM to 6 PM
    
    # 5% Anomalous behavior (Data leak patterns)
    anomaly_samples = num_samples - normal_samples
    anomaly_files = np.random.randint(200, 1000, size=anomaly_samples) # Rapid file access (e.g. 500 suspicious)
    anomaly_data = np.random.uniform(500, 5000, size=anomaly_samples) # Large data transfer (e.g. 2000 abnormal)
    anomaly_usb = np.random.randint(10, 50, size=anomaly_samples) # Sudden/frequent USB copies
    anomaly_hours = np.random.choice([0, 1, 2, 3, 20, 21, 22, 23], size=anomaly_samples) # Off-hours (e.g. 2 AM)
    
    files = np.concatenate([normal_files, anomaly_files])
    data = np.concatenate([normal_data, anomaly_data])
    usb = np.concatenate([normal_usb, anomaly_usb])
    hours = np.concatenate([normal_hours, anomaly_hours])
    labels = np.concatenate([np.zeros(normal_samples), np.ones(anomaly_samples)]) # 0=Normal, 1=Anomaly
    
    df = pd.DataFrame({
        'files_accessed': files,
        'data_transfer_mb': data,
        'usb_copy_frequency': usb,
        'hour_of_day': hours,
        'is_anomaly': labels
    })
    
    # Shuffle dataset
    df = df.sample(frac=1).reset_index(drop=True)
    
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    df.to_csv(os.path.join(os.path.dirname(__file__), 'mock_dataset.csv'), index=False)
    print("Mock dataset generated successfully.")

if __name__ == "__main__":
    generate_mock_data()
