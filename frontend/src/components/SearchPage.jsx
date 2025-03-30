import React, { useState } from 'react';
import axios from 'axios';

const SearchPage = () => {
    const [query, setQuery] = useState('');
    const [papers, setPapers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [csvLoading, setCsvLoading] = useState(false);
    const [error, setError] = useState(null);

    const sanitizeQuery = (q) => {
        return q.replace(/[^a-zA-Z0-9\s]/g, '_');
    };

    const handleSearch = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setPapers([]);
        
        try {
            const searchResponse = await axios.get(`http://localhost:5000/search?query=${query}`);
            const csvFilename = searchResponse.data.csv_filename;
            setPapers(searchResponse.data.results.map(result => ({
                source: result.dataProviders?.[0]?.name || 'Unknown',
                title: result.title || 'Unknown',
                download_url: result.downloadUrl || '',
                year: result.yearPublished || 'Unknown'
            })));
            
            setCsvLoading(true);
            try {
                const csvResponse = await axios.get(`http://localhost:5000/get_csv_data/${csvFilename}`);
                setPapers(csvResponse.data);
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

    const handleDownload = () => {
        const sanitizedQuery = sanitizeQuery(query);
        window.location.href = `http://localhost:5000/download/${sanitizedQuery}.csv`;
    };

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-4xl font-bold text-center mb-8">Research Rover</h1>
            
            {/* Search form */}
            <form onSubmit={handleSearch} className="mb-8">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search for research papers..."
                        className="flex-1 p-2 border rounded"
                    />
                    <button 
                        type="submit"
                        disabled={loading}
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
                    >
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </div>
            </form>

            {error && (
                <div className="text-red-500 mb-4">
                    {error}
                </div>
            )}

            {papers.length > 0 && (
                <div className="mb-4 flex items-center gap-4">
                    <button
                        onClick={handleDownload}
                        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                    >
                        Download CSV
                    </button>
                    {csvLoading && (
                        <span className="text-gray-600">Loading additional data...</span>
                    )}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {papers.map((paper, index) => (
                    <div key={index} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300 overflow-hidden">
                        <div className="p-6">
                            <h2 className="text-xl font-bold text-gray-800 mb-3 line-clamp-2">{paper.title}</h2>
                            <div className="space-y-2 mb-4">
                                <p className="text-gray-600 flex items-center">
                                    <span className="font-semibold mr-2">Source: </span> 
                                    {paper.source || 'N/A'}
                                </p>
                                <p className="text-gray-600 flex items-center">
                                    <span className="font-semibold mr-2">Year: </span>
                                    {paper.year || 'N/A'}
                                </p>
                            </div>
                            {paper.download_url && (
                                <a
                                    href={paper.download_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-block bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors duration-300"
                                >
                                    Download PDF
                                </a>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SearchPage;
