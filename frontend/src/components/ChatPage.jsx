import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import { Box, styled } from '@mui/material';


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
    filter: 'blur(12px)', // Increased blur
    zIndex: -1,
    opacity: 0,
    animation: 'fadeIn 0.5s ease-in-out forwards',
    '@keyframes fadeIn': {
        from: { opacity: 0 },
        to: { opacity: 1 },
    },
});

const ContentWrapper = styled(Box)({
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    zIndex: 1,
    padding: '2rem',
    opacity: 0,
    animation: 'fadeIn 0.5s ease-in-out forwards',
    '@keyframes fadeIn': {
        from: { opacity: 0 },
        to: { opacity: 1 },
    },
});

// Add scrollbar styling
const CustomScrollbar = {
    '&::WebkitScrollbar': {
        width: '6px',
    },
    '&::WebkitScrollbarTrack': {
        background: 'rgba(18, 18, 18, 0.95)',
    },
    '&::WebkitScrollbarThumb': {
        background: 'rgba(76, 175, 80, 0.5)',
        borderRadius: '3px',
        '&:hover': {
            background: 'rgba(76, 175, 80, 0.7)',
        }
    }
};

// Add loadingdots animation
const LoadingDots = () => {
    return (
        <div style={{
            display: 'flex',
            gap: '4px',
            padding: '8px 16px',
            alignItems: 'center'
        }}>
            {[1, 2, 3].map((dot) => (
                <div key={dot} style={{
                    width: '6px',
                    height: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.7)',
                    borderRadius: '50%',
                    animation: `bounce 1.2s infinite ease-in-out`,
                    animationDelay: `${(dot - 1) * 0.16}s`
                    }} />
            ))}
            <style>
                {`
                    @keyframes bounce {
                        0%, 80%, 100% { transform: translateY(0); }
                        40% { transform: translateY(-6px); }
                    }
                `}
            </style>
        </div>
    );
};

const TypeWriter = ({ text, speed = 10 }) => {
    const [displayedText, setDisplayedText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timer = setTimeout(() => {
                setDisplayedText(prev => prev + text[currentIndex]);
                setCurrentIndex(currentIndex + 1);
            }, speed);

            return () => clearTimeout(timer);
        }
    }, [currentIndex, text, speed]);

    return <>{displayedText}</>;
};

const ChatPage = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentStage, setCurrentStage] = useState(0);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const filename = queryParams.get('filename');

    const chatStages = [
        { label: 'Processing', description: 'Processing your message' },
        { label: 'Searching', description: 'Searching relevant context' },
        { label: 'Generating', description: 'Generating response' },
        { label: 'Complete', description: 'Response ready' }
    ];

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e) => {
        e?.preventDefault();
        if (!inputMessage.trim() || loading) return;

        const userMessage = inputMessage;
        setInputMessage('');
        // Add user message to chat
        setMessages(prev => [...prev, { text: userMessage, isUser: true }]);

        // Set loading state and current stage
        setMessages(prev => [...prev, { text: "", isUser: false, isloading: true }]);

        setLoading(true);
        setCurrentStage(0);

        try {
            const response = await axios.post(`http://localhost:5000/chat_conversation/${filename}`, {
                query: userMessage
            });

            setMessages(prev => [...prev.slice(0, -1), { text: response.data.answer, isUser: false }]);
            setCurrentStage(3);
        } catch (err) {
            // Remove loading message if error occurs
            setMessages(prev => prev.slice(0, -1));
            setError('Failed to get response');
            console.error('Chat error:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <BackgroundWrapper />
            <ContentWrapper>
                <div className="chat-container" style={{
                    maxWidth: '1000px',
                    width: '80%',
                    margin: '0 auto',
                    height: '81vh',
                    display: 'flex',
                    flexDirection: 'column',
                    backgroundColor: 'rgba(18, 18, 18, 0.8)',
                    backdropFilter: 'blur(10px)',
                    borderRadius: '16px',
                    border: '1px solid rgba(76, 175, 80, 0.1)',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
                    padding: '1.5rem',
                    position: 'fixed',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 10,
                    overflow: 'hidden'
                }}>
                    <div style={{
                        position: 'absolute',
                        top: '1.5rem',
                        left: '1.5rem',
                        right: '1.5rem',
                        bottom: '1.5rem',
                        backgroundColor: 'rgba(22, 22, 22, 0.98)',
                        borderRadius: '12px',
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden'
                    }}>
                        {/* Header */}
                        <div style={{
                            padding: '1.2rem 1.5rem',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                            backgroundColor: 'rgba(15, 15, 15, 0.95)',
                        }}>
                            <h1 style={{
                                color: 'white',
                                fontSize: '1.5rem',
                                margin: 0,
                                fontFamily: '"Inter", sans-serif',
                                fontWeight: 600,
                            }}>Research Rover</h1>
                        </div>

                        {/* Messages Container */}
                        <div className="messages-container" style={{
                            flex: 1,
                            overflowY: 'auto',
                            padding: '1.5rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '1.5rem',
                            backgroundColor: 'transparent',
                            ...CustomScrollbar
                        }}>
                            {messages.map((message, index) => (
                                <div
                                    key={index}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: '1rem',
                                        alignSelf: message.isUser ? 'flex-end' : 'flex-start',
                                        maxWidth: '75%',
                                    }}
                                >
                                    {!message.isUser && (
                                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                                            <img
                                                src="/rover.png"
                                                alt="AI"
                                                style={{
                                                    width: '42px',
                                                    height: '42px',
                                                    borderRadius: '12px',
                                                    objectFit: 'cover',
                                                }}
                                            />
                                            {message.isloading && <LoadingDots />}
                                        </div>   
                                    )}
                                    {!message.isloading && (
                                        <div style={{
                                            backgroundColor: message.isUser 
                                                ? 'rgba(18, 18, 18, 0.95)'
                                                : 'rgba(255, 255, 255, 0.08)',
                                            padding: '1.2rem 1.4rem',
                                            borderRadius: '16px',
                                            color: 'white',
                                            fontSize: '0.95rem',
                                            lineHeight: '1.6',
                                            fontFamily: '"Inter", sans-serif',
                                            border: message.isUser 
                                                ? '1px solid rgba(76, 175, 80, 0.5)'
                                                : '1px solid rgba(255, 255, 255, 0.1)',
                                        }}>
                                            {message.isUser ? message.text : <TypeWriter text={message.text} speed={5} />}
                                        </div>
                                    )}
                                    {message.isUser && (
                                        <div style={{
                                            width: '42px',
                                            height: '42px',
                                            borderRadius: '16px',
                                            backgroundColor: 'rgba(76, 175, 80, 0.2)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            border: '1px solid rgba(76, 175, 80, 0.3)',
                                        }}>
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="#4CAF50">
                                                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                                            </svg>
                                        </div>
                                    )}
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Chat Input */}
                        <form onSubmit={handleSendMessage} style={{
                            padding: '1.2rem',
                            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                            backgroundColor: 'rgba(15, 15, 15, 0.95)',
                        }}>
                            <div style={{
                                display: 'flex',
                                alignItems: 'flex-end',
                                gap: '0.8rem',
                                backgroundColor: 'rgba(28, 28, 28, 0.95)',
                                borderRadius: '12px',
                                padding: '0.4rem',
                                border: '1px solid rgba(255, 255, 255, 0.1)',
                            }}>
                                <textarea
                                    type="text"
                                    value={inputMessage}
                                    onChange={(e) => setInputMessage(e.target.value)}
                                    placeholder="Ask your query..."
                                    rows={1}
                                    style={{
                                        flex: 1,
                                        padding: '0.8rem 1.2rem',
                                        fontSize: '0.95rem',
                                        backgroundColor: 'transparent',
                                        border: 'none',
                                        outline: 'none',
                                        color: 'white',
                                        fontFamily: '"Inter", sans-serif',
                                        caretColor: '#4CAF50',
                                        resize: 'none',
                                        maxHeight: '120px',
                                        minHeight: '46px',
                                        overflowY: 'auto',
                                        scrollbarWidth: 'none',
                                        '&::WebkitScrollbar': {
                                            display: 'none',
                                        },
                                        msOverflowStyle: 'none',
                                    }}
                                />
                                <button
                                    type="submit"
                                    disabled={loading}
                                    style={{
                                        width: '46px',
                                        height: '46px',
                                        backgroundColor: loading ? 'rgba(76, 175, 80, 0.3)' : '#4CAF50',
                                        border: 'none',
                                        borderRadius: '10px',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        transition: 'all 0.2s ease',
                                        transform: loading ? 'none' : 'scale(1)',
                                        '&:hover': {
                                            backgroundColor: '#3d8c40',
                                            transform: 'scale(0.98)',
                                        }
                                    }}
                                >
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                    </svg>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </ContentWrapper>
        </>
    );
};

export default ChatPage;
