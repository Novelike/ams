import React from "react";
import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";
import { HeaderSection } from "../components/HeaderSection";
import { SidebarSection } from "../components/SidebarSection";
import { FooterSection } from "../components/FooterSection";
import { ThemeProvider } from "../ThemeProvider";

const MainLayout = () => {
  return (
    <ThemeProvider>
      <Box
        sx={{
          backgroundColor: "#f0f2f5",
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          width: "100%",
        }}
      >
        <Box
          sx={{
            backgroundColor: "var(--linearbackground)",
            width: { xs: "100%", xl: "1600px" },
            minHeight: { xs: "100vh", md: "1238px" },
            height: { xs: "auto", md: "1238px" },
            position: "relative",
            overflow: "hidden",
            paddingBottom: { xs: "60px", sm: "20px" },
          }}
        >
          {/* Sidebar */}
          <SidebarSection />

          <div
            className="main-content"
            style={{
              position: "absolute",
              left: "297px",
              padding: "20px 0px",
            }}
          >
            {/* Header */}
            <HeaderSection />

            {/* Main Content - Outlet will render the child routes */}
            <Box
              sx={{
                padding: { xs: "20px", md: 0 },
                marginTop: { xs: "80px", md: 0 },
                marginBottom: "30px",
                width: { xs: "100%", md: "1270px" },
              }}
            >
              <Outlet />
            </Box>

            {/* Footer */}
            <Box
              sx={{
                position: "relative",
                width: { xs: "100%", md: "1270px" },
                padding: { xs: "20px", md: 0 },
                marginTop: { xs: "20px", md: 0 },
              }}
            >
              <FooterSection />
            </Box>
          </div>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default MainLayout;
