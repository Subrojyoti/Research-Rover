import React from 'react';

const SearchProgressBar = ({ currentStage, stages }) => {
  return (
    <div className="search-progress-container">
      <div className="search-progress-bar">
        {stages.map((stage, index) => (
          <div 
            key={index} 
            className={`progress-checkpoint ${index < currentStage ? 'completed' : ''} ${index === currentStage ? 'current' : ''}`}
            style={{ 
              left: `${(index / (stages.length - 1)) * 100}%`,
              transform: `translateX(-50%)`
            }}
          >
            <div className="checkpoint-diamond"></div>
            <div className="checkpoint-label">{stage.label}</div>
          </div>
        ))}
        <div 
          className="progress-line" 
          style={{ 
            width: `${(currentStage / (stages.length - 1)) * 100}%`,
            transition: 'width 0.8s ease-in-out'
          }}
        ></div>
        <div 
          className="rover-container"
          style={{
            position: 'absolute',
            left: `${(currentStage / (stages.length - 1)) * 100}%`,
            bottom: '0',
            transform: 'translateX(-50%)',
            transition: 'left 0.8s ease-in-out',
            zIndex: 2
          }}
        >
          <img 
            src="/rover.png" 
            alt="Rover" 
            style={{
              width: '40px',
              height: 'auto'
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default SearchProgressBar; 