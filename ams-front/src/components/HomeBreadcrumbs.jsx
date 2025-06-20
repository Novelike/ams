import HomeIcon from "@mui/icons-material/Home";
import { SvgIcon } from "@mui/material";
import React from "react";

export const HomeBreadcrumbs = ({ sx }) => {
  return (
    <SvgIcon sx={sx} component={HomeIcon} fontSize="small" color="text.secondary" />
  );
};