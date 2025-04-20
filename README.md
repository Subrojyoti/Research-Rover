# Research Rover

## Introduction
Research Rover is a modern web application designed to help researchers and students efficiently gather and analyze academic research papers. The application provides a user-friendly interface for paper discovery and analysis, making it easier to find and manage research papers.

Currently, Research Rover supports advanced paper search, metadata management, interactive AI-powered chat, and embedding-based similarity search. It also integrates a Retrieval-Augmented Generation (RAG) system to provide contextual and accurate responses based on indexed research papers.

Research Rover aims to become a comprehensive platform for academic research, enabling users to streamline their research process and make data-driven decisions.

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask**: Web framework for building the REST API
- **Flask-CORS**: Handles Cross-Origin Resource Sharing
- **BeautifulSoup4**: Web scraping and HTML parsing
- **Requests**: HTTP library for API calls
- **Python-dotenv**: Environment variable management
- **FAISS**: High-performance similarity search for embedding-based indexing

### Frontend
- **React 19**: UI library
- **Vite**: Build tool and development server
- **Material-UI (MUI)**: Component library for responsive and accessible UI
- **Axios**: HTTP client for API communication
- **React Router**: Client-side routing for seamless navigation
- **Framer Motion**: Animation library for smooth transitions
- **GSAP**: Advanced animations for interactive elements
- **Locomotive Scroll**: Smooth scrolling for enhanced user experience

### Styling
- **CSS Variables**: For consistent theming
- **Responsive Design**: Media queries for mobile and desktop compatibility
- **Custom Animations**: Keyframe-based animations for dynamic UI

## Features

### Currently Implemented
- **Advanced Paper Search**
  - Search research papers using query, max results, year range (optional)
  - Real-time search progress tracking with visual indicators
  - Paginated results for efficient browsing
  - Export search results to CSV for offline analysis

- **Paper Management**
  - View detailed paper metadata (title, source, year, keywords)
  - Download paper information in structured formats
  - Organized CSV export functionality for bulk data handling
  - Download all papers in pdf zipped format

- **Interactive Chat**
  - AI-powered chat interface for intelligent responses
  - Copy functionality for chat messages with visual feedback (e.g., "Copied!" animation)
  - Editable user messages with real-time updates

- **Progress Tracking**
  - Embedding progress bar with dynamic stages and messages
  - Real-time updates on the embedding process
  - Search progress bar with checkpoints and animations

- **Premium UI Elements**
  - Custom-designed cards with hover effects
  - Smooth animations for titles and subtitles
  - Responsive layout for all screen sizes
  - Dynamic buttons with hover and click effects

- **PDF and Embedding Management**
  - Download PDFs directly from search results
  - Generate embeddings for research papers
  - FAISS-based indexing for efficient similarity search

- **Retrieval-Augmented Generation (RAG)**
  - Combines document retrieval with generative AI for contextual responses
  - Provides accurate and relevant answers based on indexed research papers

- **Error Handling**
  - User-friendly error messages for failed API calls
  - Graceful fallback for incomplete processes

## Getting Started

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
   - View real-time search progress with the embedding progress bar
   - Browse through paginated results
   - Export results to CSV for offline analysis

2. **Managing Results**
   - View detailed paper information, including metadata
   - Download paper metadata in structured formats
   - Access paper sources and download links

3. **Interactive Chat**
   - Use the chat interface to ask questions about your research
   - Copy chat responses with a single click and receive visual feedback
   - Edit user messages and get updated responses

4. **Embedding and PDF Management**
   - Generate embeddings for research papers
   - Download PDFs directly from the search results
   - Use FAISS indexing for similarity-based searches

## Animations and Responsive Design

- **Animations**
  - Titles and subtitles use `fadeInUp` animations for smooth entry
  - Buttons and cards have hover effects with opacity transitions
  - Chat messages include animations for copy feedback
  - Progress bars include smooth transitions and dynamic checkpoints

- **Responsive Design**
  - Fully responsive layout for mobile, tablet, and desktop
  - Media queries ensure optimal readability and usability on all devices

## API Endpoints

- `GET /search`: Search for research papers
- `GET /search_progress`: Get current search progress
- `GET /download/<filename>`: Download CSV file
- `GET /get_csv_data/<filename>`: Get CSV data
- `GET /get_paginated_results`: Get paginated search results
- `GET /create_embedding/<filename>`: Generate embeddings for a file
- `POST /chat_conversation/<filename>`: Get AI responses for a query

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## Current Status
This is an ongoing project, and I am actively working on adding more features, including:
- Advanced PDF processing
- Advanced Retrieval-Augmented Generation (RAG) system
- Enhanced analytics and visualization tools

Stay tuned for updates!
