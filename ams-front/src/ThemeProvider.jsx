import {
	CssBaseline,
	ThemeProvider as MuiThemeProvider,
	createTheme,
} from "@mui/material";
import React from "react";

const appTheme = createTheme({
	palette: {
		primary: {
			main: "rgba(233, 31, 99, 1)", // linearred
		},
		secondary: {
			main: "rgba(26, 115, 231, 1)", // linearblue
		},
		error: {
			main: "rgba(244, 67, 52, 1)", // linearred-orange
		},
		warning: {
			main: "rgba(251, 140, 0, 1)", // linearorange
		},
		success: {
			main: "rgba(76, 175, 80, 1)", // lineargreen
		},
		info: {
			main: "rgba(22, 192, 232, 1)", // linearlight-blue
		},
		background: {
			default: "rgba(240, 242, 245, 1)", // linearbackground
			paper: "rgba(255, 255, 255, 1)", // linearwhite
		},
		text: {
			primary: "rgba(52, 71, 103, 1)", // lineardark-blue
			secondary: "rgba(123, 128, 154, 1)", // lineargrey
		},
		// Custom colors
		darkBlack: {
			main: "rgba(25, 25, 25, 1)", // lineardark-black
		},
		darkBlue: {
			main: "rgba(52, 71, 103, 1)", // lineardark-blue
		},
		darkMud: {
			main: "rgba(79, 79, 82, 1)", // lineardark-mud
		},
		lightMud: {
			main: "rgba(99, 99, 102, 1)", // linearlight-mud
		},
		darkSnow: {
			main: "rgba(199, 204, 208, 1)", // lineardark-snow
		},
		lightGreen: {
			main: "rgba(188, 225, 190, 1)", // linearlight-green
		},
		lightGrey: {
			main: "rgba(168, 184, 216, 1)", // linearlight-grey
		},
		mediumGrey: {
			main: "rgba(222, 226, 232, 1)", // linearmedium-grey
		},
		snow: {
			main: "rgba(233, 234, 237, 1)", // linearsnow
		},
		cloud: {
			main: "rgba(248, 249, 250, 1)", // linearcloud
		},
	},
	typography: {
		fontFamily: "Roboto, Helvetica, Arial, sans-serif",
		h1: {
			fontSize: "2rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		h2: {
			fontSize: "1.5rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		h3: {
			fontSize: "1.25rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		h4: {
			fontSize: "1.125rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		h5: {
			fontSize: "1rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		h6: {
			fontSize: "0.875rem",
			fontWeight: 700,
			lineHeight: 1.2,
		},
		subtitle1: {
			fontSize: "1rem",
			fontWeight: 400,
			lineHeight: 1.4,
		},
		subtitle2: {
			fontSize: "0.875rem",
			fontWeight: 500,
			lineHeight: 1.4,
		},
		body1: {
			fontSize: "0.875rem", // 14px
			fontWeight: 400,
			lineHeight: 1.4,
			letterSpacing: "0px",
		},
		body2: {
			fontSize: "0.75rem", // 12px
			fontWeight: 400,
			lineHeight: 1.4,
			letterSpacing: "0px",
		},
		button: {
			fontSize: "0.875rem",
			fontWeight: 500,
			lineHeight: 1.75,
			textTransform: "none",
		},
		caption: {
			fontSize: "0.75rem",
			fontWeight: 400,
			lineHeight: 1.4,
		},
		overline: {
			fontSize: "0.625rem",
			fontWeight: 400,
			lineHeight: 1.4,
			textTransform: "uppercase",
		},
	},
	shadows: {
		0: "none",
		1: "0px 2px 6px 0px rgba(0, 0, 0, 0.25)", // drop-shadow-black
		2: "0px 2px 6px 0px rgba(40, 129, 235, 0.36)", // drop-shadow-blue
		3: "0px 2px 6px 0px rgba(79, 169, 83, 0.36)", // drop-shadow-green
		4: "0px 2px 6px 0px rgba(151, 172, 198, 0.25)", // drop-shadow-grey
		5: "0px 2px 6px 0px rgba(220, 34, 101, 0.36)", // drop-shadow-red
		// Keep the rest of the default shadows
		6: "0px 3px 5px -1px rgba(0,0,0,0.2),0px 6px 10px 0px rgba(0,0,0,0.14),0px 1px 18px 0px rgba(0,0,0,0.12)",
		7: "0px 4px 5px -2px rgba(0,0,0,0.2),0px 7px 10px 1px rgba(0,0,0,0.14),0px 2px 16px 1px rgba(0,0,0,0.12)",
		8: "0px 5px 5px -3px rgba(0,0,0,0.2),0px 8px 10px 1px rgba(0,0,0,0.14),0px 3px 14px 2px rgba(0,0,0,0.12)",
		9: "0px 5px 6px -3px rgba(0,0,0,0.2),0px 9px 12px 1px rgba(0,0,0,0.14),0px 3px 16px 2px rgba(0,0,0,0.12)",
		10: "0px 6px 6px -3px rgba(0,0,0,0.2),0px 10px 14px 1px rgba(0,0,0,0.14),0px 4px 18px 3px rgba(0,0,0,0.12)",
		11: "0px 6px 7px -4px rgba(0,0,0,0.2),0px 11px 15px 1px rgba(0,0,0,0.14),0px 4px 20px 3px rgba(0,0,0,0.12)",
		12: "0px 7px 8px -4px rgba(0,0,0,0.2),0px 12px 17px 2px rgba(0,0,0,0.14),0px 5px 22px 4px rgba(0,0,0,0.12)",
		13: "0px 7px 8px -4px rgba(0,0,0,0.2),0px 13px 19px 2px rgba(0,0,0,0.14),0px 5px 24px 4px rgba(0,0,0,0.12)",
		14: "0px 7px 9px -4px rgba(0,0,0,0.2),0px 14px 21px 2px rgba(0,0,0,0.14),0px 5px 26px 4px rgba(0,0,0,0.12)",
		15: "0px 8px 9px -5px rgba(0,0,0,0.2),0px 15px 22px 2px rgba(0,0,0,0.14),0px 6px 28px 5px rgba(0,0,0,0.12)",
		16: "0px 8px 10px -5px rgba(0,0,0,0.2),0px 16px 24px 2px rgba(0,0,0,0.14),0px 6px 30px 5px rgba(0,0,0,0.12)",
		17: "0px 8px 11px -5px rgba(0,0,0,0.2),0px 17px 26px 2px rgba(0,0,0,0.14),0px 6px 32px 5px rgba(0,0,0,0.12)",
		18: "0px 9px 11px -5px rgba(0,0,0,0.2),0px 18px 28px 2px rgba(0,0,0,0.14),0px 7px 34px 6px rgba(0,0,0,0.12)",
		19: "0px 9px 12px -6px rgba(0,0,0,0.2),0px 19px 29px 2px rgba(0,0,0,0.14),0px 7px 36px 6px rgba(0,0,0,0.12)",
		20: "0px 10px 13px -6px rgba(0,0,0,0.2),0px 20px 31px 3px rgba(0,0,0,0.14),0px 8px 38px 7px rgba(0,0,0,0.12)",
		21: "0px 10px 13px -6px rgba(0,0,0,0.2),0px 21px 33px 3px rgba(0,0,0,0.14),0px 8px 40px 7px rgba(0,0,0,0.12)",
		22: "0px 10px 14px -6px rgba(0,0,0,0.2),0px 22px 35px 3px rgba(0,0,0,0.14),0px 8px 42px 7px rgba(0,0,0,0.12)",
		23: "0px 11px 14px -7px rgba(0,0,0,0.2),0px 23px 36px 3px rgba(0,0,0,0.14),0px 9px 44px 8px rgba(0,0,0,0.12)",
		24: "0px 11px 15px -7px rgba(0,0,0,0.2),0px 24px 38px 3px rgba(0,0,0,0.14),0px 9px 46px 8px rgba(0,0,0,0.12)",
	},
	shape: {
		borderRadius: 8,
	},
	components: {
		MuiButton: {
			styleOverrides: {
				root: {
					textTransform: "none",
					borderRadius: 8,
				},
			},
		},
		MuiCard: {
			styleOverrides: {
				root: {
					borderRadius: 8,
					boxShadow: "0px 2px 6px 0px rgba(0, 0, 0, 0.25)",
				},
			},
		},
		MuiTableCell: {
			styleOverrides: {
				root: ({ theme }) => ({
					...theme.typography.body1,
					padding: "12px 16px",
				}),
				head: ({ theme }) => ({
					...theme.typography.subtitle2,
					backgroundColor: theme.palette.background.default,
					color: theme.palette.text.secondary,
					fontSize: "0.625rem",
					textTransform: "uppercase",
				}),
				body: ({ theme }) => ({
					...theme.typography.body1,
					color: theme.palette.text.primary,
				}),
			},
		},
		MuiListItemText: {
			styleOverrides: {
				primary: ({ theme }) => ({
					...theme.typography.body1,
					color: theme.palette.text.primary,
					fontWeight: 500,
				}),
				secondary: ({ theme }) => ({
					...theme.typography.body2,
					color: theme.palette.text.secondary,
				}),
			},
		},
		MuiListItemButton: {
			styleOverrides: {
				root: {
					borderRadius: 8,
				},
			},
		},
		MuiPaper: {
			styleOverrides: {
				root: {
					borderRadius: 8,
				},
			},
		},
	},
});

export const ThemeProvider = ({ children }) => {
	return (
		<MuiThemeProvider theme={appTheme}>
			<CssBaseline />
			{children}
		</MuiThemeProvider>
	);
};
