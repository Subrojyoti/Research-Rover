import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import { Box, styled, keyframes } from '@mui/material';

const backend_addrs = import.meta.env.VITE_API_URL;
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

const BackgroundOverlay = styled(Box)({
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    background: 'rgba(18, 32, 50, 0.65)', // dark overlay
    zIndex: -1,
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
        background: 'traparent',
    },
    '&::WebkitScrollbarTrack': {
        background: 'rgba(0, 0, 0, 0.2)',
        backdropFilter: 'blur(8px)',
        borderRadius: '10px',
        margin: '4px',
    },
    '&::WebkitScrollbarThumb': {
        background: 'rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '10px',
        '&:hover': {
            background: 'rgba(0, 0, 0, 0.8)',
        }
    },
    scrollbarWidth: 'thin',
    scrollbarColor: 'rgba(0, 0, 0, 0.6) rgba(0, 0, 0, 0.2)',
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
    const [displayedParts, setDisplayedParts] = useState([]);
    const [currentPartIndex, setCurrentPartIndex] = useState(0);
    const [currentCharIndex, setCurrentCharIndex] = useState(0);

    useEffect(() => {
        // If text is an array of parts (from formatResponseWithClickableLinks)
        if (Array.isArray(text)) {
            if (currentPartIndex >= text.length) {
                return;
            }

            const currentPart = text[currentPartIndex];
            
            // If current part is a React element (link), add it immediately
            if (React.isValidElement(currentPart)) {
                const timer = setTimeout(() => {
                    setDisplayedParts(prev => [...prev, currentPart]);
                    setCurrentPartIndex(prev => prev + 1);
                    setCurrentCharIndex(0);
                }, speed);
                return () => clearTimeout(timer);
            }
            
            // If current part is text, type it out character by character
            if (currentCharIndex < currentPart.length) {
                const timer = setTimeout(() => {
                    if (currentCharIndex === 0) {
                        setDisplayedParts(prev => [...prev, currentPart[0]]);
                    } else {
                        setDisplayedParts(prev => {
                            const newParts = [...prev];
                            newParts[newParts.length - 1] += currentPart[currentCharIndex];
                            return newParts;
                        });
                    }
                    setCurrentCharIndex(prev => prev + 1);
                }, speed);
                return () => clearTimeout(timer);
            } else {
                // Move to next part
                setCurrentPartIndex(prev => prev + 1);
                setCurrentCharIndex(0);
            }
        } else {
            // Handle regular text (old behavior)
            if (currentCharIndex < text.length) {
                const timer = setTimeout(() => {
                    setDisplayedParts([text.slice(0, currentCharIndex + 1)]);
                    setCurrentCharIndex(prev => prev + 1);
                }, speed);
                return () => clearTimeout(timer);
            }
        }
    }, [text, currentPartIndex, currentCharIndex, speed]);

    return <>{displayedParts}</>;
};

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(-50%) translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(-50%) translateX(0);
  }
`;

const formatResponseWithClickableLinks = (text, downloadUrls) => {
    if (!text) return [''];
    
    const citationRegex = /\[(\d+)\]/g;
    let parts = [];
    let lastIndex = 0;
    let match;
    
    while ((match = citationRegex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            parts.push(text.substring(lastIndex, match.index));
        }
        
        const citationNumber = parseInt(match[1]) - 1;
        const downloadUrl = downloadUrls[citationNumber];
        
        parts.push(
            <a
                key={`citation-${match.index}`}
                href={downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                    color: '#4CAF50',
                    textDecoration: 'none',
                    fontWeight: 'bold',
                    padding: '0 2px',
                    borderRadius: '4px',
                    transition: 'background-color 0.2s',
                    cursor: downloadUrl ? 'pointer' : 'not-allowed',
                }}
                onMouseEnter={(e) => {
                    e.target.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
                    e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                    e.target.style.backgroundColor = 'transparent';
                    e.currentTarget.style.transform = 'scale(1)';
                }}
            >
                <sup>[{match[1]}]</sup>
            </a>
        );
        
        lastIndex = match.index + match[0].length;
    }
    
    if (lastIndex < text.length) {
        parts.push(text.substring(lastIndex));
    }
    
    return parts;
};

const adjustTextareaHeight = (element) => {
    element.style.height = 'auto';
    element.style.height = `${element.scrollHeight}px`;
};

const ChatPage = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [currentStage, setCurrentStage] = useState(0);
    const [error, setError] = useState(null);
    // const [copiedMessageId, setCopiedMessageId] = useState(null);
    const [editingMessageId, setEditingMessageId] = useState(null);
    const [editingMessage, setEditingMessage] = useState('');
    const [copyingStates, setCopyingStates] = useState({});
    const messagesEndRef = useRef(null);
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const filename = queryParams.get('filename');


    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleCopyText = async (text, messageId) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopyingStates(prev => ({ ...prev, [messageId]: true }));
            setTimeout(() => {
                setCopyingStates(prev => ({ ...prev, [messageId]: false }));
            }, 2000); // Message disappears after 2 seconds
        } catch (err) {
            console.error("Failed to copy text:", err)
        }
    };

    const handleEditMessage = (messageText, index) => {
        setEditingMessageId(index);
        setEditingMessage(messageText);
        setInputMessage(messageText);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e) => {
        e?.preventDefault();
        if (!inputMessage.trim() || loading) return;
    
        const userMessage = inputMessage;
        setInputMessage('');
    
        if (editingMessageId !== null) {
            // Handle edited message
            setMessages(prev => {
                const newMessages = [...prev];
                // Update the edited message
                newMessages[editingMessageId] = { 
                    text: userMessage, 
                    isUser: true 
                };
                // Remove subsequent AI response
                if (newMessages[editingMessageId + 1] && !newMessages[editingMessageId + 1].isUser) {
                    newMessages.splice(editingMessageId + 1, 1);
                }
                // Add loading message
                newMessages.splice(editingMessageId + 1, 0, {
                    isUser: false,
                    isloading: true
                });
                return newMessages;
            });
    
            setLoading(true);
    
            try {
                const response = await axios.post(`${backend_addrs}/chat_conversation/${filename}`, {
                    query: userMessage
                });
    
                setMessages(prev => {
                    const newMessages = [...prev];
                    // Replace loading message with actual response
                    newMessages.splice(editingMessageId + 1, 1, {
                        text: response.data.responseText,
                        downloadUrls: response.data.downloadUrls,
                        isUser: false,
                        isloading: false
                    });
                    return newMessages;
                });
            } catch (err) {
                setError('Failed to get response');
                console.error('Chat error:', err);
                // Remove loading message on error
                setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages.splice(editingMessageId + 1, 1);
                    return newMessages;
                });
            } finally {
                setLoading(false);
                setEditingMessageId(null);
                setEditingMessage('');
            }
        } else {
            // Handle new message
            setMessages(prev => [...prev, { 
                text: userMessage, 
                isUser: true 
            }]);
    
            // Add loading message
            setMessages(prev => [...prev, {
                isUser: false,
                isloading: true
            }]);
    
            setLoading(true);
    
            try {
                const response = await axios.post(`${backend_addrs}/chat_conversation/${filename}`, {
                    query: userMessage
                });
    
                // Replace loading message with actual response
                setMessages(prev => [
                    ...prev.slice(0, -1),
                    {
                        text: response.data.responseText,
                        downloadUrls: response.data.downloadUrls,
                        isUser: false,
                        isloading: false
                    }
                ]);
            } catch (err) {
                setError('Failed to get response');
                console.error('Chat error:', err);
                // Remove loading message on error
                setMessages(prev => [...prev.slice(0, -1)]);
            } finally {
                setLoading(false);
            }
        }
    };

    return (
        <>
            <BackgroundWrapper />
            <BackgroundOverlay />
            <ContentWrapper>
                <div className="chat-container" style={{
                    maxWidth: '1400px',
                    width: '97%',
                    margin: '0 auto',
                    height: '85vh',
                    display: 'flex',
                    flexDirection: 'column',
                    backgroundColor: 'rgba(30, 58, 95, 0.90)', // theme primary
                    backdropFilter: 'blur(10px)',
                    borderRadius: '12px',
                    border: '1.5px solid rgba(76, 175, 80, 0.15)',
                    boxShadow: '0 12px 48px rgba(0,0,0,0.35)',
                    padding: '0.5rem',
                    position: 'fixed',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    zIndex: 10,
                    overflow: 'hidden',
                }}>
                    <div style={{
                        position: 'absolute',
                        top: '1rem',
                        left: '1rem',
                        right: '1rem',
                        bottom: '1rem',
                        backgroundColor: 'rgba(22, 34, 54, 0.98)', // theme dark
                        borderRadius: '10px',
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
                    }}>
                        {/* Header */}
                        <div style={{
                            padding: '1rem 1.2rem',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                            backgroundColor: 'rgba(15, 15, 15, 0.95)',
                        }}>
                            <h1 style={{
                                color: 'white',
                                fontSize: '2rem',
                                margin: 0,
                                fontFamily: '"Space Grotesk", "Inter", sans-serif',
                                fontWeight: 700,
                                letterSpacing: '0.5px',
                            }}>Research Rover</h1>
                            <div style={{
                                color: '#B8C6D9',
                                fontSize: '1.1rem',
                                fontFamily: '"Inter", sans-serif',
                                marginTop: '0.2rem',
                                fontWeight: 400,
                                letterSpacing: '0.01em',
                            }}>
                                Your AI-powered research assistant
                            </div>
                        </div>

                        {/* Messages Container */}
                        <div className="messages-container" style={{
                            flex: 1,
                            overflowY: 'auto',
                            padding: '1.5rem 2.5rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '1.5rem',
                            backgroundColor: 'transparent',
                            ...CustomScrollbar
                        }}>
                            {messages.length === 0 ? (
                                <div style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    height: '100%',
                                    gap: '1rem'
                                }}>
                                    <img
                                        src="/rover.png"
                                        alt="Research Rover"
                                        style={{
                                            width: '5rem',
                                            height: '5rem',
                                            borderRadius: '24px',
                                            objectFit: 'cover',
                                        }}
                                    />
                                    <p style={{
                                        color: '#B0BEC5', // Changed color for more prominence
                                        fontSize: '1.2rem',
                                        fontFamily: '"Inter", sans-serif',
                                        margin: 0
                                    }}>
                                        How can I assist you today?
                                    </p>
                                </div>
                            ) : (
                            messages.map((message, index) => (
                                <div
                                    key={index}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: '1rem',
                                        alignSelf: message.isUser ? 'flex-end' : 'flex-start',
                                        maxWidth: '90%',
                                        animation: 'fadeInUp 0.5s',
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
                                    {message.isUser && (
                                        <div style={{ 
                                            position: 'relative',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '8px'
                                        }}>
                                            <button
                                                onClick={() => handleCopyText(message.text, index)}
                                                style={{
                                                    background: 'transparent',
                                                    border: 'none',
                                                    cursor: 'pointer',
                                                    padding: '4px',
                                                    opacity: 0.7,
                                                    transition: 'all 0.2s ease-in-out',
                                                    color: 'rgba(255, 255, 255, 0.7)',
                                                    fontSize: '0.75rem',
                                                    fontFamily: '"Inter", sans-serif',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: '24px',
                                                    height: '24px',
                                                    ':hover': { opacity: 1 }
                                                }}
                                            >
                                                {copyingStates[index] ? (
                                                    <span style={{
                                                        animation: `${fadeIn} 0.2s ease-in-out`,
                                                        whiteSpace: 'nowrap'
                                                    }}>
                                                        Copied!
                                                    </span>
                                                ) : (
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                                                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                                                    </svg>
                                                )}
                                            </button>
                                            <button
                                                onClick={() => handleEditMessage(message.text, index)}
                                                style={{
                                                    background: 'transparent',
                                                    border: 'none',
                                                    cursor: 'pointer',
                                                    padding: '4px',
                                                    opacity: 0.7,
                                                    transition: 'opacity 0.2s',
                                                    ':hover': { opacity: 1 }
                                                }}
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                                                    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                                                </svg>
                                            </button>
                                            
                                        </div>
                                    )}
                                    {!message.isloading && (
                                        <div style={{
                                            backgroundColor: message.isUser 
                                                ? 'rgba(255,255,255,0.10)' // lighter for user
                                                : 'rgba(255, 255, 255, 0.08)',
                                            padding: '1.2rem 1.4rem',
                                            borderRadius: '16px',
                                            color: 'white',
                                            fontSize: '0.95rem',
                                            lineHeight: '1.6',
                                            fontFamily: '"Inter", sans-serif',
                                            border: message.isUser 
                                                ? '1.5px solid #4CAF50'
                                                : '1px solid rgba(255, 255, 255, 0.1)',
                                            boxShadow: '0 2px 12px rgba(30,58,95,0.10)',
                                            transition: 'box-shadow 0.2s, transform 0.2s',
                                            cursor: 'pointer',
                                            ':hover': {
                                                boxShadow: '0 4px 24px rgba(30,58,95,0.18)',
                                                transform: 'scale(1.02)',
                                            },
                                        }}>
                                            {message.isUser ? (
                                                message.text
                                            ) : (
                                                message.isloading ? (
                                                    <LoadingDots />
                                                ) : (
                                                    message.downloadUrls ? (
                                                        <TypeWriter
                                                            text={
                                                                formatResponseWithClickableLinks(message.text, message.downloadUrls)} 
                                                            speed={5}
                                                        />
                                                    ) : (
                                                        <TypeWriter
                                                            text={message.text}
                                                            speed={5}
                                                        />
                                                    )
                                                )
                                            )}
                                        </div>
                                    )}
                                   {!message.isUser && !message.isloading && (
                                        <button
                                            onClick={() => handleCopyText(message.text, index)}
                                            style={{
                                                background: 'transparent',
                                                    border: 'none',
                                                    cursor: 'pointer',
                                                    padding: '4px',
                                                    opacity: 0.7,
                                                    transition: 'all 0.2s ease-in-out',
                                                    color: 'rgba(255, 255, 255, 0.7)',
                                                    fontSize: '0.75rem',
                                                    fontFamily: '"Inter", sans-serif',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: '24px',
                                                    height: '24px',
                                                    ':hover': { opacity: 1 }
                                                }}
                                            >
                                                {copyingStates[index] ? (
                                                    <span style={{
                                                        animation: `${fadeIn} 0.2s ease-in-out`,
                                                        whiteSpace: 'nowrap'
                                                    }}>
                                                        Copied!
                                                    </span>
                                                ) : (
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                                                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                                                    </svg>
                                                )}
                                        </button>
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
                            ))
                        )}
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
                                border: '1.5px solid #1E3A5F', // theme border
                                boxShadow: '0 2px 8px rgba(30,58,95,0.10)',
                            }}>
                                <textarea
                                    type="text"
                                    value={inputMessage}
                                    onChange={(e) => {
                                        setInputMessage(e.target.value);
                                        e.target.style.height = 'auto';
                                        e.target.style.height = `${e.target.scrollHeight}px`;
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSendMessage(e);
                                        }
                                    }}
                                    placeholder="Ask your query..."
                                    rows={1}
                                    style={{
                                        flex: 1,
                                        padding: '0.8rem 1.2rem',
                                        fontSize: '0.95rem',
                                        backgroundColor: 'transparent',
                                        border: 'none',
                                        outline: 'none',
                                        color: '#FFFFFF',
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
                                        lineHeight: '1.2',
                                    }}
                                />
                                <button
                                    type="submit"
                                    disabled={loading}
                                    style={{
                                        width: '46px',
                                        height: '46px',
                                        background: loading 
                                            ? 'linear-gradient(90deg, #4CAF50 60%, #1E3A5F 100%)'
                                            : 'linear-gradient(90deg, #1E3A5F 0%, #4CAF50 100%)',
                                        border: 'none',
                                        borderRadius: '10px',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        transition: 'all 0.2s ease',
                                        boxShadow: '0 2px 8px rgba(30,58,95,0.15)',
                                        transform: loading ? 'none' : 'scale(1)',
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

// Add fadeInUp animation
<style>
{`
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
`}
</style>
