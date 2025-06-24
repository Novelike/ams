import React from 'react';
import { Box, Card, CircularProgress, LinearProgress, Typography, useTheme } from '@mui/material';

const CenteredLoader = ({ open = false, message = '처리 중...', progress = null }) => {
  const theme = useTheme();
  if (!open) return null;

  return (
    <Box
      sx={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        bgcolor: theme.palette.action.disabledBackground + 'AA',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: theme.zIndex.modal, pointerEvents: 'none'
      }}
    >
      <Card elevation={4} sx={{
        minWidth: 280, p: 3,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
        pointerEvents: 'all'
      }}>
        <CircularProgress size={56} thickness={4} />
        <Box sx={{ width: '100%', mt: 1 }}>
          <LinearProgress
            variant={typeof progress === 'number' ? "determinate" : "indeterminate"}
            value={typeof progress === 'number' ? progress : undefined}
            sx={{
              height: 6, borderRadius: 3,
              '& .MuiLinearProgress-bar': { transition: 'width 0.3s ease' }
            }}
          />
        </Box>
        <Typography
          variant="subtitle1"
          sx={{
            mt: typeof progress === 'number' ? 1 : 2,
            color: theme.palette.text.primary,
            textAlign: 'center', whiteSpace: 'pre-wrap'
          }}
        >
          {message}
        </Typography>
      </Card>
    </Box>
  );
};

export default CenteredLoader;
