import React from 'react';
import { Box, Button } from "@mui/material";

/**
 * RegistrationFooter component for displaying navigation buttons
 * @param {Object} props - Component props
 * @param {number} props.activeStep - Current active step
 * @param {number} props.totalSteps - Total number of steps
 * @param {Function} props.onBack - Function to handle back button click
 * @param {Function} props.onNext - Function to handle next button click
 * @param {Function} props.onReset - Function to handle reset button click
 * @param {boolean} props.isNextDisabled - Whether the next button should be disabled
 */
const RegistrationFooter = ({ 
  activeStep, 
  totalSteps, 
  onBack, 
  onNext, 
  onReset,
  isNextDisabled
}) => {
  return (
    <Box sx={{ 
      padding: 3,
      paddingTop: 1,
      backgroundColor: 'white',
      borderTop: '1px solid #e0e0e0',
      zIndex: 2
    }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          onClick={onBack}
          disabled={activeStep === 0}
        >
          이전
        </Button>
        
        <Box>
          <Button onClick={onReset} sx={{ marginRight: 1 }}>
            초기화
          </Button>
          {activeStep === totalSteps - 1 ? (
            <Button variant="contained" color="success">
              완료
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={onNext}
              disabled={isNextDisabled}
            >
              다음
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default RegistrationFooter;