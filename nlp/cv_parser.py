import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

import re
import nltk

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.tokenize import word_tokenize
from wordcloud import WordCloud
import os
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score, StratifiedKFold
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

plt.style.use('default')
sns.set_palette("husl")

current_dir = os.path.dirname(os.path.abspath(__file__))

dataset_path = os.path.join(current_dir, '..', 'data/archive/Resume', 'Resume.csv')
df = pd.read_csv(dataset_path)

# print(f"Dataset Shape: {df.shape}")
# print(f"Columns: {list(df.columns)}")
# print(f"\nMissing Values:\n{df.isnull().sum()}")
# print(f"\nDuplicate Rows: {df.duplicated().sum()}")
# print(df.head(5))
# print(df.info())

df_clean = df.drop(['ID', 'Resume_html'], axis=1).copy()
print(f"Cleaned Dataset Shape: {df_clean.shape}")
print(f"Categories: {df_clean['Category'].nunique()}")
print(f"Unique Resumes: {df_clean['Resume_str'].nunique()}")

category_counts = df_clean['Category'].value_counts()
print("Category Distribution:")
print(category_counts)