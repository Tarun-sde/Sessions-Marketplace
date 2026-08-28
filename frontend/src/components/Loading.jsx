import React from 'react';
import { Loader2 } from 'lucide-react';

export const Loading = ({ message = 'Loading...' }) => {
  return (
    <div className="loading-container">
      <Loader2 className="spinner" size={36} />
      <p className="loading-text">{message}</p>
    </div>
  );
};
