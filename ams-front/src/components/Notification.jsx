import NotificationsIcon from "@mui/icons-material/Notifications";
import { SvgIcon } from "@mui/material";
import React from "react";

export const Notification = ({ sx }) => {
  return (
    <SvgIcon sx={sx} component={NotificationsIcon} fontSize="small" color="text.secondary" />
  );
};