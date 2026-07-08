import React from 'react';

const LoadingBar = ({ isLoading, progress = 0 }) => {
  if (!isLoading) return null;

  return (
    <div className="fixed left-0 top-0 z-[80] h-[3px] w-full overflow-hidden bg-transparent">
      {progress > 0 ? (
        <div className="h-full bg-brand-500 transition-all duration-300 ease-out" style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
      ) : (
        <div className="h-full w-1/3 rounded-full bg-gradient-to-r from-brand-400 via-brand-600 to-accent-400 animate-slide" />
      )}
    </div>
  );
};

export default LoadingBar;
