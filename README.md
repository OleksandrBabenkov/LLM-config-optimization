```markdown
# LLM-Driven Autonomous Pipeline for Mathematical Image Filter Optimization

This repository contains the codebase for an autonomous, agentic workflow that utilizes Large Language Models (LLMs) to heuristically discover and optimize mathematical image filters. 

By decoupling the cognitive reasoning (LLM) and workflow routing (Google Apps Script) from the heavy mathematical computation (Python), this architecture establishes a highly scalable, serverless data lake using Google Workspace infrastructure. It bypasses traditional compute and orchestration bottlenecks associated with automated machine learning (AutoML).

## System Architecture

The pipeline operates as a continuous, asynchronous feedback loop:

1. **The Orchestrator (Google Apps Script):** Manages state, handles memory ("Hall of Fame"), and sends strictly engineered prompts to the LLM API.
2. **The Cognitive Core (LLM):** Acts as a heuristic search engine. It analyzes historical quantitative metrics (PSNR, SSIM) and proposes novel configurations (e.g., matrix weights or hyperparameters) formatted as JSON.
3. **The Data Lake (Google Drive/Sheets):** Acts as the asynchronous transport layer and visual dashboard. Configurations are dropped into Drive; results are logged in Sheets.
4. **The Compute Node (Python):** An extensible, object-oriented execution engine. It polls Google Drive for new configurations, runs the mathematical experiments against corrupted image datasets, evaluates the results, and uploads the metrics back to the data lake.

## Features

* **Serverless Orchestration:** Utilizes Google Apps Script and Google Drive, completely avoiding the need for dedicated orchestration servers.
* **Abstract Execution Engine:** The Python compute node uses the Factory Pattern and Abstract Base Classes. It can dynamically switch between simple OpenCV matrix convolutions and complex PyTorch neural network training without altering the orchestration layer.
* **Self-Reflecting Agentic Loop:** The LLM receives programmatic feedback (evaluation metrics and Python error tracebacks) to autonomously correct hallucinations and optimize mathematical outputs.
* **Live Dashboards:** Results are asynchronously piped into Google Sheets, updating live performance charts in real-time.

## Directory Structure

```text
├── data/
│   ├── raw/                 # Original, untouched datasets
│   └── corrupted/           # Datasets with injected noise/blur
├── src/
│   ├── experiments/
│   │   ├── base.py          # Abstract Base Class (BaseExperiment)
│   │   ├── factory.py       # Dynamic module loader
│   │   ├── kernel_filter.py # OpenCV matrix convolution implementation
│   │   └── resnet_tune.py   # Example PyTorch implementation
│   ├── utils/
│   │   ├── corruptor.py     # Deterministic image degradation scripts
│   │   └── metrics.py       # PSNR and SSIM calculation functions
│   └── main.py              # Main Google Drive polling and execution loop
├── credentials.json         # Google Cloud Service Account key (DO NOT COMMIT)
├── requirements.txt         # Python dependencies
└── README.md
```

## Prerequisites

* Python 3.9+
* A Google Cloud Project with the **Google Drive API** and **Google Sheets API** enabled.
* A Google Cloud Service Account with a generated `credentials.json` file.
* Access to an LLM API (e.g., OpenAI, Anthropic, or Google Gemini).
* A Google Workspace account to host the Google Apps Script and Drive folders.

## Setup Instructions

### 1. Python Compute Node Initialization
Clone the repository and install the required dependencies:
```bash
git clone [https://github.com/OleksandrBabenkov/LLM-config-optimization](https://github.com/OleksandrBabenkov/LLM-config-optimization)
cd LLM-config-optimization
pip install -r requirements.txt
```
Place your `credentials.json` file in the root directory. **Ensure this file is added to your `.gitignore`.**

### 2. Google Workspace Configuration
1. Create a master folder in Google Drive.
2. Create two subfolders: `LLM_Configs_In` and `Python_Results_Out`.
3. Share both subfolders with the `client_email` address found in your `credentials.json` file, granting **Editor** permissions.
4. Create a new Google Sheet for logging. Copy the Folder IDs and Sheet ID from their URLs to be used as environment variables.

### 3. Orchestrator Deployment (Google Apps Script)
1. Open your Google Sheet, navigate to **Extensions > Apps Script**.
2. Deploy the JavaScript orchestrator code (managing the `UrlFetchApp` LLM requests and Sheet appending).
3. Set a time-driven trigger in the Apps Script dashboard to execute the pipeline loop (e.g., every 1 minute).

## Usage

1. **Start the Compute Node:** Run the main Python polling script locally or on a dedicated machine/Colab instance.
   ```bash
   python src/main.py
   ```
2. **Initialize the Loop:** Drop a manual `config.json` into the `LLM_Configs_In` Drive folder, or manually trigger the Google Apps Script to make the initial LLM call.
3. **Monitor:** Open the Google Sheet to watch the autonomous researcher evaluate, fail, iterate, and optimize the mathematical parameters in real-time.
```