import SettingsIcon from "@mui/icons-material/Settings";
import {Badge, Box, Stack, Typography} from "@mui/material";
import React from "react";
import {HomeBreadcrumbs} from "./HomeBreadcrumbs";
import {Notification} from "./Notification";
import { useLocation } from "react-router-dom";

// Navigation menu data for mapping
const menuItems = [
	{
		id: "dashboards",
		label: "Dashboards",
		path: "/",
	},
	{
		id: "upload",
		label: "Upload",
		path: "/upload",
	},
	{
		id: "list",
		label: "List",
		path: "/list",
	},
	{
		id: "detailList",
		label: "Detail List",
		path: "/detail-list",
	},
	{
		id: "chatBot",
		label: "Chat Bot",
		path: "/chatbot",
	},
	{
		id: "label",
		label: "Label",
		path: "/label",
	},
];

export function HeaderSection() {
	const location = useLocation();

	// Find the current menu item based on the path
	const currentMenuItem = menuItems.find(item => item.path === location.pathname) || menuItems[0];

	return (
		<Box
			className="menu-header"
			sx={{
				position: "relative",
				width: {xs: "100%", md: "1270px"},
				height: {xs: "auto", md: "48px"},
				minHeight: "48px",
				display: "flex",
				flexDirection: {xs: "column", sm: "row"},
				justifyContent: "space-between",
				alignItems: {xs: "flex-start", sm: "center"},
				padding: {xs: "16px", md: 0},
				zIndex: 10,
				backgroundColor: {xs: "var(--linearwhite)", md: "transparent"},
				boxShadow: {xs: "var(--drop-shadow-black)", md: "none"},
				borderRadius: {xs: "8px", md: 0},
				marginBottom: "44px",
			}}
		>

			<Box
				className="overlap-3"
				sx={{
					display: "flex",
					flexDirection: "column"
				}}
			>

				<Box
					className="breadcrumbs"
					sx={{
						display: "flex",
						alignItems: "center",
						gap: "8px"
					}}
				>
					<Box
						component="img"
						className="icon-home"
						src="https://c.animaapp.com/6S1yK5Ge/img/icon-16px-home-breadcrumbs.svg"
						sx={{
							width: "16px",
							height: "16px",
						}}
					/>
					<Typography
						className="text-wrapper-21"
						variant="body2"
						color="var(--lineargrey)"
						sx={{
							fontFamily: "Roboto, Helvetica",
							fontSize: "14px",
							lineHeight: "19.6px",
						}}
					>
						/
					</Typography>
					<Typography
						className="profile-overview-2"
						variant="body2"
						color="var(--lineardark-blue)"
						sx={{
							fontFamily: "Roboto, Helvetica",
							fontSize: "14px",
							lineHeight: "19.6px",
						}}
					>
						{currentMenuItem.label}
					</Typography>
				</Box>

				<Typography
					className="profile-overview"
					variant="h6"
					color="var(--lineardark-blue)"
					sx={{
						fontFamily: "Roboto, Helvetica",
						fontWeight: 700,
						fontSize: "16px",
						lineHeight: "22.4px",
						marginBottom: "4px",
					}}
				>
					{currentMenuItem.label}
				</Typography>


			</Box>

			<Box sx={{display: "flex", alignItems: "center", gap: "16px"}}>
				<Box
					className="icon-settings"
					sx={{
						width: "16px",
						height: "16px",
						backgroundImage: "url('/icon-settings.svg')",
						backgroundSize: "contain",
						backgroundRepeat: "no-repeat",
					}}
				/>

				<Box
					className="overlap-4"
					sx={{
						position: "relative"
					}}
				>
					<Box
						component="img"
						className="icon"
						src="https://c.animaapp.com/6S1yK5Ge/img/icon-16px-notification.svg"
						sx={{
							width: "16px",
							height: "16px",
						}}
					/>
					<Box
						className="item-wrapper"
						sx={{
							position: "absolute",
							top: "-8px",
							right: "-8px"
						}}
					>
						<Box
							className="item"
							sx={{
								width: "16px",
								height: "16px",
								borderRadius: "19px",
								backgroundColor: "var(--linearred)",
								color: "white",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								fontFamily: "Roboto, Helvetica",
								fontSize: "10px",
								fontWeight: 700,
								lineHeight: "14px",
							}}
						>
							11
						</Box>
					</Box>
				</Box>
			</Box>
		</Box>
	);
}
