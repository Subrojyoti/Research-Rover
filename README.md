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
- **Sentence Transformers**: For generating embeddings using the all-mpnet-base-v2 model
- **LangChain**: For implementing the RAG system and chat functionality

### Frontend
- **React**: UI library
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
  - Integration with CORE API for paper discovery

- **Paper Management**
  - View detailed paper metadata (title, source, year, keywords)
  - Download paper information in structured formats
  - Organized CSV export functionality for bulk data handling
  - Download all papers in PDF zipped format
  - Automatic metadata extraction and processing

- **Interactive Chat**
  - AI-powered chat interface for intelligent responses
  - Copy functionality for chat messages with visual feedback
  - Editable user messages with real-time updates
  - Context-aware responses using RAG system
  - Integration with LangChain for enhanced chat capabilities

- **Progress Tracking**
  - Embedding progress bar with dynamic stages and messages
  - Real-time updates on the embedding process
  - Search progress bar with checkpoints and animations
  - Detailed status messages for each processing stage

- **Premium UI Elements**
  - Custom-designed cards with hover effects
  - Smooth animations for titles and subtitles
  - Responsive layout for all screen sizes
  - Dynamic buttons with hover and click effects
  - Modern and intuitive user interface

- **PDF and Embedding Management**
  - Download PDFs directly from search results
  - Generate embeddings for research papers using Sentence Transformers
  - FAISS-based indexing for efficient similarity search
  - Automatic PDF processing and metadata extraction
  - Batch processing capabilities for multiple papers

- **Retrieval-Augmented Generation (RAG)**
  - Combines document retrieval with generative AI for contextual responses
  - Provides accurate and relevant answers based on indexed research papers
  - Real-time context generation from paper content
  - Intelligent query processing and response generation

- **Error Handling**
  - User-friendly error messages for failed API calls
  - Graceful fallback for incomplete processes
  - Comprehensive error logging and tracking
  - Automatic retry mechanisms for failed operations

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Node.js (Latest LTS version recommended)
- npm or yarn package manager
- Sufficient disk space for paper storage and embeddings

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Research-Rover.git
   cd Research-Rover
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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
   - Optionally specify year range and maximum results
   - View real-time search progress with the embedding progress bar
   - Browse through paginated results
   - Export results to CSV for offline analysis

2. **Managing Results**
   - View detailed paper information, including metadata
   - Download paper metadata in structured formats
   - Access paper sources and download links
   - Process papers for embedding generation
   - Download PDFs in bulk or individually

3. **Interactive Chat**
   - Use the chat interface to ask questions about your research
   - Get context-aware responses based on indexed papers
   - Copy chat responses with a single click
   - Edit user messages and get updated responses
   - View source papers for responses

4. **Embedding and PDF Management**
   - Generate embeddings for research papers
   - Download PDFs directly from the search results
   - Use FAISS indexing for similarity-based searches
   - Monitor embedding generation progress
   - Manage paper storage and organization

## API Endpoints

### Search and Results
- `GET /search`: Search for research papers with query parameters
- `GET /search_progress`: Get current search progress
- `GET /get_paginated_results`: Get paginated search results
- `GET /get_csv_data/<filename>`: Get CSV data for a specific search

### File Management
- `GET /download/<filename>`: Download CSV file
- `GET /download_pdfs/<filename>`: Download PDFs in zip format

### Embedding and Chat
- `GET /create_embedding/<filename>`: Generate embeddings for a file
- `POST /chat_conversation/<filename>`: Get AI responses for a query
- `GET /embedding_progress`: Get current embedding generation progress

## Project Structure

### Backend
```
backend/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── features/          # Core functionality modules
│   ├── search.py      # Paper search implementation
│   ├── download_pdfs.py # PDF download handling
│   └── embedding_and_indexing.py # Embedding generation
└── utils/             # Utility functions
```

### Frontend
```
frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/         # Page components
│   ├── hooks/         # Custom React hooks
│   ├── assets/        # Static assets
│   └── App.jsx        # Main application component
└── public/            # Public assets
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request. When contributing:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Current Status
This is an ongoing project, and I am actively working on adding more features, including:
- Advanced PDF processing with OCR capabilities
- Enhanced RAG system with better context understanding
- Advanced analytics and visualization tools
- Collaborative research features
- Integration with more academic databases
- Improved search algorithms and filters

## Acknowledgments
- CORE API for providing access to research papers
- Sentence Transformers for embedding generation
- FAISS for efficient similarity search
- LangChain for RAG implementation
