import React from "react";
import { Box, Typography } from "@mui/material";

const Label = () => {
  return (
    <Box sx={{ marginBottom: "30px" }}>
      <Typography variant="h4" component="h1" gutterBottom>
        자산 라벨 관리
      </Typography>
      <Typography variant="body1">
        이 페이지에서는 자산 라벨을 생성하고, 다운로드하고, 프린트할 수 있습니다. 각 자산에 대한 QR 코드가 포함된 라벨을 관리할 수 있습니다.
      </Typography>
    </Box>
  );
};

export default Label;
