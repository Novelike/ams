import React from "react";
import { Box, Typography } from "@mui/material";

const ChatBot = () => {
  return (
    <Box sx={{ marginBottom: "30px" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Chat Bot Page
      </Typography>
      <Typography variant="body1">
        This is the chat bot page where users can interact with an AI assistant.
      </Typography>
    </Box>
  );
};

export default ChatBot;
