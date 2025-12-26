# 📚 AI-Powered Documentation Module Extractor

- An intelligent tool that automatically crawls documentation websites and extracts structured modules and submodules with detailed descriptions. This application uses AI and machine learning to analyze documentation structure and identify logical components.

## 🚀 Features
- Multi-URL Processing: Analyze multiple documentation sites simultaneously

- AI-Powered Analysis: Intelligent module identification using ML algorithms

- Smart Crawling: Recursive crawling with configurable depth and content filtering

- Multiple Output Formats: JSON, CSV, Markdown, HTML, and interactive visualizations

- Confidence Scoring: See confidence levels for each extracted module

- Content Cleaning: Remove headers, footers, and navigation elements

- Docker Support: Easy deployment with Docker and Docker Compose

- REST API: Optional FastAPI endpoint for programmatic access

## 📋 Prerequisites
- Python 3.11 or higher
- Git (for version control)
- Optional: OpenAI API key for AI-powered descriptions
- Optional: Docker for containerized deployment

## 🔧 Installation
- Method 1: Using pip (Recommended)
``` bash
# Clone the repository
git clone https://github.com/yourusername/docs-module-extractor.git
cd docs-module-extractor

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
- Method 2: Using Docker
``` bash
# Build and run with Docker Compose
docker-compose up -d

# The application will be available at http://localhost:8501
``` 
- Method 3: Quick Setup (Windows)
``` bash
# Run the setup script
.\setup.bat
``` 
## ⚙️ Configuration
- Create a .env file in the project root (optional):
``` env
# OpenAI API Key (optional, for AI-powered descriptions)
OPENAI_API_KEY=your_openai_api_key_here

# Redis URL for caching (optional)
REDIS_URL=redis://localhost:6379/0

# Application settings
MAX_CRAWL_DEPTH=3
MAX_PAGES_PER_SITE=50
```

## 🎯 Usage
- Web Interface (Recommended)
- Start the Streamlit application:

```bash
streamlit run app.py
Open your browser and navigate to http://localhost:8501
```
Enter documentation URLs (one per line):
```
text
https://help.instagram.com
https://wordpress.org/documentation/
https://support.neo.space/hc/en-us
Configure processing options:
```
- Crawling depth (1-5 levels)
- Enable/disable AI-powered descriptions
- Maximum pages per site
- Click "Process Documentation" and view results

## Command Line Interface
```
bash
# Process a single URL
python module_extractor.py --url https://help.instagram.com

# Process multiple URLs
python module_extractor.py --urls https://help.instagram.com https://wordpress.org/documentation/

# Specify output file
python module_extractor.py --url https://help.instagram.com --output results.json
API Endpoint (Optional)
```
## Start the FastAPI server:

``` bash
uvicorn api.main:app --reload --port 8000
```
## API Usage:

``` bash
# POST request to extract modules
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://help.instagram.com"], "max_depth": 3}'
```
## 📊 Output Formats
- The tool generates structured output in multiple formats:
``` 
JSON Output Example
json
[
  {
    "module": "Account Settings",
    "Description": "Includes features and tools for managing Instagram account preferences, privacy, and credentials.",
    "Submodules": {
      "Change Username": "Explains how to update your Instagram handle and display name via account settings.",
      "Privacy Settings": "Controls for managing account visibility and data sharing preferences."
    },
    "confidence_score": 0.85
  }
]
```
### Available Export Formats
- JSON: Structured data for programmatic use
- CSV: Spreadsheet-friendly format for analysis
- Markdown: Readable documentation format
- HTML: Interactive web report
- Visualizations: Charts and graphs of module relationships
