import React from 'react';
import { Backdrop, CircularProgress, Box, Typography } from '@mui/material';

/**
 * FullscreenLoader component for displaying full screen loading state
 * @param {Object} props - Component props
 * @param {boolean} props.open - Whether to show the loader
 * @param {string} props.message - Optional loading message
 */
const FullscreenLoader = ({ open = false, message = "처리 중..." }) => {
  return (
    <Backdrop 
      open={open} 
      sx={{ 
        color: '#fff',
        zIndex: theme => theme.zIndex.drawer + 1,
        flexDirection: 'column',
        gap: 2
      }}
    >
      <CircularProgress color="inherit" size={60} />
      {message && (
        <Typography variant="h6" component="div">
          {message}
        </Typography>
      )}
    </Backdrop>
  );
};

export default FullscreenLoader;