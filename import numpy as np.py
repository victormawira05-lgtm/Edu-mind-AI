import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 1. Simulate training data combining climate and soil features for agricultural zones
np.random.seed(42)
n_samples = 1000

# Features: Cumulative Rainfall (mm), Avg Temperature (°C), Soil Moisture Index, NDVI Anomaly
rainfall = np.random.normal(450, 100, n_samples)
temperature = np.random.normal(24, 3, n_samples)
soil_moisture = np.random.uniform(0.15, 0.60, n_samples)
ndvi_anomaly = np.random.normal(-0.05, 0.15, n_samples)

# Target: Vulnerability Risk (0 = Low Risk, 1 = Moderate Risk, 2 = High Risk)
# High risk triggered by low rainfall, high temperature, low soil moisture, and negative NDVI
risk_score = (
    (rainfall < 350).astype(int) + 
    (temperature > 27).astype(int) + 
    (soil_moisture < 0.25).astype(int) + 
    (ndvi_anomaly < -0.1).astype(int)
)
# Convert to 3 discrete classes
vulnerability_label = np.clip(risk_score, 0, 2)

df = pd.DataFrame({
    'Rainfall_mm': rainfall,
    'Temperature_C': temperature,
    'Soil_Moisture': soil_moisture,
    'NDVI_Anomaly': ndvi_anomaly,
    'Vulnerability_Risk': vulnerability_label
})

# 2. Train/Test Split
X = df[['Rainfall_mm', 'Temperature_C', 'Soil_Moisture', 'NDVI_Anomaly']]
y = df['Vulnerability_Risk']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# 3. Model Training Pipeline
model = RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42)
model.fit(X_train, y_train)

# 4. Evaluation
y_pred = model.predict(X_test)
print(f"Model Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=['Low Risk', 'Moderate Risk', 'High Risk']))

# Feature Importances (Explaining what is driving the risk)
importances = pd.Series(model.feature_importances_, index=X.columns)
print("\nKey Environmental Drivers of Risk:")
print(importances.sort_values(ascending=False))