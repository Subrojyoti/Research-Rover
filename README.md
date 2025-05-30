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

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Research-Rover.git
   cd Research-Rover
   ```

2. **Backend Setup**
   ```bash
   cd backend
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

## API Endpoints

- `GET /search`: Search for research papers
- `GET /search_progress`: Get current search progress
- `GET /download/<filename>`: Download CSV file
- `GET /get_csv_data/<filename>`: Get CSV data
- `GET /get_paginated_results`: Get paginated search results

