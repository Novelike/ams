import DashboardIcon from "@mui/icons-material/Dashboard";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import {
	Box,
	Divider,
	List,
	ListItem,
	ListItemIcon,
	ListItemText,
	Typography,
} from "@mui/material";
import {useTheme} from "@mui/material/styles";
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";

// Navigation menu data for mapping
const menuItems = [
	{
		id: "dashboard",
		label: "대시보드",
		icon: <DashboardIcon fontSize="small"/>,
		path: "/",
	},
	{
		id: "registration",
		label: "자산 등록",
		letter: "R",
		path: "/registration",
	},
	{
		id: "assetList",
		label: "자산 목록",
		letter: "A",
		path: "/assets",
	},
	{
		id: "chatBot",
		label: "챗봇",
		letter: "C",
		path: "/chatbot",
	},
	{
		id: "label",
		label: "라벨",
		letter: "L",
		path: "/labels",
	},
];

const getBackgroundColor = (isSelected, isActive, theme) => {
	if (isActive) return theme.palette.lightMud.main; // lineardark-mud - 클릭된 상태
	if (isSelected) return theme.palette.primary.main; // linearred - 선택된 상태
	return "transparent";
};

export const SidebarSection = () => {
	const theme = useTheme();
	const navigate = useNavigate();
	const location = useLocation();
	const [activeItem, setActiveItem] = React.useState(null);

	const handleMenuItemClick = (path) => {
		navigate(path);
	};

	// 마우스 다운 시 active 상태로 변경
	const handleMouseDown = (id) => {
		setActiveItem(id);
	};

	// 마우스 업 시 active 상태 해제
	const handleMouseUp = () => {
		setActiveItem(null);
	};

	return (
		<Box
			className="menu-main"
			sx={{
				position: "fixed",
				width: {xs: "100%", sm: "64px", md: "200px", lg: "256px"},
				height: "740px",
				bottom: {xs: "0", sm: "auto"},
				display: "flex",
				flexDirection: {xs: "row", sm: "column"},
				padding: {xs: "8px", sm: "16px"},
				borderRadius: {xs: "8px 8px 0 0", sm: "8px"},
				background:
					"linear-gradient(180deg, rgba(62,61,69,1) 0%, rgba(32,32,32,1) 100%)",
				zIndex: 1000,
				transition: "all 0.3s ease",
			}}
		>
			{/* Header with logo and title */}
			<Box
				className="logo"
				sx={{
					display: {xs: "none", sm: "flex"},
					alignItems: "center",
					gap: "8px",
					marginBottom: "16px",
					justifyContent: {sm: "center", md: "flex-start"}
				}}
			>
				<Box
					className="novelike-white-nobg"
					sx={{
						position: "relative",
						width: "28px",
						height: "28px"
					}}
				>
					<Box
						component="img"
						src="/novelike-logo-white.svg"
						alt="Logo"
						className="group-2"
						sx={{
							position: "absolute",
							width: "24px",
							height: "28px",
							top: "0",
							left: "2px",
						}}
					/>
				</Box>
				<Typography
					className="text-wrapper-16"
					variant="subtitle2"
					fontWeight="bold"
					color="common.white"
					sx={{
						whiteSpace: "nowrap",
						fontFamily: "Roboto, Helvetica",
						fontSize: "14px",
						lineHeight: "19.6px",
					}}
				>
					자산 관리 시스템
				</Typography>
			</Box>

			<Box
				component="img"
				className="line-2"
				src="https://c.animaapp.com/6S1yK5Ge/img/line-3.svg"
				sx={{
					width: {sm: "100%", lg: "224px"},
					height: "1px",
					marginBottom: "16px",
					display: {xs: "none", sm: "block"}
				}}
			/>

			{/* Navigation menu */}
			<Box
				className="main-nav"
				sx={{
					display: "flex",
					flexDirection: {xs: "row", sm: "column"},
					gap: {xs: "4px", sm: "12px"},
					flex: 1,
					width: {xs: "100%", sm: "auto"},
					justifyContent: {xs: "space-around", sm: "flex-start"},
					alignItems: {xs: "center", sm: "stretch"}
				}}
			>
				{menuItems.map((item, index) => {
					const buttonClass = index === 0 ? "menu-button-primary" :
						index === 1 ? "menu-button" : "menu-button-2";

					const isSelected = location.pathname === item.path;
					const isActive = activeItem === item.id;

					return (
						<Box
							key={item.id}
							className={buttonClass}
							onClick={() => handleMenuItemClick(item.path)}
							onMouseDown={() => handleMouseDown(item.id)}
							onMouseUp={handleMouseUp}
							onMouseLeave={handleMouseUp} // 마우스가 버튼을 벗어나면 active 해제
							sx={{
								height: {xs: "40px", sm: "48px"},
								width: {xs: "40px", sm: "auto"},
								borderRadius: "8px",
								padding: {xs: "0", sm: "0 16px"},
								display: "flex",
								alignItems: "center",
								justifyContent: {xs: "center", sm: "flex-start"},
								backgroundColor: getBackgroundColor(isSelected, isActive, theme),
								"&:hover": {
									backgroundColor: isSelected ? theme.palette.primary.main : "rgba(255,255,255,0.1)",
									cursor: "pointer",
								},
								flex: {xs: 1, sm: "none"},
								maxWidth: {xs: "60px", sm: "none"},
								transition: "background-color 0.2s ease", // 부드러운 색상 전환
							}}
						>
							{item.icon ? (
								<Box
									className="icon-dashboard"
									sx={{
										width: "20px",
										height: "20px",
										marginRight: {xs: "0", sm: "16px"},
										color: "white"
									}}
								>
									{item.icon}
								</Box>
							) : (
								<Box
									className="a"
									sx={{
										width: "20px",
										height: "20px",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										marginRight: {xs: "0", sm: "16px"},
										color: "white",
										fontFamily: "Roboto, Helvetica",
										fontSize: "14px",
									}}
								>
									{item.letter}
								</Box>
							)}

							<Typography
								className="text-wrapper-17"
								sx={{
									color: "white",
									fontFamily: "Roboto, Helvetica",
									fontSize: "14px",
									fontWeight: 400,
									lineHeight: "19.6px",
									flex: 1,
									display: {xs: "none", sm: "block"}
								}}
							>
								{item.label}
							</Typography>

						</Box>
					);
				})}
			</Box>
		</Box>
	);
};
