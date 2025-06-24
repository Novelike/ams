import React from 'react';
import { Box, Typography, Stepper, Step, StepLabel } from "@mui/material";

/**
 * RegistrationHeader component for displaying the title and stepper
 * @param {Object} props - Component props
 * @param {number} props.activeStep - Current active step
 * @param {Array} props.steps - Array of step objects with label and description
 */
const RegistrationHeader = ({ activeStep, steps }) => {
  return (
    <Box sx={{ 
      padding: 3, 
      paddingBottom: 1,
      backgroundColor: 'white',
      borderBottom: '1px solid #e0e0e0',
      zIndex: 2
    }}>
      <Typography variant="h4" gutterBottom align="center">
        자산 등록 시스템
      </Typography>
      
      <Stepper activeStep={activeStep} orientation="horizontal" sx={{ marginBottom: 2 }}>
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel>
              <Typography variant="subtitle2">{step.label}</Typography>
              <Typography variant="caption" color="textSecondary">
                {step.description}
              </Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
};

export default RegistrationHeader;