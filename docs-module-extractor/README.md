# 📚 AI-Powered Documentation Module Extractor

An intelligent tool that automatically crawls documentation websites and extracts structured modules and submodules with detailed descriptions.

## 🚀 Features

- **Multi-URL Processing**: Analyze multiple documentation sites simultaneously
- **AI-Powered Analysis**: Intelligent module identification using ML algorithms
- **Multiple Output Formats**: JSON, CSV, Markdown, HTML, and visualizations
- **Advanced Crawling**: Recursive crawling with configurable depth
- **Content Cleaning**: Remove headers, footers, and navigation elements
- **Confidence Scoring**: See confidence levels for each extracted module
- **Docker Support**: Easy deployment with Docker and Docker Compose

## 📋 Prerequisites

- Python 3.9+
- Optional: OpenAI API key for AI-powered descriptions
- Optional: Docker for containerized deployment

## 🔧 Installation

### Method 1: Using pip

```bash
# Clone the repository
git clone <repository-url>
cd docs-module-extractor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt