import React, { useState, useEffect } from 'react';
import axios from 'axios';
import SearchProgressBar from './SearchProgressBar';
import EmbeddingProgressBar from './EmbeddingProgressBar';
import ChatPage from './ChatPage';
import { Box, styled, Menu, MenuItem, IconButton } from '@mui/material';
import {useNavigate, Route} from 'react-router-dom';
import API from '../api';

// Add a default fallback URL if environment variable is not set
const backend_addrs = import.meta.env.VITE_API_URL || 'http://localhost:5000'; 
console.log("Using backend API URL:", backend_addrs);

// Configure axios with timeout
axios.defaults.timeout = 30000; // 30 seconds timeout

const BackgroundWrapper = styled(Box)({
  position: 'fixed',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  backgroundImage: 'url(/background.jpg)',
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  backgroundAttachment: 'fixed',
  filter: 'blur(8px)',
  zIndex: -1,
  transition: 'all 0.5s ease-in-out',
  opacity: 0,
  animation: 'fadeIn 0.5s ease-in-out forwards',
  '@keyframes fadeIn': {
    from: {
      opacity: 0,
    },
    to: {
      opacity: 1,
    },
  },
});

const ContentWrapper = styled(Box)({
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  position: 'relative',
  zIndex: 1,
  padding: '2rem',
  transition: 'all 0.5s ease-in-out',
  opacity: 0,
  animation: 'fadeIn 0.5s ease-in-out forwards',
  '@keyframes fadeIn': {
    from: {
      opacity: 0,
    },
    to: {
      opacity: 1,
    },
  },
});

const SearchPage = () => {
    const [query, setQuery] = useState('');
    const [prevquery, setPrevQuery] = useState('');
    const [maxResults, setMaxResults] = useState('');
    const [startYear, setStartYear] = useState('');
    const [endYear, setEndYear] = useState('');
    const [isYearRangeExpanded, setIsYearRangeExpanded] = useState(false);
    const [papers, setPapers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [csvLoading, setCsvLoading] = useState(false);
    const [error, setError] = useState(null);
    const [csvFilename, setCsvFilename] = useState('');
    const [currentStage, setCurrentStage] = useState(-1);
    const [progressMessage, setProgressMessage] = useState('');
    const [totalResults, setTotalResults] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [perPage] = useState(10);
    const [anchorEl, setAnchorEl] = useState(null);
    const open = Boolean(anchorEl);
    const [embeddingLoading, setEmbeddingLoading] = useState(false);
    const [embeddingCurrentStage, setEmbeddingCurrentStage] = useState(0);
    const [embeddingProgressMessage, setEmbeddingProgressMessage] = useState('');
    const [showChatPage, setShowChatPage] = useState(false);
    const [embeddingFilename, setEmbeddingFilename] = useState('');
    const [searchSource, setSearchSource] = useState('core'); // Default to CORE API
    
    // Add new state for confirmation dialog:
    const [showConfirmation, setShowConfirmation] = useState(false);
    const [pendingSearch, setPendingSearch] = useState(false);
    
    // Add new state for download confirmation dialog:
    const [showDownloadConfirmation, setShowDownloadConfirmation] = useState(false);
    
    const navigate = useNavigate();
    // Define the stages of the search process
    const searchStages = [
        { label: 'Initializing', description: 'Setting up search environment' },
        { label: 'Searching', description: `Querying ${searchSource === 'pubmed' ? 'PubMed' : 'CORE'} API for research papers` },
        { label: 'Processing', description: 'Extracting and validating paper information' },
        { label: 'Compiling', description: 'Processing and organizing paper data' },
        { label: 'Complete', description: 'Search process finished' }
    ];

    // Define the stages of the embedding process
    const embeddingStages = [
        { label: 'Initializing', description: 'Setting up embedding environment' },
        { label: 'Loading Model', description: 'Loading embedding model' },
        { label: 'Processing', description: 'Processing data and generating embeddings' },
        { label: 'Complete', description: 'Embedding process finished' }
    ];

    // Add this style block at the top of the file, after the imports
    const maxResultsInputStyle = `
        .max-results-input::placeholder {
            color: rgba(255, 255, 255, 0.7) !important;
            opacity: 1 !important;
        }
        .max-results-input:focus::placeholder {
            color: rgba(255, 255, 255, 0.9) !important;
        }
    `;

    // Add this style element to the component
    useEffect(() => {
        const styleElement = document.createElement('style');
        styleElement.textContent = `
            ${maxResultsInputStyle}
            
            /* Source dropdown styling */
            #source-select {
                background-color: rgba(20, 20, 40, 0.9);
                font-weight: 500;
            }
            #source-select option {
                background-color: #1a1a2e;
                color: white !important;
                padding: 10px;
                font-weight: 500;
            }
            
            /* For Firefox */
            @-moz-document url-prefix() {
                #source-select {
                    background-color: rgba(20, 20, 40, 0.9);
                }
                #source-select option {
                    background-color: #1a1a2e !important;
                }
            }
            
            /* For Webkit browsers */
            @media screen and (-webkit-min-device-pixel-ratio:0) {
                #source-select option {
                    background-color: #1a1a2e !important;
                }
            }
        `;
        document.head.appendChild(styleElement);
        return () => {
            document.head.removeChild(styleElement);
        };
    }, []);

    // Poll for progress updates
    useEffect(() => {
        let intervalId;
        
        if (loading) {
            intervalId = setInterval(async () => {
                try {
                    const response = await axios.get(`${backend_addrs}/search_progress`);
                    const { stage, message } = response.data;
                    
                    // Update the current stage and message
                    setCurrentStage(stage);
                    setProgressMessage(message);
                    
                    // If search is complete or there's an error, stop polling
                    if (stage === 4 || stage === -1) {
                        clearInterval(intervalId);
                        
                        // Add a small delay before setting loading to false to allow animations to complete
                        setTimeout(() => {
                            setLoading(false);
                        }, 1000);
                    }
                } catch (err) {
                    console.error('Error fetching progress:', err);
                }
            }, 1000); // Poll every 1 second instead of 500ms
        }
        
        return () => {
            if (intervalId) {
                clearInterval(intervalId);
            }
        };
    }, [loading]);

    // Poll for embedding progress updates
    useEffect(() => {
        let intervalId;
        
        if (embeddingLoading) {
            intervalId = setInterval(async () => {
                try {
                    const response = await axios.get(`${backend_addrs}/embedding_progress`);
                    const { stage, message } = response.data;
                    
                    // Update the current stage and message
                    setEmbeddingCurrentStage(stage);
                    setEmbeddingProgressMessage(message);
                    
                    // If embedding is complete or there's an error, stop polling
                    if (stage === 3 || stage === -1) {
                        clearInterval(intervalId);
                        
                        // Add a small delay before setting loading to false to allow animations to complete
                        setTimeout(() => {
                            setEmbeddingLoading(false);
                            if (stage === 3) {
                                // Redirect to the chat page when embedding is complete
                                navigate(`/search/chat?filename=${csvFilename}`);
                            }
                        }, 1000);
                    }
                } catch (err) {
                    console.error('Error fetching embedding progress:', err);
                }
            }, 1000); // Poll every 1 second
        }
        
        return () => {
            if (intervalId) {
                clearInterval(intervalId);
            }
        };
    }, [embeddingLoading]);

    const sanitizeQuery = (q) => {
        return q.replace(/[^a-zA-Z0-9\s]/g, '_');
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        
        // Check if maxResults is more than 1000 and show confirmation
        const maxResultsValue = maxResults === "" ? 10 : parseInt(maxResults);
        if (maxResultsValue > 1000) {
            setShowConfirmation(true);
            setPendingSearch(true);
            return;
        }
        
        // If we get here, either maxResults is <= 1000 or user confirmed
        await executeSearch();
    };

    // New function to execute the search
    const executeSearch = async () => {
        setLoading(true);
        setError(null);
        setPapers([]);
        setCurrentStage(0);
        setProgressMessage('Starting search...');
        setCurrentPage(1); // Reset to first page on new search
        setPendingSearch(false); // Reset pending search flag
        
        // Ensure we have valid values for the parameters
        const maxResultsValue = maxResults === "" ? 10 : maxResults;
        const startYearValue = startYear === "" ? 0 : startYear;
        const endYearValue = endYear === "" ? 0 : endYear;
        
        try {
            // Properly encode query parameters
            const encodedQuery = encodeURIComponent(query);
            const searchURL = `${backend_addrs}/search?query=${encodedQuery}&page=1&per_page=${perPage}&max_results=${maxResultsValue}&start_year=${startYearValue}&end_year=${endYearValue}&search_source=${searchSource}`;
            
            console.log("Sending search request to:", searchURL);
            
            const searchResponse = await API.get(searchURL);
            console.log("🔍 Search raw response:", searchResponse.data);
            const csvFilename = searchResponse.data.csv_filename;
            setCsvFilename(csvFilename);
            setPrevQuery(query);
            setTotalResults(searchResponse.data.total_results || 0)
            setTotalPages(searchResponse.data.total_pages || 1);

            navigate(`/search?filename=${csvFilename}`, { replace: true });

            setPapers(searchResponse.data.results.map(result => ({
                source: result.dataProviders?.[0]?.name || 'Unknown',
                title: result.title || 'Unknown',
                download_url: result.downloadUrl || '',
                year: result.yearPublished || 'Unknown'
            })));
            
            setCsvLoading(true);
            try {
                console.log(`Fetching CSV data from: ${backend_addrs}/get_paginated_results?filename=${csvFilename}&page=1&per_page=${perPage}`);
                const csvResponse = await axios.get(`${backend_addrs}/get_paginated_results?filename=${csvFilename}&page=1&per_page=${perPage}`);
                // Parse the CSV data and extract keywords
                const parsedPapers = csvResponse.data.results.map(paper => ({
                    ...paper,
                    // Keywords should already be a list from the backend now
                    keywords: Array.isArray(paper.keywords) ? paper.keywords : []
                }));
                setPapers(parsedPapers);
                setTotalPages(csvResponse.data.total_pages || 1);
            } catch (csvError) {
                console.error('CSV error:', csvError.response?.data || csvError.message);
                if (csvError.message && csvError.message.includes('timeout')) {
                    setError('Request timed out while fetching CSV data. Basic results are still available.');
                } else if (csvError.response?.status === 404) {
                    setError('CSV file not found. Please try your search again.');
                } else {
                    setError('Error loading detailed results. Basic results are still available.');
                }
            } finally {
                setCsvLoading(false);
            }
        } catch (err) {
            console.error('Search error:', err);
            let errorMessage = '';
            
            if (err.message && err.message.includes('timeout')) {
                errorMessage = 'Search request timed out. Please try a more specific query or reduce the number of results.';
            } else if (err.message && err.message.includes('Network Error')) {
                errorMessage = 'Cannot connect to the server. Please check your internet connection and verify the server is running.';
            } else if (err.response?.status === 404) {
                errorMessage = 'Search endpoint not found. The server may be misconfigured.';
            } else if (err.response?.data?.error) {
                errorMessage = err.response.data.error;
            } else {
                errorMessage = 'An unexpected error occurred during search. Please try again later.';
            }
            
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    // Add a useEffect to handle initial load with filename in URL
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const filenameFromUrl = params.get('filename');
        
        if (filenameFromUrl) {
            setCsvFilename(filenameFromUrl);
            // Load the results for this filename
            const loadResults = async () => {
                try {
                    const csvResponse = await axios.get(`${backend_addrs}/get_paginated_results?filename=${filenameFromUrl}&page=1&per_page=${perPage}`);
                    const parsedPapers = csvResponse.data.results.map(paper => ({
                        ...paper,
                        // Keywords should already be a list from the backend now
                        keywords: Array.isArray(paper.keywords) ? paper.keywords : []
                    }));
                    setPapers(parsedPapers);
                    setTotalPages(csvResponse.data.total_pages || 1);
                } catch (error) {
                    console.error('Error loading results:', error);
                    setError('Failed to load saved results');
                }
            };
            loadResults();
        }
    }, []);

    const handleDownloadClick = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleDownloadCSV = () => {
        handleClose();
        window.location.href = `${backend_addrs}/download/${csvFilename}`;
    };

    const handleDownloadPDFs = () => {
        handleClose();
        // Show confirmation dialog before proceeding with download
        setShowDownloadConfirmation(true);
    };
    
    // New function to actually download PDFs after confirmation
    const executeDownloadPDFs = () => {
        setShowDownloadConfirmation(false);
        // Use the endpoint to download PDFs as a zip file
        window.location.href = `${backend_addrs}/download_pdfs/${csvFilename}`;
    };

    const handlePageChange = async (newPage) => {
        if (newPage < 1 || newPage > totalPages) return;
        
        setLoading(true);
        try {
            const response = await axios.get(`${backend_addrs}/get_paginated_results?filename=${csvFilename}&page=${newPage}&per_page=${perPage}`);
            
            navigate(`/search?filename=${csvFilename}&page=${newPage}`, { replace: true });
            // Parse the CSV data and extract keywords
            const parsedPapers = response.data.results.map(paper => ({
                ...paper,
                // Keywords should already be a list from the backend now
                keywords: Array.isArray(paper.keywords) ? paper.keywords : []
            }));
            
            setPapers(parsedPapers);
            setCurrentPage(newPage);
        } catch (err) {
            console.error('Error fetching page:', err);
            setError('Failed to load page results');
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <BackgroundWrapper />
            <ContentWrapper>
                {!showChatPage ? (
                    <div className="search-container" style={{
                        display: 'flex',
                        flexDirection: 'column',
                        minHeight: '100vh',
                        width: '100%',
                        position: 'relative',
                        paddingTop: papers.length > 0 ? '9rem' : '0'
                    }}>
                        <div className="fixed-header" style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            height: papers.length > 0 ? '9rem' : '100vh',
                            background: 'linear-gradient(180deg, rgba(0, 0, 32, 0.95) 0%, rgba(0, 0, 32, 0.95) 85%, rgba(0, 0, 32, 0) 100%)',
                            backdropFilter: 'blur(10px)',
                            zIndex: 998,
                            transition: 'all 0.5s ease-in-out',
                            pointerEvents: 'none'
                        }} />

                        <div className="search-title-section" style={{ 
                            position: 'fixed',
                            top: papers.length > 0 ? '0.5rem' : '30%',
                            left: 0,
                            right: 0,
                            textAlign: 'center',
                            zIndex: 1000,
                            padding: '0 1rem',
                            backgroundColor: 'transparent',
                            transition: 'all 0.5s ease-in-out'
                        }}>
                            <h2 className="search-title" style={{
                                fontSize: '2rem',
                                fontWeight: '700',
                                color: 'white',
                                margin: 0,
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                textShadow: '0 2px 4px rgba(0,0,0,0.2)'
                            }}>Research Rover</h2>
                        </div>

                        <div className="search-section" style={{ 
                            position: 'fixed',
                            top: papers.length > 0 ? '3.5rem' : '45%',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            backgroundColor: 'rgba(255, 255, 255, 0.1)', 
                            backdropFilter: 'blur(10px)',
                            zIndex: 1000,
                            padding: '1rem',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                            borderRadius: '16px',
                            width: '90%',
                            maxWidth: '800px',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            transition: 'all 0.5s ease-in-out'
                        }}>
                            <form onSubmit={handleSearch} className="search-form" style={{
                                width: '100%'
                            }}>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '10px',
                                    width: '100%'
                                }}>
                                    <div className="search-input-group" style={{
                                        position: 'relative',
                                        flex: '1',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px'
                                    }}>
                                        {/* Source selection dropdown with clear label */}
                                        <div style={{
                                            display: 'flex', 
                                            alignItems: 'center',
                                            background: 'rgba(20, 20, 40, 0.7)',
                                            borderRadius: '25px',
                                            padding: '2px 2px 2px 12px',
                                            border: '1px solid rgba(255, 255, 255, 0.3)',
                                            height: '40px', // Match search box height
                                            boxSizing: 'border-box'
                                        }}>
                                            <span style={{
                                                color: 'white',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                marginRight: '6px',
                                                whiteSpace: 'nowrap'
                                            }}>Source:</span>
                                            <select
                                                id="source-select"
                                                value={searchSource}
                                                onChange={(e) => setSearchSource(e.target.value)}
                                                style={{
                                                    padding: '0px 30px 0px 5px',
                                                    fontSize: '14px',
                                                    backgroundColor: 'transparent',
                                                    border: 'none',
                                                    outline: 'none',
                                                    transition: 'all 0.3s ease',
                                                    color: 'white',
                                                    appearance: 'none',
                                                    WebkitAppearance: 'none',
                                                    MozAppearance: 'none',
                                                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
                                                    backgroundRepeat: 'no-repeat',
                                                    backgroundPosition: 'right 2px center',
                                                    backgroundSize: '16px',
                                                    cursor: 'pointer',
                                                    width: '90px',
                                                    fontWeight: '600'
                                                }}
                                            >
                                                <option value="core" style={{
                                                    backgroundColor: '#1a1a2e',
                                                    color: 'white',
                                                    padding: '8px'
                                                }}>ALL</option>
                                                <option value="pubmed" style={{
                                                    backgroundColor: '#1a1a2e',
                                                    color: 'white',
                                                    padding: '8px'
                                                }}>PubMed</option>
                                            </select>
                                        </div>
                                        
                                        <input
                                            type="text"
                                            id="query"
                                            name="query"
                                            value={query}
                                            onChange={(e) => setQuery(e.target.value)}
                                            placeholder="Search for research papers..."
                                            style={{
                                                width: '100%',
                                                padding: '10px 170px 10px 16px',
                                                fontSize: '15px',
                                                backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                border: '1px solid rgba(255, 255, 255, 0.3)',
                                                borderRadius: '25px',
                                                outline: 'none',
                                                transition: 'all 0.3s ease',
                                                color: 'white',
                                                caretColor: 'white',
                                                boxSizing: 'border-box',
                                                flex: 1,
                                                minWidth: 0,
                                                height: '40px' // Match dropdown height
                                            }}
                                            onFocus={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
                                            onBlur={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                                        />
                                        <input
                                            type="number"
                                            id="maxResults"
                                            name="maxResults"
                                            value={maxResults}
                                            onChange={(e) => {
                                                const value = e.target.value;
                                                if (value === "") {
                                                    setMaxResults("");
                                                } else {
                                                    const parsedValue = parseInt(value);
                                                    if (!isNaN(parsedValue) && parsedValue >=1) {
                                                        setMaxResults(parsedValue);
                                                    }
                                                }
                                            }}
                                            placeholder="# Papers"
                                            min="1"
                                            maxLength={7}
                                            style={{
                                                position: 'absolute',
                                                right: '40px',
                                                top: '50%',
                                                transform: 'translateY(-50%)',
                                                width: '120px',
                                                padding: '8px',
                                                fontSize: '14px',
                                                backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                border: '1px solid rgba(255, 255, 255, 0.3)',
                                                borderRadius: '15px',
                                                outline: 'none',
                                                transition: 'all 0.3s ease',
                                                color: 'white',
                                                caretColor: 'white',
                                                textAlign: 'center',
                                                height: '30px',
                                                lineHeight: '1',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap'
                                            }}
                                            onFocus={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
                                            onBlur={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                                            className="max-results-input"
                                        />
                                        <button 
                                            type="submit"
                                            disabled={loading}
                                            style={{
                                                position: 'absolute',
                                                right: '5px',
                                                top: '50%',
                                                transform: 'translateY(-50%)',
                                                background: 'none',
                                                border: 'none',
                                                cursor: 'pointer',
                                                padding: '6px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center'
                                            }}
                                        >
                                            <svg 
                                                width="20" 
                                                height="20" 
                                                viewBox="0 0 24 24" 
                                                fill="none" 
                                                xmlns="http://www.w3.org/2000/svg"
                                                style={{ color: loading ? 'rgba(255, 255, 255, 0.5)' : 'white' }}
                                            >
                                                <path 
                                                    d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" 
                                                    fill="currentColor"
                                                />
                                            </svg>
                                        </button>
                                    </div>
                                    
                                    <div className="year-range-container" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                        padding: '4px 12px',
                                        borderRadius: '20px',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        transition: 'all 0.3s ease',
                                        width: isYearRangeExpanded ? 'auto' : 'auto',
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            cursor: 'pointer',
                                            color: 'white',
                                            fontSize: '14px',
                                            fontWeight: '500'
                                        }}
                                        onClick={() => setIsYearRangeExpanded(!isYearRangeExpanded)}>
                                            <span>Year Range</span>
                                            <IconButton 
                                                size="small"
                                                style={{
                                                    color: 'white',
                                                    padding: '2px',
                                                    transform: isYearRangeExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                                    transition: 'transform 0.3s ease'
                                                }}
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z" fill="currentColor"/>
                                                </svg>
                                            </IconButton>
                                        </div>
                                        
                                        {isYearRangeExpanded && (
                                            <div className="year-filters" style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '5px',
                                                marginLeft: '8px',
                                                paddingLeft: '8px',
                                                borderLeft: '1px solid rgba(255, 255, 255, 0.2)'
                                            }}>
                                                <input
                                                    type="number"
                                                    id="startYear"
                                                    name="startYear"
                                                    value={startYear}
                                                    onChange={(e) => {
                                                        const value = e.target.value;
                                                        if (value === "") {
                                                            setStartYear("");
                                                        } else {
                                                            const parsedValue = parseInt(value);
                                                            if (!isNaN(parsedValue) && parsedValue >= 0) {
                                                                setStartYear(parsedValue);
                                                            }
                                                        }
                                                    }}
                                                    placeholder="YYYY"
                                                    min="0"
                                                    style={{
                                                        width: '70px',
                                                        padding: '8px',
                                                        fontSize: '14px',
                                                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                        border: '1px solid rgba(255, 255, 255, 0.3)',
                                                        borderRadius: '15px',
                                                        outline: 'none',
                                                        transition: 'all 0.3s ease',
                                                        color: 'white',
                                                        caretColor: 'white',
                                                        textAlign: 'center'
                                                    }}
                                                    onFocus={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
                                                    onBlur={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                                                />
                                                <span style={{ color: 'white' }}>-</span>
                                                <input
                                                    type="number"
                                                    id="endYear"
                                                    name="endYear"
                                                    value={endYear}
                                                    onChange={(e) => {
                                                        const value = e.target.value;
                                                        if (value === "") {
                                                            setEndYear("");
                                                        } else {
                                                            const parsedValue = parseInt(value);
                                                            if (!isNaN(parsedValue && parsedValue >= 0)) {
                                                                setEndYear(parsedValue);
                                                            }
                                                        }
                                                    }}
                                                    placeholder="YYYY"
                                                    min="0"
                                                    style={{
                                                        width: '70px',
                                                        padding: '8px',
                                                        fontSize: '14px',
                                                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                        border: '1px solid rgba(255, 255, 255, 0.3)',
                                                        borderRadius: '15px',
                                                        outline: 'none',
                                                        transition: 'all 0.3s ease',
                                                        color: 'white',
                                                        caretColor: 'white',
                                                        textAlign: 'center'
                                                    }}
                                                    onFocus={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
                                                    onBlur={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </form>

                            {error && (
                                <div className="error-message">
                                    {error}
                                </div>
                            )}
                            
                            {/* Confirmation Dialog for Large # Papers */}
                            {showConfirmation && (
                                <div style={{
                                    position: 'fixed',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                                    backdropFilter: 'blur(5px)',
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    zIndex: 2000,
                                    padding: '20px'
                                }}>
                                    <div style={{
                                        backgroundColor: '#1a1a2e',
                                        borderRadius: '12px',
                                        padding: '24px',
                                        maxWidth: '450px',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)'
                                    }}>
                                        <h3 style={{
                                            fontSize: '1.2rem',
                                            color: 'white',
                                            marginTop: 0,
                                            marginBottom: '16px'
                                        }}>Large Number of Papers</h3>
                                        
                                        <p style={{
                                            fontSize: '0.9rem',
                                            color: 'rgba(255, 255, 255, 0.8)',
                                            marginBottom: '20px',
                                            lineHeight: '1.5'
                                        }}>
                                            You've requested <strong style={{ color: '#4CAF50' }}>{maxResults}</strong> papers. 
                                            Retrieving a large number of papers may take longer to process and could impact 
                                            performance. Would you like to continue?
                                        </p>
                                        
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'flex-end',
                                            gap: '12px'
                                        }}>
                                            <button 
                                                onClick={() => {
                                                    setShowConfirmation(false);
                                                    setPendingSearch(false);
                                                }}
                                                style={{
                                                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                    color: 'white',
                                                    border: 'none',
                                                    padding: '8px 16px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.9rem',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.25)';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
                                                }}
                                            >
                                                Cancel
                                            </button>
                                            <button 
                                                onClick={() => {
                                                    setShowConfirmation(false);
                                                    executeSearch();
                                                }}
                                                style={{
                                                    backgroundColor: '#4CAF50',
                                                    color: 'white',
                                                    border: 'none',
                                                    padding: '8px 16px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.9rem',
                                                    fontWeight: '500',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = '#3e8e41';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = '#4CAF50';
                                                }}
                                            >
                                                Continue
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                            
                            {/* Confirmation Dialog for PDF Downloads */}
                            {showDownloadConfirmation && (
                                <div style={{
                                    position: 'fixed',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                                    backdropFilter: 'blur(5px)',
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    zIndex: 2000,
                                    padding: '20px'
                                }}>
                                    <div style={{
                                        backgroundColor: '#1a1a2e',
                                        borderRadius: '12px',
                                        padding: '24px',
                                        maxWidth: '450px',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)'
                                    }}>
                                        <h3 style={{
                                            fontSize: '1.2rem',
                                            color: 'white',
                                            marginTop: 0,
                                            marginBottom: '16px'
                                        }}>Download Multiple PDFs</h3>
                                        
                                        <p style={{
                                            fontSize: '0.9rem',
                                            color: 'rgba(255, 255, 255, 0.8)',
                                            marginBottom: '20px',
                                            lineHeight: '1.5'
                                        }}>
                                            Downloading all PDFs may take a significant amount of time depending on 
                                            the number of papers and their size. The server will package them into a zip file.
                                            Would you like to continue?
                                        </p>
                                        
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'flex-end',
                                            gap: '12px'
                                        }}>
                                            <button 
                                                onClick={() => {
                                                    setShowDownloadConfirmation(false);
                                                }}
                                                style={{
                                                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                                    color: 'white',
                                                    border: 'none',
                                                    padding: '8px 16px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.9rem',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.25)';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)';
                                                }}
                                            >
                                                Cancel
                                            </button>
                                            <button 
                                                onClick={executeDownloadPDFs}
                                                style={{
                                                    backgroundColor: '#4CAF50',
                                                    color: 'white',
                                                    border: 'none',
                                                    padding: '8px 16px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.9rem',
                                                    fontWeight: '500',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = '#3e8e41';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = '#4CAF50';
                                                }}
                                            >
                                                Continue Download
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                            
                            {loading && currentStage >= 0 && (
                                <>
                                    <SearchProgressBar 
                                        currentStage={currentStage} 
                                        stages={searchStages} 
                                    />
                                    <div className="progress-message">
                                        {progressMessage}
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Results section - This is the missing code that displays papers */}
                        {papers.length > 0 && !loading && !embeddingLoading && (
                            <div className="results-section" style={{
                                margin: '9rem auto 2rem auto',
                                width: '90%',
                                maxWidth: '1200px',
                                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                backdropFilter: 'blur(10px)',
                                padding: '2rem',
                                borderRadius: '16px',
                                border: '1px solid rgba(255, 255, 255, 0.2)'
                            }}>

                                <div className="results-header">
                                    <h3 className="results-title" style={{
                                        fontSize: '1.4rem',
                                        fontWeight: '700',
                                        color: 'white',
                                        marginBottom: '1rem',
                                        textShadow: '0 2px 4px rgba(0,0,0,0.2)'
                                    }}>Search Results</h3>
                                    <div className="results-summary" style={{ 
                                        marginBottom: '1.5rem',
                                        padding: '1rem',
                                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                        borderRadius: '12px',
                                        border: '1px solid rgba(255, 255, 255, 0.2)',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '8px'
                                    }}>
                                        <div style={{ 
                                            display: 'flex', 
                                            alignItems: 'center',
                                            gap: '8px'
                                        }}>
                                            <span style={{ 
                                                backgroundColor: '#4CAF50',
                                                color: 'white',
                                                padding: '4px 10px',
                                                borderRadius: '16px',
                                                fontSize: '0.9rem',
                                                fontWeight: '600',
                                                boxShadow: '0 2px 4px rgba(76, 175, 80, 0.2)'
                                            }}>
                                                {totalResults}
                                            </span>
                                            <span style={{ 
                                                fontSize: '0.9rem',
                                                color: 'white',
                                                fontWeight: '500'
                                            }}>
                                                results found for
                                            </span>
                                            <span style={{ 
                                                fontSize: '0.9rem',
                                                color: 'white',
                                                fontWeight: '600',
                                                fontStyle: 'italic'
                                            }}>
                                                "{prevquery}"
                                            </span>
                                        </div>
                                        <div style={{ 
                                            color: 'white',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                            fontSize: '0.8rem'
                                        }}>
                                            <span style={{ 
                                                width: '6px',
                                                height: '6px',
                                                borderRadius: '50%',
                                                backgroundColor: '#4CAF50',
                                                display: 'inline-block',
                                                boxShadow: '0 0 8px rgba(76, 175, 80, 0.4)'
                                            }}></span>
                                            Showing {papers.length} results (Page {currentPage} of {totalPages})
                                        </div>
                                    </div>
                                    <div className="results-actions">
                                        <button
                                            onClick={handleDownloadClick}
                                            className="btn btn-secondary"
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                padding: '12px 20px',
                                                backgroundColor: '#4CAF50',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '12px',
                                                fontSize: '15px',
                                                fontWeight: '600',
                                                cursor: 'pointer',
                                                transition: 'all 0.3s ease',
                                                boxShadow: '0 2px 4px rgba(76, 175, 80, 0.2)'
                                            }}
                                            onMouseOver={(e) => {
                                                e.target.style.backgroundColor = '#3e8e41';
                                                e.target.style.boxShadow = '0 4px 8px rgba(76, 175, 80, 0.3)';
                                                e.target.style.transform = 'translateY(-2px)';
                                            }}
                                            onMouseOut={(e) => {
                                                e.target.style.backgroundColor = '#4CAF50';
                                                e.target.style.boxShadow = '0 2px 4px rgba(76, 175, 80, 0.2)';
                                                e.target.style.transform = 'translateY(0)';
                                            }}
                                        >
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="currentColor"/>
                                            </svg>
                                            Download
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginLeft: '4px' }}>
                                                <path d="M7 10l5 5 5-5z" fill="currentColor"/>
                                            </svg>
                                        </button>
                                        <Menu
                                            anchorEl={anchorEl}
                                            open={open}
                                            onClose={handleClose}
                                            anchorOrigin={{
                                                vertical: 'bottom',
                                                horizontal: 'right',
                                            }}
                                            transformOrigin={{
                                                vertical: 'top',
                                                horizontal: 'right',
                                            }}
                                            componentsProps={{
                                                style: {
                                                    backgroundColor: 'white',
                                                    borderRadius: '8px',
                                                    marginTop: '8px',
                                                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                                                }
                                            }}
                                        >
                                            <MenuItem 
                                                onClick={handleDownloadCSV}
                                                style={{
                                                    padding: '10px 20px',
                                                    fontSize: '14px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px',
                                                    color: '#2c3e50',
                                                    transition: 'all 0.2s ease',
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = 'transparent';
                                                }}
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="#4CAF50"/>
                                                </svg>
                                                Download CSV
                                            </MenuItem>
                                            <MenuItem 
                                                onClick={handleDownloadPDFs}
                                                style={{
                                                    padding: '10px 20px',
                                                    fontSize: '14px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px',
                                                    color: '#2c3e50',
                                                    transition: 'all 0.2s ease',
                                                }}
                                                onMouseOver={(e) => {
                                                    e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
                                                }}
                                                onMouseOut={(e) => {
                                                    e.target.style.backgroundColor = 'transparent';
                                                }}
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="#4CAF50"/>
                                                </svg>
                                                Download PDFs
                                            </MenuItem>
                                        </Menu>
                                        {csvLoading && (
                                            <span className="loading-indicator" style={{
                                                color: '#2c3e50',
                                                fontSize: '14px',
                                                fontStyle: 'italic'
                                            }}>Loading additional data...</span>
                                        )}
                                    </div>
                                </div>

                                <div className="papers-grid" style={{
                                    display: 'flex', 
                                    flexDirection: 'column', 
                                    gap: '1rem',
                                    padding: '0.5rem'
                                }}>
                                    {papers.map((paper, index) => (
                                        <div key={index} className="paper-card" style={{ 
                                            width: '100%',
                                            padding: '1.5rem',
                                            borderRadius: '10px',
                                            backgroundColor: 'rgba(10, 20, 50, 0.9)',
                                            border: '1px solid rgba(255, 255, 255, 0.1)',
                                            transition: 'all 0.3s ease',
                                            marginBottom: '0.5rem',
                                            boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                                        }}
                                        onMouseOver={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-2px)';
                                            e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.3)';
                                        }}
                                        onMouseOut={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                                        }}>
                                            <h4 className="paper-title" style={{
                                                fontSize: '1.1rem',
                                                marginBottom: '1rem',
                                                color: 'white',
                                                fontWeight: '600',
                                                lineHeight: '1.4'
                                            }}>{paper.title}</h4>
                                            
                                            <div style={{
                                                display: 'flex',
                                                flexWrap: 'wrap',
                                                gap: '0.8rem',
                                                marginBottom: '1.2rem'
                                            }}>
                                                <div style={{ 
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem'
                                                }}>
                                                    <span style={{ 
                                                        color: '#4CAF50',
                                                        fontWeight: '600',
                                                        fontSize: '0.85rem'
                                                    }}>Source</span>
                                                    <span style={{ 
                                                        color: 'white',
                                                        fontSize: '0.85rem'
                                                    }}>{paper.source || 'N/A'}</span>
                                                </div>
                                                
                                                <div style={{ 
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem'
                                                }}>
                                                    <span style={{ 
                                                        color: '#4CAF50',
                                                        fontWeight: '600',
                                                        fontSize: '0.85rem'
                                                    }}>Year</span>
                                                    <span style={{ 
                                                        color: 'white',
                                                        fontSize: '0.85rem'
                                                    }}>{paper.year || 'N/A'}</span>
                                                </div>
                                            </div>

                                            {paper.keywords && paper.keywords.length > 0 && (
                                                <div className="keywords-container" style={{
                                                    display: 'flex',
                                                    flexWrap: 'wrap',
                                                    gap: '0.4rem',
                                                    marginBottom: '1rem'
                                                }}>
                                                    {paper.keywords.map((keyword, idx) => (
                                                        <span key={idx} style={{
                                                            backgroundColor: 'rgba(76, 175, 80, 0.15)',
                                                            padding: '3px 8px',
                                                            borderRadius: '12px',
                                                            fontSize: '0.75rem',
                                                            color: '#4CAF50',
                                                            fontWeight: '500',
                                                            transition: 'all 0.2s ease'
                                                        }}
                                                        onMouseOver={(e) => {
                                                            e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.25)';
                                                            e.target.style.transform = 'translateY(-1px)';
                                                        }}
                                                        onMouseOut={(e) => {
                                                            e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.15)';
                                                            e.target.style.transform = 'translateY(0)';
                                                        }}>
                                                            {keyword}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            {paper.download_url && (
                                                <a
                                                    href={paper.download_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        width: '140px',
                                                        padding: '0.4rem 0.5rem',
                                                        backgroundColor: '#4CAF50',
                                                        color: 'white',
                                                        textDecoration: 'none',
                                                        borderRadius: '6px',
                                                        fontSize: '0.75rem',
                                                        fontWeight: '500',
                                                        transition: 'all 0.3s ease',
                                                        boxShadow: '0 2px 8px rgba(76, 175, 80, 0.3)',
                                                        whiteSpace: 'nowrap'
                                                    }}
                                                    onMouseOver={(e) => {
                                                        e.target.style.backgroundColor = '#3e8e41';
                                                        e.target.style.boxShadow = '0 4px 12px rgba(76, 175, 80, 0.4)';
                                                        e.target.style.transform = 'translateY(-2px)';
                                                    }}
                                                    onMouseOut={(e) => {
                                                        e.target.style.backgroundColor = '#4CAF50';
                                                        e.target.style.boxShadow = '0 2px 8px rgba(76, 175, 80, 0.3)';
                                                        e.target.style.transform = 'translateY(0)';
                                                    }}
                                                >
                                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{marginRight: '4px'}}>
                                                        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="currentColor"/>
                                                    </svg>
                                                    Download PDF
                                                </a>
                                            )}
                                        </div>
                                    ))}
                                </div>

                                {/* Pagination controls */}
                                {totalPages > 1 && (
                                    <div className="pagination-controls" style={{
                                        display: 'flex',
                                        justifyContent: 'center',
                                        alignItems: 'center',
                                        marginTop: '2rem',
                                        marginBottom: '1rem',
                                        gap: '1rem'
                                    }}>
                                        <button
                                            onClick={() => handlePageChange(currentPage - 1)}
                                            disabled={currentPage === 1 || loading}
                                            style={{
                                                padding: '8px 16px',
                                                backgroundColor: currentPage === 1 ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.2)',
                                                color: currentPage === 1 ? 'rgba(255, 255, 255, 0.5)' : 'white',
                                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                                borderRadius: '8px',
                                                cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                transition: 'all 0.3s ease'
                                            }}
                                            onMouseOver={(e) => {
                                                if (currentPage !== 1 && !loading) {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
                                                    e.target.style.transform = 'translateY(-2px)';
                                                }
                                            }}
                                            onMouseOut={(e) => {
                                                if (currentPage !== 1 && !loading) {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                                                    e.target.style.transform = 'translateY(0)';
                                                }
                                            }}
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L13.17 12z" fill="currentColor"/>
                                            </svg>
                                            Previous
                                        </button>
                                        
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            color: 'white',
                                            fontSize: '14px',
                                            fontWeight: '500'
                                        }}>
                                            <span>Page {currentPage} of {totalPages}</span>
                                        </div>
                                        
                                        <button
                                            onClick={() => handlePageChange(currentPage + 1)}
                                            disabled={currentPage === totalPages || loading}
                                            style={{
                                                padding: '8px 16px',
                                                backgroundColor: currentPage === totalPages ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.2)',
                                                color: currentPage === totalPages ? 'rgba(255, 255, 255, 0.5)' : 'white',
                                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                                borderRadius: '8px',
                                                cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                fontSize: '14px',
                                                fontWeight: '500',
                                                transition: 'all 0.3s ease'
                                            }}
                                            onMouseOver={(e) => {
                                                if (currentPage !== totalPages && !loading) {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
                                                    e.target.style.transform = 'translateY(-2px)';
                                                }
                                            }}
                                            onMouseOut={(e) => {
                                                if (currentPage !== totalPages && !loading) {
                                                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                                                    e.target.style.transform = 'translateY(0)';
                                                }
                                            }}
                                        >
                                            Next
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z" fill="currentColor"/>
                                            </svg>
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Rover Chat Icon - Moved outside results section */}
                        {papers.length > 0 && !embeddingLoading && (
                            <div className="rover-chat-icon" style={{
                                position: 'fixed',
                                bottom: '2rem',
                                right: '2rem',
                                cursor: 'pointer',
                                transition: 'all 0.3s ease',
                                zIndex: 1000,
                                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                backdropFilter: 'blur(10px)',
                                borderRadius: '50%',
                                padding: '8px',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                            }}
                            onClick={async () => {
                                try {
                                    setEmbeddingLoading(true);
                                    setEmbeddingCurrentStage(0);
                                    setEmbeddingProgressMessage('Starting embedding process...');
                                    setEmbeddingFilename(csvFilename);
                                    
                                    // Clear the page content
                                    setPapers([]);
                                    setLoading(false);
                                    setError(null);
                                    setCurrentStage(-1);
                                    setProgressMessage('');
                                    setTotalResults(0);
                                    setCurrentPage(1);
                                    setTotalPages(1);
                                    
                                    // Call the embedding endpoint
                                    await axios.get(`${backend_addrs}/create_embedding/${csvFilename}`);
                                } catch (error) {
                                    console.error('Error creating embeddings:', error);
                                    setEmbeddingLoading(false);
                                }
                            }}
                            onMouseOver={(e) => {
                                e.currentTarget.style.transform = 'scale(1.1)';
                                e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
                            }}
                            onMouseOut={(e) => {
                                e.currentTarget.style.transform = 'scale(1)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                            }}>
                                <img 
                                    src="/rover.png" 
                                    alt="Chat with Rover" 
                                    style={{
                                        width: '60px',
                                        height: '60px',
                                        borderRadius: '50%',
                                        display: 'block'
                                    }}
                                />
                            </div>
                        )}

                        {/* Embedding Progress */}
                        {embeddingLoading && (
                            <div className="embedding-progress-container" style={{
                                position: 'fixed',
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)',
                                width: '80%',
                                maxWidth: '800px',
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                backdropFilter: 'blur(10px)',
                                borderRadius: '16px',
                                padding: '2rem',
                                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                zIndex: 1000,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                gap: '1.5rem',
                                animation: 'fadeIn 0.5s ease-in-out'
                            }}>
                                <h2 style={{
                                    color: 'white',
                                    fontSize: '1.8rem',
                                    fontWeight: '600',
                                    margin: 0,
                                    textAlign: 'center'
                                }}>Preparing Research Rover</h2>
                                
                                <p style={{
                                    color: 'rgba(255, 255, 255, 0.8)',
                                    fontSize: '1rem',
                                    textAlign: 'center',
                                    margin: '0 0 1rem 0'
                                }}>
                                    Research Rover is analyzing your research papers to provide intelligent responses.
                                    This may take a few moments.
                                </p>
                                
                                <EmbeddingProgressBar 
                                    currentStage={embeddingCurrentStage} 
                                    stages={embeddingStages} 
                                />
                                
                                <p style={{
                                    color: 'rgba(255, 255, 255, 0.8)',
                                    fontSize: '0.9rem',
                                    textAlign: 'center',
                                    margin: 0,
                                    fontStyle: 'italic'
                                }}>
                                    {embeddingProgressMessage}
                                </p>
                            </div>
                        )}
                    </div>
                ) : (
                    // <ChatPage filename={embeddingFilename} />
                    <ChatPage filename={embeddingFilename} />   
                )}
            </ContentWrapper>
        </>
    );
};

export default SearchPage;
