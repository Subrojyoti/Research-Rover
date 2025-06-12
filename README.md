# Research Rover

## Introduction
Research Rover is a modern web application designed to help researchers and students efficiently gather and analyze academic research papers. The application provides a user-friendly interface for paper discovery and analysis, making it easier to find and manage research papers.

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask**: Web framework for building the REST API
- **Flask-CORS**: Handles Cross-Origin Resource Sharing
- **BeautifulSoup4**: Web scraping and HTML parsing
- **Requests**: HTTP library for API calls
- **Python-dotenv**: Environment variable management

### Frontend
- **React 19**: UI library
- **Vite**: Build tool and development server
- **Material-UI (MUI)**: Component library
- **Axios**: HTTP client
- **React Router**: Client-side routing
- **Framer Motion**: Animation library
- **GSAP**: Advanced animations
- **Locomotive Scroll**: Smooth scrolling

## Features

### Currently Implemented
- **Advanced Paper Search**
  - Search research papers using keywords
  - Real-time search progress tracking
  - Paginated results
  - Export search results to CSV

- **Paper Management**
  - View paper metadata (title, source, year, keywords)
  - Download paper information
  - Organized CSV export functionality


### Prerequisites
- Python 3.8 or higher
- Node.js (Latest LTS version recommended)
- npm or yarn package manager

### Configuration
* Get [CORE API](https://core.ac.uk/services/api)
* Get [Gemini API](https://aistudio.google.com/apikey)
* Get [Pubmed API](https://support.nlm.nih.gov/kbArticle/?pn=KA-05317)

Create a secret.txt file inside the `backend/` folder and fill it with the information below:
```
CORE_API='Your_Core_API_key'
GOOGLE_GENAI_API_KEY=your_gemini_api_key
EMAIL='your_email'
PUBMED_API_KEY='Your_Pubmed_Api_Key'
```
### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Research-Rover.git
   cd Research-Rover
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv .venv
   pip install -r requirements.txt
   python app.py
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
## Usage Guide
1. **Searching Papers**
   - Enter your search keywords in the search bar
   - View real-time search progress
   - Browse through paginated results
   - Export results to CSV for offline analysis

2. **Managing Results**
   - View detailed paper information
   - Download paper metadata
   - Access paper sources and download links

3. **AI Chat**
   - Get response to queries from the collected papers.
   - Get citations along with reponses.

## API Endpoints

- `GET /search`: Search for research papers
- `GET /search_progress`: Get current search progress
- `GET /download/<filename>`: Download CSV file
- `GET /get_csv_data/<filename>`: Get CSV data
- `GET /get_paginated_results`: Get paginated search results