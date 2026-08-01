"""
All LLM prompt templates for the Data Analyst Copilot.
Centralized here for easy tuning and versioning.
"""

SYSTEM_PROMPT = """You are an expert Data Analyst AI Copilot. You help users analyze datasets, generate insights, write Python/Pandas code, create visualizations, and explain statistical findings in plain English.

Your capabilities:
- Analyze datasets and answer questions about the data
- Generate Python/Pandas code to answer questions
- Create visualizations using matplotlib, seaborn, or plotly
- Perform statistical analysis
- Explain findings in clear, business-friendly language
- Suggest cleaning operations and feature engineering ideas
- Build ML models for prediction tasks

When generating code:
- Always use 'df' as the DataFrame variable name
- Use only allowed libraries: pandas (pd), numpy (np), matplotlib.pyplot (plt), seaborn (sns), scipy, sklearn
- Never use os, sys, subprocess, open, socket, or any file I/O
- Keep code concise and well-commented
- If creating a chart, do NOT use plt.show() or plt.savefig() or plt.close(). The system will automatically capture the active matplotlib figure.

Always respond in a structured way with clear explanations."""


INTENT_DETECTION_PROMPT = """Classify the user's question into one of these intents:

1. dataset_info - Questions about the dataset structure, columns, rows, types
2. statistics - Mean, median, std, correlation, distribution questions
3. visualization - Chart, plot, graph, histogram, bar chart requests
4. filtering - Filter, where, select, find rows matching criteria
5. aggregation - Group by, sum, count, average by category
6. cleaning - Handle missing values, duplicates, outliers
7. feature_engineering - Create new columns, transform data
8. sql_query - SQL-style queries
9. prediction - ML, model, predict, forecast
10. report - Summary, report, export, PDF
11. comparison - Compare columns, datasets, or categories
12. general - General conversation or unclear intent

User question: {question}

Dataset columns: {columns}

Respond with ONLY a JSON object:
{{
  "intent": "intent_name",
  "confidence": 0.95,
  "suggested_approach": "brief description of how to answer"
}}"""


NL_TO_PANDAS_PROMPT = """Convert the user's natural language question into Python/Pandas code.

Dataset Information:
- DataFrame variable: df
- Columns: {columns}
- Sample data:
{sample_data}
- Data types:
{dtypes}

User question: {question}

Rules:
1. Use ONLY: pandas (pd), numpy (np), matplotlib.pyplot (plt), seaborn (sns)
2. The result should be stored in a variable called 'result'
3. If creating a chart, do NOT use plt.show() or plt.savefig() or plt.close(). The system will automatically capture the active matplotlib figure.
4. Keep code clean and add inline comments
5. For tables/data, result should be a pandas DataFrame or Series
6. Never use os, sys, subprocess, open, or socket

Respond with ONLY a JSON object:
{{
  "code": "your_python_code_here",
  "chart_requested": true/false,
  "result_type": "table|value|chart|mixed",
  "explanation": "brief explanation of what the code does"
}}"""


INSIGHT_GENERATION_PROMPT = """You are analyzing data results. Generate a clear, insightful explanation.

Dataset: {dataset_name}
Analysis type: {analysis_type}
Question asked: {question}

Results:
{results}

Statistical context:
{stats_context}

INSTRUCTIONS:
If the analysis type is 'general' and the user is just greeting or asking a conversational question (e.g. "hi", "hello", "how are you"), do NOT provide a dataset summary. Instead, simply reply politely and concisely, introducing yourself as their Data Analyst Copilot and asking how you can help them analyze their {dataset_name} dataset.

For all other data-related questions, provide:
1. Direct answer to the user's question.
2. Key insights and patterns (3-4 bullet points)
3. Business implications or recommendations (1-2 sentences)
4. Any anomalies or things to investigate further

Keep language professional but accessible. Focus on actionable insights."""


CHART_EXPLANATION_PROMPT = """Explain this chart to a business user.

Chart type: {chart_type}
Column(s): {columns}
Dataset: {dataset_name}

Statistical summary:
{stats}

Provide:
1. What this chart shows (1 sentence)
2. Key patterns or trends (2-3 bullet points)
3. Outliers or anomalies (if any)
4. Business recommendation based on this data

Keep it concise and actionable (max 150 words)."""


EDA_SUMMARY_PROMPT = """Perform an automatic exploratory data analysis summary.

Dataset: {dataset_name}
Rows: {rows}, Columns: {columns}
Missing values: {missing_pct}%
Duplicates: {duplicates}

Column overview:
{column_summary}

Numeric statistics:
{numeric_stats}

Provide a comprehensive but concise EDA summary:
1. Dataset overview (2 sentences)
2. Data quality issues (missing values, duplicates, outliers)
3. Key patterns in numeric columns
4. Distribution insights
5. Recommendations for cleaning/analysis
6. Interesting questions to explore

Format as clean markdown with headers."""


SUGGESTED_QUESTIONS_PROMPT = """Based on this dataset, generate 10 insightful questions a data analyst would ask.

Dataset: {dataset_name}
Columns: {columns}
Sample data:
{sample_data}
Data types: {dtypes}
Quick stats: {quick_stats}

Generate questions across these categories:
- overview: basic dataset understanding
- statistics: statistical analysis
- visualization: chart/plot requests
- cleaning: data quality
- business: business insights

Respond with ONLY a JSON array:
[
  {{"question": "What is the...", "category": "overview", "icon": "📊"}},
  ...
]

Make questions specific to the actual column names and data. Be creative and insightful."""


ML_ASSISTANT_PROMPT = """You are an ML assistant. The user wants to build a predictive model.

Dataset: {dataset_name}
Columns: {columns}
Data types: {dtypes}
User request: {request}

1. Identify the most appropriate target column
2. Identify feature columns
3. Recommend the best model type (classification/regression)
4. Generate complete Python scikit-learn code to:
   - Preprocess the data
   - Train/test split
   - Train the model
   - Evaluate with appropriate metrics
   - Return feature importance if available

Store final metrics in 'result' dict with keys: model_type, accuracy_or_r2, features, target

Code should use: pandas (pd), numpy (np), sklearn (imported normally), matplotlib.pyplot (plt)"""


REPORT_GENERATION_PROMPT = """Generate a professional data analysis report.

Dataset: {dataset_name}
Analysis date: {date}
Rows: {rows}, Columns: {columns}

Profile summary:
{profile_summary}

Key findings from conversation:
{conversation_summary}

Charts generated: {chart_count}

Write a professional executive report with:
1. Executive Summary (3-4 sentences)
2. Dataset Overview
3. Key Findings (numbered list with specifics)
4. Data Quality Assessment
5. Business Recommendations (3-5 actionable items)
6. Conclusion

Format as clean markdown. Be specific with numbers and percentages."""


CLEANING_RECOMMENDATION_PROMPT = """Analyze this dataset and recommend data cleaning operations.

Dataset: {dataset_name}
Columns with missing values: {missing_columns}
Duplicate rows: {duplicates}
Data types: {dtypes}
Outlier columns: {outlier_columns}

Recommend specific cleaning steps:
1. For each column with missing values: recommend fill strategy (mean/median/mode/drop/forward fill)
2. Duplicate handling recommendation
3. Outlier treatment recommendation
4. Type conversion recommendations
5. Column rename suggestions (if names are unclear)

Respond as a JSON object with cleaning_steps array."""
