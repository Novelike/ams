import React from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';

/**
 * UploadProgressBar component for displaying file upload progress
 * @param {Object} props - Component props
 * @param {number} props.progress - Upload progress (0-100)
 * @param {boolean} props.show - Whether to show the progress bar
 */
const UploadProgressBar = ({ progress = 0, show = false }) => {
  if (!show) return null;

  return (
    <Box sx={{ width: '100%', mt: 2 }}>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        업로드 중... {Math.round(progress)}%
      </Typography>
      <LinearProgress 
        variant="determinate" 
        value={progress}
        sx={{
          height: 8,
          borderRadius: 4,
          backgroundColor: theme => theme.palette.grey[300],
          '& .MuiLinearProgress-bar': { 
            borderRadius: 4,
            backgroundColor: theme => theme.palette.primary.main
          }
        }}
      />
    </Box>
  );
};

export default UploadProgressBar;