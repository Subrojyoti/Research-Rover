import React, { useState, useEffect } from 'react';
import axios from 'axios';
import SearchProgressBar from './SearchProgressBar';
import { Box, styled, Menu, MenuItem } from '@mui/material';

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
    
    // Define the stages of the search process
    const searchStages = [
        { label: 'Initializing', description: 'Setting up search environment' },
        { label: 'Searching', description: 'Querying CORE API for research papers' },
        { label: 'Processing', description: 'Extracting and validating paper information' },
        { label: 'Compiling', description: 'Processing and organizing paper data' },
        { label: 'Complete', description: 'Search process finished' }
    ];

    // Poll for progress updates
    useEffect(() => {
        let intervalId;
        
        if (loading) {
            intervalId = setInterval(async () => {
                try {
                    const response = await axios.get('http://localhost:5000/search_progress');
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

    const sanitizeQuery = (q) => {
        return q.replace(/[^a-zA-Z0-9\s]/g, '_');
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setPapers([]);
        setCurrentStage(0);
        setProgressMessage('Starting search...');
        setCurrentPage(1); // Reset to first page on new search
        
        try {
            const searchResponse = await axios.get(`http://localhost:5000/search?query=${query}&page=1&per_page=${perPage}`);
            const csvFilename = searchResponse.data.csv_filename;
            setCsvFilename(csvFilename);
            setTotalResults(searchResponse.data.total_results || 0);
            setTotalPages(searchResponse.data.total_pages || 1);
            setPapers(searchResponse.data.results.map(result => ({
                source: result.dataProviders?.[0]?.name || 'Unknown',
                title: result.title || 'Unknown',
                download_url: result.downloadUrl || '',
                year: result.yearPublished || 'Unknown'
            })));
            
            setCsvLoading(true);
            try {
                const csvResponse = await axios.get(`http://localhost:5000/get_paginated_results?filename=${csvFilename}&page=1&per_page=${perPage}`);
                // Parse the CSV data and extract keywords
                const parsedPapers = csvResponse.data.results.map(paper => ({
                    ...paper,
                    // Parse keywords if they're in string format
                    keywords: paper.keywords ? 
                        (typeof paper.keywords === 'string' ? 
                            JSON.parse(paper.keywords.replace(/'/g, '"')) : 
                            paper.keywords) : 
                        []
                }));
                setPapers(parsedPapers);
                setTotalPages(csvResponse.data.total_pages || 1);
            } catch (csvError) {
                console.error('CSV error:', csvError.response?.data);
            } finally {
                setCsvLoading(false);
            }
        } catch (err) {
            const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch results';
            setError(errorMessage);
            console.error('Search error:', errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadClick = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleDownloadCSV = () => {
        handleClose();
        window.location.href = `http://localhost:5000/download/${csvFilename}`;
    };

    const handleDownloadPDFs = () => {
        handleClose();
        // Use the new endpoint to download PDFs as a zip file
        window.location.href = `http://localhost:5000/download_pdfs/${csvFilename}`;
    };

    const handlePageChange = async (newPage) => {
        if (newPage < 1 || newPage > totalPages) return;
        
        setLoading(true);
        try {
            const response = await axios.get(`http://localhost:5000/get_paginated_results?filename=${csvFilename}&page=${newPage}&per_page=${perPage}`);
            
            // Parse the CSV data and extract keywords
            const parsedPapers = response.data.results.map(paper => ({
                ...paper,
                // Parse keywords if they're in string format
                keywords: paper.keywords ? 
                    (typeof paper.keywords === 'string' ? 
                        JSON.parse(paper.keywords.replace(/'/g, '"')) : 
                        paper.keywords) : 
                    []
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
                        maxWidth: '600px',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        transition: 'all 0.5s ease-in-out'
                    }}>
                        <form onSubmit={handleSearch} className="search-form" style={{
                            width: '100%'
                        }}>
                            <div className="search-input-group" style={{
                                position: 'relative',
                                width: '100%'
                            }}>
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Search for research papers..."
                                    style={{
                                        width: '100%',
                                        padding: '10px 40px 10px 16px',
                                        fontSize: '15px',
                                        backgroundColor: 'rgba(255, 255, 255, 0.15)',
                                        border: '1px solid rgba(255, 255, 255, 0.3)',
                                        borderRadius: '25px',
                                        outline: 'none',
                                        transition: 'all 0.3s ease',
                                        color: 'white',
                                        caretColor: 'white'
                                    }}
                                    onFocus={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'}
                                    onBlur={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.15)'}
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
                        </form>

                        {error && (
                            <div className="error-message">
                                {error}
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

                    {papers.length > 0 && (
                        <>
                            <div className="results-section" style={{ 
                                position: 'relative',
                                width: '90%',
                                maxWidth: '1200px',
                                margin: '0 auto',
                                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                backdropFilter: 'blur(10px)',
                                borderRadius: '16px',
                                padding: '1.5rem',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                zIndex: 1,
                                transition: 'all 0.5s ease-in-out',
                                opacity: 0,
                                animation: 'fadeIn 0.5s ease-in-out forwards 0.3s'
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
                                                "{query}"
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
                                            PaperProps={{
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
                                        <div key={index} className="card paper-card" style={{ 
                                            width: '100%',
                                            padding: '0.75rem',
                                            borderRadius: '10px',
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                                            backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                            backdropFilter: 'blur(10px)',
                                            border: '1px solid rgba(255, 255, 255, 0.2)',
                                            transition: 'all 0.3s ease',
                                            marginBottom: '0.5rem'
                                        }}
                                        onMouseOver={(e) => {
                                            e.currentTarget.style.transform = 'translateY(-2px)';
                                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                                        }}
                                        onMouseOut={(e) => {
                                            e.currentTarget.style.transform = 'translateY(0)';
                                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                        }}>
                                            <h4 className="paper-title" style={{
                                                fontSize: '1.1rem',
                                                marginBottom: '0.5rem',
                                                color: '#2c3e50',
                                                fontWeight: '600',
                                                lineHeight: '1.4'
                                            }}>{paper.title}</h4>
                                            
                                            <div className="paper-details" style={{
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.25rem',
                                                marginBottom: '0.5rem'
                                            }}>
                                                <p className="paper-source" style={{ 
                                                    margin: 0,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '6px',
                                                    color: '#2c3e50',
                                                    fontSize: '0.8rem'
                                                }}>
                                                    <span style={{ 
                                                        fontWeight: '600',
                                                        color: '#4CAF50',
                                                        fontSize: '0.7rem',
                                                        padding: '1px 4px',
                                                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                                        borderRadius: '3px'
                                                    }}>Source</span>
                                                    {paper.source || 'N/A'}
                                                </p>
                                                <p className="paper-year" style={{ 
                                                    margin: 0,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '6px',
                                                    color: '#2c3e50',
                                                    fontSize: '0.8rem'
                                                }}>
                                                    <span style={{ 
                                                        fontWeight: '600',
                                                        color: '#4CAF50',
                                                        fontSize: '0.7rem',
                                                        padding: '1px 4px',
                                                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                                        borderRadius: '3px'
                                                    }}>Year</span>
                                                    {paper.year || 'N/A'}
                                                </p>
                                            </div>

                                            {paper.keywords && paper.keywords.length > 0 && (
                                                <div className="keywords-container" style={{
                                                    display: 'flex',
                                                    flexWrap: 'wrap',
                                                    gap: '0.3rem',
                                                    marginBottom: '0.75rem'
                                                }}>
                                                    {paper.keywords.map((keyword, idx) => (
                                                        <span key={idx} style={{
                                                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                                            padding: '1px 6px',
                                                            borderRadius: '10px',
                                                            fontSize: '0.7rem',
                                                            color: '#4CAF50',
                                                            fontWeight: '500',
                                                            transition: 'all 0.2s ease'
                                                        }}
                                                        onMouseOver={(e) => {
                                                            e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.2)';
                                                            e.target.style.transform = 'translateY(-1px)';
                                                        }}
                                                        onMouseOut={(e) => {
                                                            e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
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
                                                    className="btn btn-primary paper-download"
                                                    style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        gap: '6px',
                                                        padding: '6px 12px',
                                                        backgroundColor: '#4CAF50',
                                                        color: 'white',
                                                        textDecoration: 'none',
                                                        borderRadius: '6px',
                                                        fontSize: '0.8rem',
                                                        fontWeight: '500',
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
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" fill="currentColor"/>
                                                    </svg>
                                                    Download PDF
                                                </a>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                
                                {/* Pagination Controls */}
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
                                                <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" fill="currentColor"/>
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
                        </>
                    )}
                </div>
            </ContentWrapper>
        </>
    );
};

export default SearchPage;
