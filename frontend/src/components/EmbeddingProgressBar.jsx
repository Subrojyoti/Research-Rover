import React from 'react';

const EmbeddingProgressBar = ({ currentStage, stages }) => {
    return (
        <div className="embedding-progress" style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
            <div className="progress-stages" style={{
                display: 'flex',
                justifyContent: 'space-between',
                position: 'relative',
                marginBottom: '1rem'
            }}>
                {/* Progress Line */}
                <div className="progress-line" style={{
                    position: 'absolute',
                    top: '25%',
                    left: '0',
                    right: '0',
                    height: '2px',
                    backgroundColor: 'rgba(255, 255, 255, 0.2)',
                    zIndex: 1
                }} />
                
                {/* Active Progress Line */}
                <div className="progress-line-active" style={{
                    position: 'absolute',
                    top: '25%',
                    left: '0',
                    height: '2px',
                    backgroundColor: '#4CAF50',
                    zIndex: 2,
                    width: `${(currentStage / (stages.length - 1)) * 100}%`,
                    transition: 'width 0.5s ease-in-out'
                }} />
                
                {/* Stage Markers */}
                {stages.map((stage, index) => (
                    <div key={index} className="stage" style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        zIndex: 3,
                        flex: 1
                    }}>
                        <div className="stage-marker" style={{
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            backgroundColor: index <= currentStage ? '#4CAF50' : 'rgba(255, 255, 255, 0.2)',
                            marginBottom: '0.5rem',
                            transition: 'all 0.3s ease',
                            boxShadow: index <= currentStage ? '0 0 10px rgba(76, 175, 80, 0.5)' : 'none'
                        }} />
                        <div className="stage-label" style={{
                            color: index <= currentStage ? '#fff' : 'rgba(255, 255, 255, 0.6)',
                            fontSize: '0.8rem',
                            fontWeight: index <= currentStage ? '600' : '400',
                            textAlign: 'center',
                            transition: 'all 0.3s ease'
                        }}>
                            {stage.label}
                        </div>
                        <div className="stage-description" style={{
                            color: 'rgba(255, 255, 255, 0.6)',
                            fontSize: '0.7rem',
                            textAlign: 'center',
                            marginTop: '0.25rem',
                            maxWidth: '120px'
                        }}>
                            {stage.description}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default EmbeddingProgressBar; 